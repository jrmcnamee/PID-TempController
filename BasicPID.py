# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import matplotlib.pyplot as plt

class PIDController:
    def __init__(self, kp, ki, kd, setpoint=0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.integral = 0
        self.prev_error = 0

    def update(self, measured_value, dt):
        error = self.setpoint - measured_value
        p_term = self.kp * error
        
        self.integral += error * dt
        i_term = self.ki * self.integral

        derivative = (error - self.prev_error) / dt if dt > 0 else 0
        d_term = self.kd * derivative

        self.prev_error = error
        return p_term + i_term + d_term


# Setup
pid = PIDController(kp=1.2, ki=0.1, kd=0.93975, setpoint=100)
# Kp 1.2, ki 0.1, kd 0.93975 produces a state where the signal bounces between +/- 1031.1936065995408

dt = 0.1
n_steps = 10000
current_value = 0
time_data = []
value_data = []
setpoint_data = []
control_data = []

for step in range(n_steps):
    t = step * dt
    control_value = pid.update(current_value, dt)
    print(control_value)
    current_value += control_value * dt  # simple system model

    time_data.append(t)
    value_data.append(current_value)
    setpoint_data.append(pid.setpoint)
    control_data.append(control_value)

# Plot
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7), sharex=True)

ax1.plot(time_data, value_data, label="OVR Value", linewidth=2)
ax1.plot(time_data, setpoint_data, '--', label="Setpoint", color="gray")
ax1.set_ylabel("Value")
ax1.set_title("PID Response")
ax1.legend()
ax1.grid(True)

ax2.plot(time_data, control_data, label="Control Signal", color="orange")
ax2.set_xlabel("Time (s)")
ax2.set_ylabel("Control Signal")
ax2.legend()
ax2.grid(True)

plt.tight_layout()
plt.show()