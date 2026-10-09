# SPDX-FileCopyrightText: 2020 Bryan Siepert, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
import time
import socket

import board
import digitalio
import adafruit_bitbangio as bitbangio

from adafruit_bno08x import (
    BNO_REPORT_ACCELEROMETER,
    BNO_REPORT_GYROSCOPE,
    BNO_REPORT_MAGNETOMETER,
    BNO_REPORT_ROTATION_VECTOR,
)
from adafruit_bno08x.i2c import BNO08X_I2C

#UDP setup

sock =socket.socket(
    socket.AF_INET,
    socket.SOCK_DGRAM
)

#ipconfig
target = (
    "172.20.10.3", #self ip
    #172.26.173.84",
    6000
)


i2c = bitbangio.I2C(board.SCL, board.SDA, frequency=400000)
bno = BNO08X_I2C(i2c)

bno.enable_feature(BNO_REPORT_ACCELEROMETER)
bno.enable_feature(BNO_REPORT_GYROSCOPE)
bno.enable_feature(BNO_REPORT_MAGNETOMETER)
bno.enable_feature(BNO_REPORT_ROTATION_VECTOR)

print("BNO085 running - sending UDP data")


while True:
    time.sleep(0.05) #20hz
    

    accel_x, accel_y, accel_z = bno.acceleration
    #print("A ok")
    gyro_x, gyro_y, gyro_z = bno.gyro
    #print("G ok")
    mag_x, mag_y, mag_z = bno.magnetic
    #print("M ok")
    quat_i, quat_j, quat_k, quat_real = bno.quaternion
    #print("Q ok")

    
    #create packet
    message = (
        f"IMU:{accel_x},{accel_y},{accel_z},"   
        f"{gyro_x},{gyro_y},{gyro_z}," 
        f"{mag_x},{mag_y},{mag_z},"
        f"{quat_i},{quat_j},{quat_k},{quat_real}"
    )

    #print("sending:", message)

    #send packet
    sock.sendto(
        message.encode(),
        target
    )

    

