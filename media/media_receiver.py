import socket
import struct
import cv2
import numpy as np
import threading
import sounddevice as sd
import time
import queue

from media_protocol import *


# ============================================================
# SETTINGS
# ============================================================

PI_IP = "172.20.10.3"

MEDIA_PORT = 6009
COMMAND_PORT = 6002

DEBUG_LATENCY = False

# Keep these intentionally small.
# If processing falls behind, old data gets dropped.
AUDIO_QUEUE_SIZE = 5
VIDEO_QUEUE_SIZE = 2


# ============================================================
# QUEUES
# ============================================================

audio_queue = queue.Queue(maxsize=AUDIO_QUEUE_SIZE)

# This queue contains COMPLETE JPEG frames,
# not individual UDP packets.
video_queue = queue.Queue(maxsize=VIDEO_QUEUE_SIZE)


# ============================================================
# MEDIA SOCKET
# ============================================================

media_sock = socket.socket(
    socket.AF_INET,
    socket.SOCK_DGRAM
)

media_sock.setsockopt(
    socket.SOL_SOCKET,
    socket.SO_RCVBUF,
    4 * 1024 * 1024
)

media_sock.bind(
    ("0.0.0.0", MEDIA_PORT)
)


# ============================================================
# COMMAND SOCKET
# ============================================================

command_sock = socket.socket(
    socket.AF_INET,
    socket.SOCK_DGRAM
)


def send_command(command):

    command_sock.sendto(
        command.encode(),
        (PI_IP, COMMAND_PORT)
    )

    print(f"[CMD] {command}")


def command_input():

    print()
    print("Camera controls:")
    print("  START")
    print("  STOP")
    print("  SET_BRIGHTNESS 0.0")
    print("  SET_FPS 25")
    print("  SET_QUALITY 30")
    print("  SET_EXPOSURE 10000")
    print()

    while running:

        try:

            command = input("camera> ").strip()

            if command:
                send_command(command)

        except EOFError:
            break

        except Exception:
            break


# ============================================================
# AUDIO OUTPUT
# ============================================================

audio_stream = sd.RawOutputStream(
    samplerate=16000,
    channels=1,
    dtype="int16",
    blocksize=320,
    latency="low"
)


# ============================================================
# STATE
# ============================================================

running = True

audio_packets_received = 0
audio_packets_dropped = 0

video_frames_received = 0
video_frames_dropped = 0


# ============================================================
# HELPER: PUT NEWEST ITEM INTO QUEUE
# ============================================================

def put_latest(q, item):
    """
    Put an item into a bounded queue.

    If the queue is full, discard the oldest item
    so we always prioritize the newest real-time data.
    """

    try:

        q.put_nowait(item)

    except queue.Full:

        try:
            q.get_nowait()
        except queue.Empty:
            pass

        try:
            q.put_nowait(item)
        except queue.Full:
            pass


# ============================================================
# UDP RECEIVER THREAD
# ============================================================

def receiver_thread():

    global running

    global audio_packets_received
    global audio_packets_dropped

    global video_frames_received
    global video_frames_dropped

    # Video frame reconstruction state
    packets = {}

    current_frame_id = None
    current_total_packets = 0
    current_timestamp_ns = 0

    while running:

        try:

            packet, addr = media_sock.recvfrom(65535)

        except OSError:
            break


        # ----------------------------------------------------
        # COMMON HEADER
        # ----------------------------------------------------

        if len(packet) < COMMON_HEADER_SIZE:
            continue


        (
            stream_type,
            sequence,
            timestamp_ns
        ) = struct.unpack(
            COMMON_HEADER_FORMAT,
            packet[:COMMON_HEADER_SIZE]
        )


        # ====================================================
        # AUDIO
        # ====================================================

        if stream_type == STREAM_AUDIO:

            audio_payload = packet[
                COMMON_HEADER_SIZE:
            ]


            if len(audio_payload) != 640:
                continue


            audio_packets_received += 1


            # Try inserting newest audio packet.
            # Drop oldest audio if queue is full.
            if audio_queue.full():

                try:
                    audio_queue.get_nowait()
                    audio_packets_dropped += 1

                except queue.Empty:
                    pass


            try:

                audio_queue.put_nowait(
                    (
                        sequence,
                        timestamp_ns,
                        audio_payload
                    )
                )

            except queue.Full:

                audio_packets_dropped += 1


        # ====================================================
        # VIDEO
        # ====================================================

        elif stream_type == STREAM_VIDEO:

            video_header_start = COMMON_HEADER_SIZE

            video_header_end = (
                COMMON_HEADER_SIZE
                + VIDEO_HEADER_SIZE
            )


            if len(packet) < video_header_end:
                continue


            (
                frame_id,
                packet_id,
                total_packets
            ) = struct.unpack(
                VIDEO_HEADER_FORMAT,
                packet[
                    video_header_start:
                    video_header_end
                ]
            )


            chunk = packet[
                video_header_end:
            ]


            # ------------------------------------------------
            # NEW FRAME
            # ------------------------------------------------

            if frame_id != current_frame_id:

                # If old frame never completed,
                # abandon it immediately.
                packets = {}

                current_frame_id = frame_id
                current_total_packets = total_packets

                # Save timestamp from first packet
                current_timestamp_ns = timestamp_ns


            packets[packet_id] = chunk


            # ------------------------------------------------
            # COMPLETE FRAME
            # ------------------------------------------------

            if len(packets) == current_total_packets:

                try:

                    jpeg_data = b"".join(
                        packets[i]
                        for i in range(
                            current_total_packets
                        )
                    )

                except KeyError:

                    packets = {}
                    continue


                video_frames_received += 1


                # Drop old complete frame if the
                # video decoder is behind.
                if video_queue.full():

                    try:
                        video_queue.get_nowait()
                        video_frames_dropped += 1

                    except queue.Empty:
                        pass


                try:

                    video_queue.put_nowait(
                        (
                            current_frame_id,
                            current_timestamp_ns,
                            jpeg_data
                        )
                    )

                except queue.Full:

                    video_frames_dropped += 1


                packets = {}


