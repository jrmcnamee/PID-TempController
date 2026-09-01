#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 21 15:37:03 2026

@author: jeffreymcnameex
"""

import serial
import time

# 1. Open the serial port (Replace with your actual port path from Step 2)
# Timeout stops readline() from hanging forever if no data returns
arduino = serial.Serial(port='/dev/cu.usbmodem101', baudrate=9600, timeout=1)

# 2. Wait for Arduino to reset
# Opening a serial connection automatically reboots most Arduinos.
time.sleep(2) 

try:
    # 3. Send data to Arduino (Must be encoded to bytes)
    message = "Hello Arduino\n"
    arduino.write(message.encode('utf-8'))
    print(f"Sent to Arduino: {message.strip()}")

    # 4. Read the response back
    # readline() looks for the '\n' character sent by Serial.println()
    response_bytes = arduino.readline()
    
    # Decode bytes back into a human-readable Python string
    response_string = response_bytes.decode('utf-8').strip()
    print(f"Received from Arduino: {response_string}")

finally:
    # 5. Always close the port when finished
    arduino.close()
    print("Serial port closed.")
