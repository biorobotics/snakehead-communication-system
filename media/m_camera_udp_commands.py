from picamera2 import Picamera2
import cv2
import socket
import struct
import time
import threading
from media_protocol import *

# ============================================================
# NETWORK SETTINGS
# ============================================================

LAPTOP_IP = "172.20.10.2"

VIDEO_PORT = 6009
COMMAND_PORT = 6002

# ============================================================
# CAMERA SETTINGS
# ============================================================

camera_settings = {
    "streaming": True,
    "brightness": 0.0,
    "fps": 20,
    "jpeg_quality": 25,
}

# ============================================================
# CAMERA SETUP
# ============================================================

TUNING_FILE = "/usr/share/libcamera/ipa/rpi/vc4/vd56g3.json"

picam2 = Picamera2(
    tuning=Picamera2.load_tuning_file(TUNING_FILE)
)

config = picam2.create_preview_configuration(
    main={"size": (820,616)}
)

picam2.configure(config)
picam2.start()

# ============================================================
# VIDEO SOCKET
# ============================================================

video_sock = socket.socket(
    socket.AF_INET,
    socket.SOCK_DGRAM
)

# ============================================================
# COMMAND SOCKET
# ============================================================

cmd_sock = socket.socket(
    socket.AF_INET,
    socket.SOCK_DGRAM
)

cmd_sock.bind(("0.0.0.0", COMMAND_PORT))

# ============================================================
# COMMAND LISTENER
# ============================================================

def command_listener():

    while True:

        data, addr = cmd_sock.recvfrom(1024)

        command = data.decode().strip()

        print(f"[CMD] {command}")

        try:

            if command == "START":

                camera_settings["streaming"] = True

            elif command == "STOP":

                camera_settings["streaming"] = False

            elif command.startswith("SET_BRIGHTNESS"):

                value = float(command.split()[1])

                camera_settings["brightness"] = value

                picam2.set_controls({
                    "Brightness": value
                })

            elif command.startswith("SET_FPS"):

                value = int(command.split()[1])

                camera_settings["fps"] = value

            elif command.startswith("SET_QUALITY"):

                value = int(command.split()[1])

                camera_settings["jpeg_quality"] = value

            elif command.startswith("SET_EXPOSURE"):

                value = int(command.split()[1])

                picam2.set_controls({
                    "ExposureTime": value
                })

        except Exception as e:

            print(f"[CMD ERROR] {e}")

# ============================================================
# START COMMAND THREAD
# ============================================================

threading.Thread(
    target=command_listener,
    daemon=True
).start()

print("Camera stream started")
print(f"Video port   : {VIDEO_PORT}")
print(f"Command port : {COMMAND_PORT}")

# ============================================================
# MAIN LOOP
# ============================================================

frame_id = 0
video_sequence = 0

try:

    while True:

        loop_start = time.time()

        if not camera_settings["streaming"]:

            time.sleep(0.1)
            continue

        frame = picam2.capture_array()

        frame = cv2.cvtColor(
            frame,
            cv2.COLOR_RGBA2BGR
        )
        
        cv2.imshow("Pi Camera", frame)
		
        if cv2.waitKey(1) & 0xFF == ord ("q"):
            break

        success, encoded = cv2.imencode(
            ".jpg",
            frame,
            [
                cv2.IMWRITE_JPEG_QUALITY,
                camera_settings["jpeg_quality"]
            ]
        )

        if not success:
            continue

        data = encoded.tobytes()

        MAX_PACKET_SIZE = 19000

        total_packets = (
            len(data) + MAX_PACKET_SIZE - 1
        ) // MAX_PACKET_SIZE

        for packet_id in range(total_packets):

            start = packet_id * MAX_PACKET_SIZE
            end = min(
                start + MAX_PACKET_SIZE,
                len(data)
            )

            chunk = data[start:end]

            # Header:
            # frame_id      -> uint32
            # packet_id     -> uint16
            # total_packets -> uint16

            '''header = struct.pack(
                "!IHH",
                frame_id,
                packet_id,
                total_packets
            )

            video_sock.sendto(
                header + chunk,
                (LAPTOP_IP, VIDEO_PORT)
            )'''

            timestamp_ns = time.time_ns()
            
            common_header = struct.pack(COMMON_HEADER_FORMAT, STREAM_VIDEO, video_sequence, timestamp_ns)
            video_header = struct.pack(VIDEO_HEADER_FORMAT, frame_id, packet_id, total_packets)
            
            packet = (common_header + video_header + chunk)
            
            video_sock.sendto(packet, (LAPTOP_IP, VIDEO_PORT))
            
            video_sequence += 1
            
        frame_id += 1

        target_frame_time = (
            1.0 / camera_settings["fps"]
        )

        elapsed = time.time() - loop_start

        if elapsed < target_frame_time:

            time.sleep(
                target_frame_time - elapsed
            )

except KeyboardInterrupt:

    print("\nStopping camera...")

finally:

    picam2.stop()
    cmd_sock.close()
    video_sock.close()
