import socket
import struct
import subprocess
import time
from media_protocol import *

DEST_IP = "172.20.10.2"
DEST_PORT = 6009

CHUNK_BYTES = 640

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

cmd = [
    "pw-record",
    "--rate", "16000",
    "--channels", "1",
    "--format", "s16",
    "-"
]

print("Starting audio capture...")
print(f"UDP: {DEST_IP}:{DEST_PORT}")
print(f"Chunk: {CHUNK_BYTES} bytes")

process = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    bufsize=0
)

sequence = 0
buffer = bytearray()

try:
    while True:
        data = process.stdout.read(256)

        if not data:
            break

        buffer.extend(data)

        while len(buffer) >= CHUNK_BYTES:
            audio = buffer[:CHUNK_BYTES]
            del buffer[:CHUNK_BYTES]

            timestamp_ns = time.time_ns()

            #packet = struct.pack("!IQ", sequence, timestamp_ns) + audio
            
            packet = (struct.pack(COMMON_HEADER_FORMAT, STREAM_AUDIO,sequence, timestamp_ns) + audio)
            
            sock.sendto(packet, (DEST_IP, DEST_PORT))

            sequence += 1

            if sequence % 50 == 0:
                print(f"Packets sent: {sequence}")

except KeyboardInterrupt:
    print("\nStopping...")

finally:
    process.terminate()
    process.wait()
    sock.close()
