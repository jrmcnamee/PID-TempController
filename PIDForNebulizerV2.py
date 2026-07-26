#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jul 24 11:19:01 2026

@author: jeffreymcnamee
"""
import numpy as np

class Atomizer:
    """
    generates an object of class atomizer. permits the addition of unlimited atomizers,
    as long as the system is identifiable to the arduino. 
    
    can also be assigned a "preference" which allows you to choose the nebulizer, 
    as long as you know its respective pin and characteristic arduino.
    """
    
    def __init__(self, power, atomizerID):
        self.power;
        self.atomizerID = id(self.atomizerID)
        

class temperaturePID:
    """
    generates an object of class PID. permits the addition of unlimited PID controllers,
    as long as the system is identifiable to the arduino. 
    
    can also be assigned a "preference" which allows you to choose the nebulizer, 
    as long as you know its respective pin and characteristic arduino.
    
    Further, customizability as a cooler, heater, or full range temperature control.
    """
    
    def __init__(self, kp, ki, kd, probeID, heaterID, coolerID, dt = 1, integral = 0.0, heaterBool=True, coolerBool=True):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral = integral
        self.dt = dt
        self.probeID = id(self.id)
        if (heaterBool):                                                        #if-loops check the boolean that determines
            self.heaterID = id(self.heaterID)                                   #if our PID thinks about cooling, heating, or both.
        else:
            self.heaterID = 0
        if (coolerBool):
            self.coolerID = id(self.CoolerID)
        else:
            self.coolerID = 0
            
        if heaterBool and coolerBool:
            self.out_min, self.out_max = -1, 1
        elif heaterBool and not coolerBool:
            self.out_min, self.out_max = 0, 1
        elif coolerBool and not heaterBool:
            self.out_min, self.out_max = -1, 0
        else:
            self.out_min, self.out_max = 0, 0
            
        
    def signalCalculator(self, curr_error, prev_error, width):

        p_term = curr_error * self.kp

        # Tentatively update the integral -- don't commit yet.
        potential_integral = self.integral + curr_error * self.dt
        i_term_tentative = potential_integral * self.ki

        derivative = (curr_error - prev_error) / self.dt
        d_term = derivative * self.kd

        total_tentative = p_term + i_term_tentative + d_term

        if total_tentative <= 0:  ##CURRENTLY WRONG
            raw_output = 0.0
        else:
            raw_output = 1 - np.exp(-(total_tentative ** 2) / (2 * width ** 2))

        # Is the *actual* output saturated at a bound?
        is_saturated = raw_output <= self.out_min or raw_output >= self.out_max
        # Is the error still pushing further into that same saturated bound?
        pushing_further = (curr_error > 0 and raw_output >= self.out_max) or \
                           (curr_error < 0 and raw_output <= self.out_min)

        if not (is_saturated and pushing_further):
            self.integral = potential_integral

        # Recompute with whatever integral we actually committed to.
        i_term = self.integral * self.ki
        total = p_term + i_term + d_term

        if total <= 0:
            return 0.0

        output = 1 - np.exp(-(total ** 2) / (2 * width ** 2))
        return max(self.out_min, min(output, self.out_max))
        