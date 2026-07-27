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
    Returns a heater signal in [0, 1].

    curr_error = target - current_temp
      curr_error > 0  -> too cold, need heat
      curr_error <= 0 -> at/above target, no heat (heater can't cool!)

    Only the positive side of the error uses the bell-curve response;
    negative error (overshoot) is forced to 0 output.

    Anti-windup: the integral term is only allowed to grow/shrink if doing
    so wouldn't just be "pushed further into" an already-saturated output.
    """
    global integral

    p_term = curr_error * kp

    # Tentatively update the integral -- don't commit yet.
    potential_integral = integral + curr_error * dt
    i_term_tentative = potential_integral * ki

    derivative = (curr_error - prev_error) / dt
    d_term = derivative * kd

    total_tentative = p_term + i_term_tentative + d_term

    raw_output = (total_tentative/abs(total_tentative)) - np.exp(-(total_tentative ** 2) / (2 * width ** 2))

    # Is the *actual* output saturated at a bound?
    is_saturated = raw_output - epsilon <= out_min or raw_output + epsilon >= out_max
    # Is the error still pushing further into that same saturated bound?
    pushing_further = (curr_error > 0 and raw_output + epsilon >= out_max) or \
                       (curr_error < 0 and raw_output - epsilon <= out_min)

    # Only update the integral if doing so wouldn't just be "pushed further into" an already-saturated output.
    if not (is_saturated and pushing_further):
        integral = potential_integral

    # Recompute with whatever integral we actually committed to.
    i_term = integral * ki
    total = p_term + i_term + d_term

    output = 1 - np.exp(-(total ** 2) / (2 * width ** 2))
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
    sendSignal(signal)

    time.sleep(dt)
    
