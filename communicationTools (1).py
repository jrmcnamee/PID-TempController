import math
import threading

# The PID thread and the main thread share one serial port, so every access goes through this lock.
_lock = threading.RLock()


def sendCommand(arduino, actionID, value):
    """Send a command to the Arduino."""
    # fixed-point formatting: Python would otherwise print tiny values like 1e-05, which the Arduino may misparse
    delivery = f"{actionID}:{float(value):.3f}\n"
    with _lock:
        arduino.write(delivery.encode('utf-8'))


def readProbe(arduino):
    with _lock:
        arduino.reset_input_buffer()          # drop stale lines
        sendCommand(arduino, 1, 0)
        response_bytes = arduino.readline()
    try:
        value = float(response_bytes.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return None   # signal "bad read" explicitly instead of returning a string
    return value if math.isfinite(value) else None


def ping(arduino):
    """Keepalive: resets the Arduino's 2 s watchdog without changing any output."""
    sendCommand(arduino, 0, 0)


def sendSignal(arduino, signal):
    """Heat/cool command in PID units (-255..255). Arduino converts to PWM duty itself."""
    sendCommand(arduino, 2, signal)


def setAtomizerDuty(arduino, pct):        # 0..100
    sendCommand(arduino, 3, pct)


def setAtomizerFreq(arduino, hz):
    sendCommand(arduino, 4, hz)


def setHeaterFreq(arduino, hz):
    sendCommand(arduino, 5, hz)


def setCoolerFreq(arduino, hz):
    sendCommand(arduino, 6, hz)
