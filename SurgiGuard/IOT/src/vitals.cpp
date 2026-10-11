#include <Arduino.h>
#include "MAX30105.h"
#include "heartRate.h"
#include "spo2_algorithm.h"
#include "vitals.h"

// Méthode du tutoriel Random Nerd Tutorials :
//  - BPM : checkForBeat() de SparkFun + moyenne des 5 derniers battements valides
//  - SpO2 : maxim_heart_rate_and_oxygen_saturation() sur 100 échantillons
// Le capteur tourne à 100 Hz (400 Hz / moyenne 4) pour checkForBeat ;
// l'algorithme SpO2 attend 25 Hz, on lui passe donc 1 échantillon sur 4.

namespace {
MAX30105 sensor;
bool isReady = false;
bool finger = false;

const long FINGER_THRESHOLD = 20000;  // sans doigt l'IR est ~250-3000
const long CONTACT_MIN = 8000;        // contact leger : on augmente la LED sans encore valider le doigt

// Réglage automatique de la LED : on vise un IR entre IR_LOW et IR_HIGH
// (18 bits = 262143 max ; au-delà le signal sature et le pouls disparait)
const long IR_HIGH = 180000;
const long IR_LOW = 40000;
byte ledPower = 20;
unsigned long lastLedAdjust = 0;

// ---- BPM ----
const byte RATE_SIZE = 5;
const float MIN_BPM = 45;
const float MAX_BPM = 180;
byte rates[RATE_SIZE];
byte rateSpot = 0;
byte validBeats = 0;
unsigned long lastBeat = 0;
int averageBPM = 0;

// ---- SpO2 ----
const int DECIMATION = 4;   // 100 Hz -> 25 Hz
const int SHIFT = 25;       // recalcul toutes les secondes
uint32_t irBuffer[BUFFER_SIZE];
uint32_t redBuffer[BUFFER_SIZE];
int bufCount = 0;
int sinceCompute = 0;
int decimCount = 0;
uint64_t irAcc = 0, redAcc = 0;
int spo2Val = 0;
int rawSpo2 = -999;
long lastIr = 0, lastRedVal = 0;

// ---- Température interne ----
float dieTemp = NAN;
unsigned long lastTempRead = 0;
const unsigned long TEMP_PERIOD_MS = 2000;

void resetMeasurement() {
  rateSpot = 0;
  validBeats = 0;
  lastBeat = 0;
  averageBPM = 0;
  bufCount = 0;
  sinceCompute = 0;
  decimCount = 0;
  irAcc = redAcc = 0;
  spo2Val = 0;
}

void onBeat() {
  unsigned long now = millis();
  if (lastBeat != 0) {
    float bpm = 60.0f / ((now - lastBeat) / 1000.0f);
    if (bpm >= MIN_BPM && bpm <= MAX_BPM) {
      rates[rateSpot] = (byte)bpm;
      rateSpot = (rateSpot + 1) % RATE_SIZE;
      if (validBeats < RATE_SIZE) validBeats++;
      if (validBeats >= RATE_SIZE) {
        int sum = 0;
        for (byte i = 0; i < RATE_SIZE; i++) sum += rates[i];
        averageBPM = sum / RATE_SIZE;
      }
    }
  }
  lastBeat = now;
}

void computeSpo2() {
  int32_t spo2, heartRate;
  int8_t validSpo2, validHr;
  maxim_heart_rate_and_oxygen_saturation(irBuffer, BUFFER_SIZE, redBuffer,
                                         &spo2, &validSpo2, &heartRate, &validHr);
  rawSpo2 = validSpo2 ? spo2 : -999;
  if (validSpo2 && spo2 >= 70 && spo2 <= 100) spo2Val = spo2;
}

void addSpo2Sample(uint32_t ir, uint32_t red) {
  irAcc += ir;
  redAcc += red;
  if (++decimCount < DECIMATION) return;
  uint32_t irAvg = irAcc / DECIMATION;
  uint32_t redAvg = redAcc / DECIMATION;
  irAcc = redAcc = 0;
  decimCount = 0;

  if (bufCount == BUFFER_SIZE) {  // fenêtre glissante
    memmove(irBuffer, irBuffer + 1, (BUFFER_SIZE - 1) * sizeof(uint32_t));
    memmove(redBuffer, redBuffer + 1, (BUFFER_SIZE - 1) * sizeof(uint32_t));
    bufCount--;
  }
  irBuffer[bufCount] = irAvg;
  redBuffer[bufCount] = redAvg;
  bufCount++;

  if (bufCount == BUFFER_SIZE && ++sinceCompute >= SHIFT) {
    sinceCompute = 0;
    computeSpo2();
  }
}
}

namespace Vitals {

bool begin() {
  isReady = sensor.begin(Wire, I2C_SPEED_STANDARD);
  if (!isReady) return false;

  byte ledBrightness = ledPower;
  byte sampleAverage = 4;
  byte ledMode = 2;       // Rouge + IR
  int sampleRate = 400;   // /4 -> 100 Hz effectifs
  int pulseWidth = 411;
  int adcRange = 16384;
  sensor.setup(ledBrightness, sampleAverage, ledMode, sampleRate, pulseWidth, adcRange);
  return true;
}

void update() {
  if (!isReady) return;

  if (millis() - lastTempRead >= TEMP_PERIOD_MS) {
    lastTempRead = millis();
    float t = sensor.readTemperature();  // bloque ~30 ms
    if (t > 10 && t < 60) dieTemp = t;   // ignore les lectures I2C ratees (0.0)
  }

  sensor.check();
  while (sensor.available()) {
    uint32_t red = sensor.getFIFORed();
    uint32_t ir = sensor.getFIFOIR();
    sensor.nextSample();
    lastIr = ir;
    lastRedVal = red;

    // Ajuste la puissance des LED (au plus une fois par 500 ms), des qu'il y a un contact
    // (meme leger) : sinon un doigt peu appuye reste sous le seuil et la LED n'augmente jamais.
    if (ir >= CONTACT_MIN && millis() - lastLedAdjust > 500) {
      byte target = ledPower;
      if (ir > IR_HIGH && ledPower > 2) target = ledPower > 10 ? ledPower - 5 : ledPower - 1;
      else if (ir < IR_LOW && ledPower < 200) target = ledPower + 5;
      if (target != ledPower) {
        ledPower = target;
        sensor.setPulseAmplitudeRed(ledPower);
        sensor.setPulseAmplitudeIR(ledPower);
      }
      lastLedAdjust = millis();
    }

    if (ir < FINGER_THRESHOLD) {
      if (finger) resetMeasurement();
      finger = false;
      continue;
    }
    finger = true;

    if (checkForBeat(ir)) onBeat();
    addSpo2Sample(ir, red);
  }
}

bool ready() { return isReady; }
bool fingerPresent() { return finger; }
float bpm() { return averageBPM; }
int spo2() { return spo2Val; }
long lastIR() { return lastIr; }
long lastRed() { return lastRedVal; }
int beatsCount() { return validBeats; }
int rawSpo2Status() { return rawSpo2; }
float dieTemperature() { return dieTemp; }

}
