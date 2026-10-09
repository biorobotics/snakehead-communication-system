import socket

PI_IP = "172.20.10.3"
PI_PORT = 6010

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def led_on():
    sock.sendto(b"ON", (PI_IP, PI_PORT))
    print("Sent: ON")


def led_off():
    sock.sendto(b"OFF", (PI_IP, PI_PORT))
    print("Sent: OFF")


while True:
    command = input("Enter ON, OFF, or Q: ").strip().upper()

    if command == "ON":
        led_on()

    elif command == "OFF":
        led_off()

    elif command == "Q":
        break

    else:
        print("Please enter ON, OFF, or Q.")


sock.close()