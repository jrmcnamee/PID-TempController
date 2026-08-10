#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 21 15:47:58 2026

@author: jeffreymcnamee
"""

import serial
import time
import numpy as np

import communicationTools as comm ##functions in communicationTools.py are used for serial communication with the Arduino. These are the functions readProbe and sendSignal.
    
class controllerPID:
    def __init__ (self, PORT, heater_kp, heater_ki, heater_kd, cooler_kp, cooler_ki, cooler_kd, tau, heater_bool = True, cooler_bool = False):
        """
        Initializes the PID controller with the given parameters. 
        If heater_bool is True, the controller will use the provided heater PID parameters.
        If cooler_bool is True, the controller will use the provided cooler PID parameters.
        Otherwise, the controller will not use the corresponding PID parameters and will set the output limits accordingly.
        """
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
        """
        Runs the PID controller to maintain the target temperature.
        Call this function to start the controller. It will continuously read the temperature from the probe, calculate the PID signal, and send it to the Arduino until the controller is stopped.
        """
        self.integral = 0
        arduino = serial.Serial(port=self.port, baudrate=9600, timeout=1) ##this function opens the serial port to communicate with the Arduino. The baudrate and timeout are set to match the Arduino's settings.
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
        """
        For the purpose of this tutorial, ignore this function and stop the controller by using the red box in the top right corner of the Kernel.
        In a real application, the controllerRun function would be running in a separate thread, and this function would be called to stop the controller gracefully.
        """
        self.RUN = False
        return

    def signalCalculator(self, error, prev_error):
        """
        This is the PID algorithm, nearly everything else is for the purpose of reading the temperature and sending the signal to the Arduino.
        If you want to change the PID parameters, do it in the __init__ function. If you want to change the delay between readings, do it in the __init__ function. 
        If you want to change the target temperature, do it in the controllerRun function.
        This function calculates the PID output using the independent gain equation. It also utilizes anti-windup to prevent the integral term from growing 
        too large when the output is saturated. The integral term is only updated when the output is not saturated or when the error is pushing the output back towards the unsaturated range.

        IT IS RECCOMENDED TO GET YOUR PID TO WORK WITH P AND I GAIN FIRST. START WITH D AT 0.
        """
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
