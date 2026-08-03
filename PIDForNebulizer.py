#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 21 15:47:58 2026

@author: jeffreymcnamee
"""

import serial
import time
import numpy as np

import communicationTools
    
class controllerPID:
    def __init__ (self, PORT, heater_kp, heater_ki, heater_kd, cooler_kp, cooler_ki, cooler_kd, tau, heater_bool = True, cooler_bool = False):
        if heater_bool:
            self.heater_kp = heater_kp
            self.heater_ki = heater_ki
            self.heater_kd = heater_kd
            self.MAX = 255
        else:
            self.MAX = 0
            
        if cooler_bool:
            self.cooler_kp = cooler_kp
            self.cooler_ki = cooler_ki
            self.cooler_kd = cooler_kd
            self.MIN = -255
        else:
            self.MIN = 0
            
        self.integral = 0
        self.port = PORT
        self.delay = tau
        self.RUN = True
        
    def controllerRun (target_temp):
        self.integral = 0
        arduino = serial.Serial(port=self.port, baudrate=9600, timeout=1)
        error = target_temp - readProbe(arduino)

        while self.RUN == True:
            prev_error = error
            error = target_temp - readProbe(arduino)
    `       
            signal = self.signalCalculator(error, prev_error)
            sendSignal(arduino, signal)

        
    def closeController():
        self.RUN = False
        return

    def signalCalculator(error, prev_error):
        
        if error < 0: 
            p_term = self.cooler_kp * error
        else if error >= 0:
            p_term = self.heater_kp * error

        potential_integral = self.integral + self.delay * error
        if potential_integral < 0: 
            i_term = self.cooler_ki * potential_integral
        else if potential_integral >= 0:
            i_term = self.heater_ki * potential_integral

        derivative = (error-prev_error) / self.delay
        if error < 0: 
            d_term = self.cooler_kd * derivative
        else if error >= 0:
            d_term = self.heater_kd * derivative

        raw_output = p_term + i_term + d_term

        is_saturated = raw_output <= self.MIN or raw_output >= self.MAX
        pushing_further = (error > 0 and raw_output >= self.MAX) or \
                           (error < 0 and raw_output <= self.MIN)

        if not (is_saturated and pushing_further):
            self.integral = potential_integral

        i_term = k_i * self.integral
        output = p_term + i_term + d_term
        return output

    
