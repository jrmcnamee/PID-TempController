"""
Created on Sunday Aug 2nd 2026

@author: jeffreymcnamee
"""

def sendCommand(arduino, actionID, value):
    """Send a command to the Arduino."""
    delivery = f"{actionID}:{value}\n"
    arduino.write(delivery.encode('utf-8'))

def readProbe(arduino):
    """Ask Arduino for current temperature reading."""
    sendCommand(arduino, 1, 0)  # 1 = probe command, value is ignored
    response_bytes = arduino.readline()
    return float(response_bytes.decode('utf-8'))

def sendSignal(arduino, signal):
    """Send the heat/cool command, then the normalized (-1 to 1) scalar.
    Arduino's setWattage() does the *255 PWM conversion itself."""
    sendCommand(arduino, 2, signal)  # 2 = heat/cool command, value is normalized signal
