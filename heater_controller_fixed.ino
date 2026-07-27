#include <SPI.h>
#include <Arduino.h>
#include "Adafruit_MAX31855.h"

const int heaterPin = 10;
const int max31855_CLK = 5;
const int max31855_CS  = 4;
const int max31855_DO  = 3;
Adafruit_MAX31855 thermocouple(max31855_CLK, max31855_CS, max31855_DO);

// this is housekeeping. Don't worry about it.

enum class SignalState {
  Heater,
  Probe,
  Standby
};

// Shared across setup()/loop()/checkSerial() — must be file-scope, not local.
SignalState signal_ = SignalState::Standby;

// checks serial for initiator signal.
void checkSerial() {
  String command = Serial.readStringUntil('\n');
  command.trim();

  if (command == "heat") {
    signal_ = SignalState::Heater;
  }
  else if (command == "probe") {
    signal_ = SignalState::Probe;
  }
  else {
    signal_ = SignalState::Standby;
  }
}

// reads temperature and sends it back to loop
double temperatureReading() {
  double celsius = thermocouple.readCelsius();

  // Check if the library returns a "NaN" (Not a Number) error code
  if (isnan(celsius)) {
    Serial.println("Error: Something is wrong with the thermocouple probe!");

    // Read the exact error register bits to diagnose the issue
    uint8_t exceptionBits = thermocouple.readError();
    if (exceptionBits & MAX31855_FAULT_OPEN)      Serial.println(" - Fault: Connection is open (No probe attached).");
    if (exceptionBits & MAX31855_FAULT_SHORT_GND) Serial.println(" - Fault: Thermocouple shorted to Ground.");
    if (exceptionBits & MAX31855_FAULT_SHORT_VCC) Serial.println(" - Fault: Thermocouple shorted to VCC.");

    return NAN;
  }
  else {
    return celsius;
  }
}

// sets the wattage by multiplying the computer signal by the max PWM value
void setWattage(float scalar) {
  scalar = constrain(scalar, 0.0, 1.0);
  analogWrite(heaterPin, (int)(255 * scalar));
}

void setup() {
  Serial.begin(9600);
  while (!Serial) {
    delay(10);
  }
  pinMode(heaterPin, OUTPUT);
}

void loop() {
  // check serial function to set a signal, if standby just keep repeating the loop
  while (Serial.available() == 0) {
    ;
  }
  checkSerial();

  if (signal_ == SignalState::Probe) {
    double reading = temperatureReading();
    Serial.println(reading); // sent as human-readable text; Python side does float(line)
  }
  else if (signal_ == SignalState::Heater) {
    while (Serial.available() == 0) {
      delay(10);
    }
    // Expecting the scalar sent as text, e.g. "0.75\n"
    float normSignal = Serial.parseFloat();
    setWattage(normSignal);
  }
  else if (signal_ == SignalState::Standby) {
    return;
  }
}
