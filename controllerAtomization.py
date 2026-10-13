import threading
import serial
import time
import numpy as np

import communicationTools as comm
import livePlot


class controllerAtomization:
    def __init__ (self, PORT, heater_kp, heater_ki, heater_kd, cooler_kp, cooler_ki, cooler_kd, tau, heater_bool, cooler_bool,
                  heater_freq=1000, cooler_freq=2000, atom_freq=25000, atom_onset=0):
        # The Arduino kills all outputs after 2 s of silence, and the loop sends a command every cycle.
        if tau >= 1.5:
            raise ValueError("tau must be below 1.5 s or the Arduino watchdog will switch everything off.")

        if heater_bool:
            self.heater_kp = heater_kp
            self.heater_ki = heater_ki
            self.heater_kd = heater_kd
            self.MAX = 50
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
        self.pause = False                 # was never initialised before
        self.thread = None
        self.atom_onset = atom_onset       # lowest duty (%) at which the atomizer actually makes mist
        self.log = livePlot.TempLog()

        self.arduino = serial.Serial(port=self.port, baudrate=9600, timeout=1)
        time.sleep(2)                      # let the Nano finish resetting after the port opens
        comm.setHeaterFreq(self.arduino, heater_freq)
        comm.setCoolerFreq(self.arduino, cooler_freq)
        comm.setAtomizerFreq(self.arduino, atom_freq)

    def controllerRun(self, target_temp):
        self.integral = 0
        self.RUN = True
        self.pause = False
        self.log.reset()

        # args needs the trailing comma, otherwise the float is unpacked as the argument list
        self.thread = threading.Thread(target=self.controllerLoop, args=(target_temp,), daemon=True)
        self.thread.start()

    def controllerLoop(self, targ):
        error = None
        while error is None and self.RUN:          # keep retrying the first read until it's valid
            temp = comm.readProbe(self.arduino)
            if temp is not None:
                error = targ - temp
                self.log.add(temp, targ, 0.0)
        if not self.RUN:
            return

        while self.RUN == True:
            while self.pause == True and self.RUN:
                time.sleep(1.3)
            prev_error = error
            temp = comm.readProbe(self.arduino)
            print(temp)

            if temp is None:
                # bad reading — skip this cycle, don't update PID state or send a signal
                time.sleep(self.delay)
                continue

            error = targ - temp
            signal = self.signalCalculator(error, prev_error)
            comm.sendSignal(self.arduino, signal)
            self.log.add(temp, targ, signal)
            time.sleep(self.delay)

    def controllerPause(self, logic):
        if logic:
            self.pause = True
        if not logic:
            self.pause = False

    def closeController(self):
        self.RUN = False
        if self.thread is not None:
            self.thread.join(timeout=3)
        if self.arduino.is_open:
            comm.sendSignal(self.arduino, 0)
            comm.setAtomizerDuty(self.arduino, 0)
            self.log.set_atomizer(0)
            self.arduino.flush()
            self.arduino.close()

    # ---- atomizer controls (replace the old atomizerShift) ----
    def atomizerOn(self, duty=50):
        """Raw PWM duty, 0-100 %."""
        duty = max(0.0, min(100.0, duty))
        comm.setAtomizerDuty(self.arduino, duty)
        self.log.set_atomizer(duty)

    def atomizerOff(self):
        self.atomizerOn(0)

    def atomizerLevel(self, level):
        """Mist level 0..1, mapped onto [atom_onset, 100] % duty so the whole range is usable. 0 = off."""
        level = max(0.0, min(1.0, level))
        duty = 0 if level == 0 else self.atom_onset + level * (100 - self.atom_onset)
        self.atomizerOn(duty)

    def atomizerSetFreq(self, hz):
        comm.setAtomizerFreq(self.arduino, hz)

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


        print(max(self.MIN, min(output, self.MAX)))
        return max(self.MIN, min(output, self.MAX))