# ============================================================
# AUDIO PLAYBACK THREAD
# ============================================================

def audio_thread():

    global running

    audio_stream.start()

    while running:

        try:

            (
                sequence,
                timestamp_ns,
                audio_payload
            ) = audio_queue.get(
                timeout=0.1
            )

        except queue.Empty:
            continue


        if DEBUG_LATENCY:

            latency_ms = (
                time.time_ns()
                - timestamp_ns
            ) / 1e6

            # Only occasional debug output
            if sequence % 100 == 0:

                print(
                    f"\nAUDIO "
                    f"seq={sequence} "
                    f"latency={latency_ms:.1f} ms"
                )


        try:

            audio_stream.write(
                audio_payload
            )

        except Exception as e:

            print(
                f"\n[AUDIO ERROR] {e}"
            )


# ============================================================
# START THREADS
# ============================================================

receiver = threading.Thread(
    target=receiver_thread,
    daemon=True
)

audio_worker = threading.Thread(
    target=audio_thread,
    daemon=True
)

command_worker = threading.Thread(
    target=command_input,
    daemon=True
)


receiver.start()
audio_worker.start()
command_worker.start()


# ============================================================
# START MESSAGE
# ============================================================

print()
print(
    f"Listening for unified media "
    f"on UDP port {MEDIA_PORT}"
)

print(
    "Audio: 16000 Hz / mono / int16"
)

print(
    f"Audio queue: {AUDIO_QUEUE_SIZE} packets"
)

print(
    f"Video queue: {VIDEO_QUEUE_SIZE} frames"
)

print(
    "Press 'q' in the video window to quit."
)

print()


# ============================================================
# VIDEO LOOP
#
# Keep OpenCV display in MAIN THREAD.
# ============================================================

try:

    while running:

        try:

            (
                frame_id,
                timestamp_ns,
                jpeg_data
            ) = video_queue.get(
                timeout=0.01
            )


            # -----------------------------------------------
            # LATENCY DEBUG
            # -----------------------------------------------

            if DEBUG_LATENCY:

                latency_ms = (
                    time.time_ns()
                    - timestamp_ns
                ) / 1e6

                if frame_id % 20 == 0:

                    print(
                        f"\nVIDEO "
                        f"frame={frame_id} "
                        f"latency={latency_ms:.1f} ms"
                    )


            # -----------------------------------------------
            # DECODE JPEG
            # -----------------------------------------------

            image_array = np.frombuffer(
                jpeg_data,
                dtype=np.uint8
            )


            frame = cv2.imdecode(
                image_array,
                cv2.IMREAD_COLOR
            )


            # -----------------------------------------------
            # DISPLAY
            # -----------------------------------------------

            if frame is not None:

                cv2.imshow(
                    "Unified Media Stream",
                    frame
                )


        except queue.Empty:
            pass


        # -----------------------------------------------
        # QUIT
        # -----------------------------------------------

        if cv2.waitKey(1) & 0xFF == ord("q"):
            running = False
            break


except KeyboardInterrupt:

    running = False


# ============================================================
# CLEANUP
# ============================================================

finally:

    print("\nStopping receiver...")

    running = False

    try:
        media_sock.close()
    except Exception:
        pass

    try:
        command_sock.close()
    except Exception:
        pass

    try:
        audio_stream.stop()
        audio_stream.close()
    except Exception:
        pass

    cv2.destroyAllWindows()

    print()
    print("Session stats:")
    print(
        f"Audio packets received: "
        f"{audio_packets_received}"
    )

    print(
        f"Audio packets dropped: "
        f"{audio_packets_dropped}"
    )

    print(
        f"Video frames received: "
        f"{video_frames_received}"
    )

    print(
        f"Video frames dropped: "
        f"{video_frames_dropped}"
    )