#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 21 15:47:58 2026

@author: jeffreymcnamee
"""

import serial
import time
import numpy as np

import communicationTools as comm
    
class controllerPID:
    def __init__ (self, PORT, heater_kp, heater_ki, heater_kd, cooler_kp, cooler_ki, cooler_kd, tau, heater_bool = True, cooler_bool = False):
        if heater_bool:
            self.heater_kp = heater_kp
            self.heater_ki = heater_ki
            self.heater_kd = heater_kd
            self.MAX = 255
        else:
            self.MAX = 0
            self.heater_kp = 0
            self.heater_ki = 0
            self.heater_kd = 0
            
        if cooler_bool:
            self.cooler_kp = cooler_kp
            self.cooler_ki = cooler_ki
            self.cooler_kd = cooler_kd
            self.MIN = -255
        else:
            self.MIN = 0
            self.cooler_kp = 0
            self.cooler_ki = 0
            self.cooler_kd = 0
            
        self.integral = 0
        self.port = PORT
        self.delay = tau
        self.RUN = True
        
    def controllerRun(self, target_temp):
        self.integral = 0
        arduino = serial.Serial(port=self.port, baudrate=9600, timeout=1)
        time.sleep(2)
    
        error = None
        while error is None:          # keep retrying the first read until it's valid
            temp = comm.readProbe(arduino)
            if temp is not None:
                error = target_temp - temp
    
        while self.RUN == True:
            prev_error = error
            temp = comm.readProbe(arduino)
            print(temp)
    
            if temp is None:
                # bad reading — skip this cycle, don't update PID state or send a signal
                time.sleep(self.delay)
                continue
    
            error = target_temp - temp
            signal = self.signalCalculator(error, prev_error)
            comm.sendSignal(arduino, signal)
            time.sleep(self.delay)

        
    def closeController(self):
        self.RUN = False
        return

    def signalCalculator(self, error, prev_error):
        
        if error < 0: 
            p_term = self.cooler_kp * error
        elif error >= 0:
            p_term = self.heater_kp * error

        potential_integral = self.integral + self.delay * error
        if potential_integral < 0: 
            i_term = self.cooler_ki * potential_integral
        elif potential_integral >= 0:
            i_term = self.heater_ki * potential_integral

        derivative = (error-prev_error) / self.delay
        if error < 0: 
            d_term = self.cooler_kd * derivative
        elif error >= 0:
            d_term = self.heater_kd * derivative

        raw_output = p_term + i_term + d_term

        is_saturated = raw_output <= self.MIN or raw_output >= self.MAX
        pushing_further = (error > 0 and raw_output >= self.MAX) or \
                           (error < 0 and raw_output <= self.MIN)

        if not (is_saturated and pushing_further):
            self.integral = potential_integral

        if self.integral < 0: 
            i_term = self.cooler_ki * self.integral
        elif self.integral >= 0:
            i_term = self.heater_ki * self.integral
            
        output = p_term + i_term + d_term
        
        if output<2:
            output=0
            
        print(max(self.MIN, min(output, self.MAX)))
        return max(self.MIN, min(output, self.MAX))

    
