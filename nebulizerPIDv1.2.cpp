#include <SPI.h>
#include <Arduino.h>
#include "Adafruit_MAX31855.h"

const int heaterPin = 10;
const int coolerPin = 9;
const int max31855_CLK = 5;
const int max31855_CS  = 4;
const int max31855_DO  = 3;
Adafruit_MAX31855 thermocouple(max31855_CLK, max31855_CS, max31855_DO);

// checks serial for initiator signal.
void checkSerial() {
  String command = Serial.readStringUntil('\n');
  command.trim();

  int separatorIndex = command.indexOf(':');

  if (separatorIndex != -1){
    String actionPart = command.substring(0, separatorIndex);
    String valuePart = command.substring(separatorIndex + 1);

    int actionID = actionPart.toInt();
    int targetValue = valuePart.toInt();

    executeAction(actionID, targetValue);
  }
}

void executeAction(int action, int value){
  switch(action){
    case 1:
      temperatureReading();
      break;
    
    case 2:
      setWattage(value);
      
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
  if (scalar < 0){
    analogWrite(coolerPin, (int)(255*scalar))
    analogWrite(heaterPin, 0)
  }
  else if (scalar > 0){
    analogWrite(heaterPin, (int)(255*scalar));
    analogWrite(coolerPin, 0)
  }
}

void setup() {
  Serial.begin(9600);
  while (!Serial) {
    delay(10);
  }
  pinMode(heaterPin, OUTPUT);
  pinMode(coolerPin, OUTPUT);
}

void loop() {
  // check serial function to set a signal, if standby just keep repeating the loop
  while (Serial.available() == 0) {
    ;
  }
  checkSerial();
}
