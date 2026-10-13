# snakehead-communication-system
Raspberry Pi robot communication system for remote LED control, camera and audio streaming, and IMU data publishing through UDP and ROS 2.


# Overview

This project establishes communication between a Raspberry Pi and a laptop over a local Wi-Fi network. It combines UDP-based communication for real-time media streaming and remote hardware control with ROS 2 for IMU data publishing.

The system is organized into three subsystems:

LED control: Send ON/OFF commands from the laptop to control a NeoPixel LED strip connected to the Raspberry Pi.
Camera and audio streaming: Transmit camera video and microphone audio from the Raspberry Pi to the laptop for real-time playback and visualization.
IMU orientation: Read acceleration, angular velocity, magnetic field, and quaternion orientation from a BNO085 sensor and publish the measurements to a ROS 2 topic.


# System Architecture

LED Control: Laptop → UDP Command → Raspberry Pi Listener → NeoPixel Driver → LED Strip

Video: CSI Camera → Picamera2 → UDP → Laptop Receiver → OpenCV
Audio: Bluetooth Microphone → PipeWire → UDP → Laptop Receiver → Speaker

IMU: BNO085 → IMUstream.py → UDP → imu_bridge.py → ROS 2 /imu/data

The IMU streaming and bridge scripts run on the Raspberry Pi. ROS 2 runs inside a Docker container on the laptop, where the published topic can be inspected.

# Technologies and Libraries: 

Python for sensor acquisition, communication, and hardware control
UDP sockets for network communication
Picamera2 and OpenCV for camera capture and video display
PipeWire for audio input and streaming
Adafruit BNO08x libraries for IMU sensor communication
ROS 2 and rclpy for IMU message publishing
NeoPixel libraries for LED control
Docker for the pi's ROS 2 environment


# Repository Structure

```
snakehead-communication-system/

├── README.md
├── imu/
│  IMUstream.py
│   └── imu_bridge.py
├── media/
│   ├── m_camera_udp_commands.py
│   ├── m_audio_stream.py
│   └── media_receiver.py
├── led/
│   ├── LED_server.py
│   └── led_control.py
└── docs/
    ├── usage
    ├── environment tranfer
    ├── Report and steps.pdf
    └── environments/
        ├── ros_env1.yaml
        └── requirements.txt



#PI: 
IMUstream.py
imu_bridge.py
m_audio_stream.py
m_camera_udp_commands.py
led_server.py

#Laptop:
media_receiver.py
led_control.py

```

# Network Configuration

The Raspberry Pi and laptop communicate over the same local Wi-Fi network or phone hotspot. The scripts use UDP ports for their respective communication channels.

The laptop's IP address may change when reconnecting to the network. Verify the current addresses and update the relevant script configuration before starting the system.

# Documentation

usage: Startup sequence, commands, and verification steps for each subsystem.

environment transfer: commands to transfer environmets to a new laptop or a new pi

report and steps: Project hand off and further documentation

Developed as a robotics communication and integration project. The repository documents the implementation and handoff of the LED control, media streaming, and IMU communication subsystems.
