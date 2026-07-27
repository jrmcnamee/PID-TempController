#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 21 15:47:58 2026

@author: jeffreymcnamee
"""

import serial
import time
import numpy as np

k_p, k_i, k_d = 1.0, 0.0, 0.0   # tune these
dt = 1.0
out_min, out_max = -1.0, 1.0
epsilon = 0.01  # threshold for "close enough" to target

arduino = serial.Serial(port='/dev/tty.usbmodem1101', baudrate=9600, timeout=1)

integral = 0.0
max_step = 0.1  # max change in signal per control loop iteration
prev_signal = 0.0

def rateLimited(signal, prev_signal, max_step):
    delta = signal - prev_signal
    if abs(delta) > max_step:
        signal = prev_signal + max_step * np.sign(delta)
    return signal

def sendCommand(actionID, value):
    """Send a command to the Arduino."""
    delivery = f"{actionID}:{value}\n"
    arduino.write(delivery.encode('utf-8'))

def readProbe():
    """Ask Arduino for current temperature reading."""
    sendCommand(1, 0)  # 1 = probe command, value is ignored
    response_bytes = arduino.readline()
    return float(response_bytes.decode('utf-8'))


def normalizedSignalPID(kp, ki, kd, curr_error, prev_error, width):
    """
    Returns a signal in [-1, 1].
      output > 0 -> heat
      output < 0 -> cool
    Anti-windup: the integral term is only allowed to grow/shrink if doing
    so wouldn't just be "pushed further into" an already-saturated output.
    """
    global integral
    p_term = curr_error * kp
    potential_integral = integral + curr_error * dt
    i_term_tentative = potential_integral * ki
    derivative = (curr_error - prev_error) / dt
    d_term = derivative * kd
    total_tentative = p_term + i_term_tentative + d_term

    def bell_output(total):
        if total == 0:
            return 0.0
        return np.sign(total) * (1 - np.exp(-(total ** 2) / (2 * width ** 2)))

    raw_output = bell_output(total_tentative)

    is_saturated = raw_output - epsilon <= out_min or raw_output + epsilon >= out_max
    pushing_further = (curr_error > 0 and raw_output + epsilon >= out_max) or \
                       (curr_error < 0 and raw_output - epsilon <= out_min)

    if not (is_saturated and pushing_further):
        integral = potential_integral

    i_term = integral * ki
    total = p_term + i_term + d_term
    output = bell_output(total)

    return max(out_min, min(output, out_max))

def sendSignal(signal):
    """Send the heat/cool command, then the normalized (-1 to 1) scalar.
    Arduino's setWattage() does the *255 PWM conversion itself."""
    sendCommand(2, signal)  # 2 = heat/cool command, value is normalized signal


target_temp = float(input("enter temperature: "))
width = 30 / np.sqrt(-2 * np.log(0.01))  # tuned so total~30 -> output near max

error = target_temp - readProbe()

while True:
    prev_error = error

    current_temp = readProbe()
    error = target_temp - current_temp

    signal = normalizedSignalPID(k_p, k_i, k_d, error, prev_error, width)
    signal = rateLimited(signal, prev_signal, max_step)
    prev_signal = signal
    sendSignal(signal)

    time.sleep(dt)
    
