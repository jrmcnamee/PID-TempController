import threading
import time

import livePlot
from controllerAtomization import controllerAtomization

# ---------------- settings ----------------
PORT = "COM3"              # e.g. "COM3" on Windows, "/dev/ttyACM0" on Linux, "/dev/cu.usbmodem..." on macOS
TARGET = 37.0              # °C
TOL = 0.5                  # ± band you count as "at target"
TAU = 0.5                  # control loop period (s); must stay below 1.5

RUN_DURATION_S = 600       # plot window closes itself after this (close it earlier by hand if you like)
ATOM_ON_AT_S = 180         # turn mist on after the vial has settled...
ATOM_OFF_AT_S = 480        # ...and off again, so the figure shows the temperature holding with mist running
ATOM_LEVEL = 0.6           # 0..1, mapped onto [ATOM_ONSET, 100] % duty
ATOM_FREQ = 25000          # Hz, replace with the winner from atomizerSweep.py
ATOM_ONSET = 0             # %, replace with the onset duty from atomizerSweep.py

# ---------------- build the controller ----------------
ctrl = controllerAtomization(
    PORT,
    heater_kp=20, heater_ki=0.5, heater_kd=0,      # REPLACE with your tuned gains
    cooler_kp=20, cooler_ki=0.5, cooler_kd=0,      # (cooler gains act on negative error)
    tau=TAU, heater_bool=True, cooler_bool=True,
    heater_freq=1000, cooler_freq=2000,
    atom_freq=ATOM_FREQ, atom_onset=ATOM_ONSET,
)

timers = [
    threading.Timer(ATOM_ON_AT_S, ctrl.atomizerLevel, args=(ATOM_LEVEL,)),
    threading.Timer(ATOM_OFF_AT_S, ctrl.atomizerOff),
]
prefix = time.strftime("run_%Y%m%d_%H%M%S")

# ---------------- run ----------------
try:
    ctrl.controllerRun(TARGET)
    for t in timers:
        t.start()
    # blocks until the window closes or RUN_DURATION_S passes
    livePlot.run_live_plot(ctrl.log, TARGET, tol=TOL, duration_s=RUN_DURATION_S)
finally:
    # always runs, even on Ctrl+C or a crash: outputs off, port closed, data saved
    for t in timers:
        t.cancel()
    ctrl.closeController()
    livePlot.save_report(ctrl.log, TARGET, tol=TOL, prefix=prefix)
