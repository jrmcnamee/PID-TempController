#include "pwm.h"

// ---------- pins (each one gates an IRLZ44N) ----------
#define HEATER_PIN  9
#define COOLER_PIN  6
#define ATOM_PIN    10

// ---------- safety limits ----------
const float OVERTEMP_C   = 80.0f;    // heater is locked out above this. Set ~15-20 C above your highest target.
const float SENSOR_MIN_C = -40.0f;   // readings outside this window = broken/disconnected probe
const float SENSOR_MAX_C = 250.0f;
const unsigned long TIMEOUT_MS = 2000;          // no serial for this long -> everything off
const unsigned long SAFETY_INTERVAL_MS = 200;

PwmOut heaterPwm(HEATER_PIN);
PwmOut coolerPwm(COOLER_PIN);
PwmOut atomPwm(ATOM_PIN);

float heaterFreq = 1000.0f;
float coolerFreq = 2000.0f;
float atomFreq   = 25000.0f;
float atomDuty   = 0.0f;       // percent, 0 = off

bool heaterLockout = false;
bool sensorFault   = false;
unsigned long lastCommandTime = 0;
unsigned long lastSafetyCheck = 0;

// ---------- helpers ----------
void allOff() {
  heaterPwm.pulse_perc(0.0f);
  coolerPwm.pulse_perc(0.0f);
  atomPwm.pulse_perc(0.0f);
}

// reads temperature (16-sample average to cut ADC noise)
double temperatureReading() {
  long sum = 0;
  for (int i = 0; i < 16; i++) sum += analogRead(A1);
  float raw = sum / 16.0f;
  float voltage = (raw / 16383.0f) * 5.0f;   // default AREF on Nano R4 is 5V
  return (voltage - 1.162f) / 0.005f;        // AD8495: Vout = Vref + 5mV/C * T
}

// signal arrives in the same -255..255 units the PID uses
void setWattage(float scalar) {
  float pct = constrain(fabs(scalar) / 255.0f * 100.0f, 0.0f, 100.0f);

  if (sensorFault) {                         // can't trust the probe: nothing thermal runs
    heaterPwm.pulse_perc(0.0f);
    coolerPwm.pulse_perc(0.0f);
    return;
  }
  if (scalar < 0) {
    coolerPwm.pulse_perc(pct);
    heaterPwm.pulse_perc(0.0f);
  } else if (scalar > 0) {
    heaterPwm.pulse_perc(heaterLockout ? 0.0f : pct);
    coolerPwm.pulse_perc(0.0f);
  } else {
    heaterPwm.pulse_perc(0.0f);
    coolerPwm.pulse_perc(0.0f);
  }
}

void setAtomizer(float dutyPct) {
  atomDuty = constrain(dutyPct, 0.0f, 100.0f);
  atomPwm.pulse_perc(atomDuty);
}

// re-initialize a channel at a new frequency; duty is 0 until the next command
void setFrequency(PwmOut &ch, float &store, float hz, float minHz, float maxHz) {
  hz = constrain(hz, minHz, maxHz);
  store = hz;
  ch.end();
  ch.begin(hz, 0.0f);
}

// independent of the PC: runs every SAFETY_INTERVAL_MS
void safetyCheck() {
  float t = temperatureReading();
  sensorFault = !(t > SENSOR_MIN_C && t < SENSOR_MAX_C);   // NaN also lands here
  if (t > OVERTEMP_C) heaterLockout = true;
  else if (t < OVERTEMP_C - 2.0f) heaterLockout = false;   // 2 C hysteresis

  if (sensorFault || heaterLockout) heaterPwm.pulse_perc(0.0f);
  if (sensorFault) coolerPwm.pulse_perc(0.0f);
  digitalWrite(LED_BUILTIN, (sensorFault || heaterLockout) ? HIGH : LOW);  // LED on = safety tripped
}

// ---------- command dispatch ----------
// 0: keepalive (no-op)      1: read temp
// 2: heat/cool (-255..255)  3: atomizer duty %
// 4: atomizer freq Hz       5: heater freq Hz      6: cooler freq Hz
void executeAction(int action, float value) {
  switch (action) {
    case 0: break;
    case 1: Serial.println(temperatureReading(), 3); break;
    case 2: setWattage(value); break;
    case 3: setAtomizer(value); break;
    case 4:
      setFrequency(atomPwm, atomFreq, value, 100.0f, 200000.0f);
      setAtomizer(atomDuty);
      break;
    case 5: setFrequency(heaterPwm, heaterFreq, value, 20.0f, 20000.0f); break;
    case 6: setFrequency(coolerPwm, coolerFreq, value, 20.0f, 20000.0f); break;
  }
}

// checks serial for a "action:value" line
void checkSerial() {
  String command = Serial.readStringUntil('\n');
  command.trim();

  int sep = command.indexOf(':');
  if (sep != -1) {
    int actionID = command.substring(0, sep).toInt();
    float v = command.substring(sep + 1).toFloat();
    executeAction(actionID, v);
  }
}

void setup() {
  Serial.begin(9600);
  Serial.setTimeout(100);
  while (!Serial) delay(10);
  pinMode(LED_BUILTIN, OUTPUT);
  analogReadResolution(14);
  heaterPwm.begin(heaterFreq, 0.0f);
  coolerPwm.begin(coolerFreq, 0.0f);
  atomPwm.begin(atomFreq, 0.0f);
}

void loop() {
  if (Serial.available() > 0) {
    checkSerial();
    lastCommandTime = millis();
  } else if (millis() - lastCommandTime > TIMEOUT_MS) {
    allOff();   // watchdog: kill everything if the PC goes silent
  }

  if (millis() - lastSafetyCheck >= SAFETY_INTERVAL_MS) {
    lastSafetyCheck = millis();
    safetyCheck();
  }
}
