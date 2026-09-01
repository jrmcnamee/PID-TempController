#include <SPI.h>
#include "Adafruit_MAX31855.h"

const int max31855_CLK = 5;
const int max31855_CS  = 4;
const int max31855_DO  = 3;
Adafruit_MAX31855 thermocouple(max31855_CLK, max31855_CS, max31855_DO);

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
  delay(20);

}

void loop() {
    // put your main code here, to run repeatedly:
    double celsius = thermocouple.readCelsius();

    // Check if the library returns a "NaN" (Not a Number) error code
    if (isnan(celsius)) {
      Serial.println("Error: Something is wrong with the thermocouple probe!");

      // Read the exact error register bits to diagnose the issue
      uint8_t exceptionBits = thermocouple.readError();
      if (exceptionBits & MAX31855_FAULT_OPEN)      Serial.println(" - Fault: Connection is open (No probe attached).");
      if (exceptionBits & MAX31855_FAULT_SHORT_GND) Serial.println(" - Fault: Thermocouple shorted to Ground.");
      if (exceptionBits & MAX31855_FAULT_SHORT_VCC) Serial.println(" - Fault: Thermocouple shorted to VCC.");

    }
    else {
      Serial.println(celsius);
  }
  delay(1000);
}