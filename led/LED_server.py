import socket
import board
import neopixel

# -----------------------------
# NeoPixel configuration
# -----------------------------

PIXEL_PIN = board.D18
NUM_PIXELS = 12
BRIGHTNESS = 0.2

pixels = neopixel.NeoPixel(
    PIXEL_PIN,
    NUM_PIXELS,
    brightness=BRIGHTNESS,
    auto_write=False,
    pixel_order=neopixel.GRB
)


# -----------------------------
# LED functions
# -----------------------------

def led_on():
    pixels.fill((255, 255, 255))
    pixels.show()
    print("LED: ON")


def led_off():
    pixels.fill((0, 0, 0))
    pixels.show()
    print("LED: OFF")


# Make sure we start OFF
led_off()


# -----------------------------
# UDP server
# -----------------------------

UDP_IP = "0.0.0.0"
UDP_PORT = 6010

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print(f"LED server listening on UDP port {UDP_PORT}")
print("Commands: ON / OFF")


try:
    while True:
        data, addr = sock.recvfrom(1024)

        command = data.decode("utf-8").strip().upper()

        print(f"Received '{command}' from {addr[0]}:{addr[1]}")

        if command == "ON":
            led_on()

        elif command == "OFF":
            led_off()

        else:
            print(f"Unknown command: {command}")

except KeyboardInterrupt:
    print("\nStopping LED server...")
    led_off()
    sock.close()
