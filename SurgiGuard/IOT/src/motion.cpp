#include <Arduino.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include "motion.h"

namespace {
Adafruit_MPU6050 mpu;
bool isReady = false;
float ax = 0, ay = 0, az = 0;
float prevX = 0, prevY = 0, prevZ = 0;
bool hasPrev = false;
float smoothActivity = 0;
int badReads = 0;

// Activité = variation de l'accélération entre deux lectures (indépendant
// de l'orientation du capteur et de la gravité).
const float THRESHOLD_LEGER = 0.3f;  // m/s²
const float THRESHOLD_AGITE = 1.5f;  // m/s²
const int REINIT_AFTER_BAD = 20;
}

namespace Motion {

bool begin() {
  isReady = mpu.begin(0x68, &Wire);
  if (isReady) mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  hasPrev = false;
  return isReady;
}

void update() {
  if (!isReady) {
    static unsigned long lastTry = 0;
    if (millis() - lastTry > 2000) {  // le capteur a décroché : on retente
      lastTry = millis();
      begin();
    }
    return;
  }
  sensors_event_t a, g, t;
  mpu.getEvent(&a, &g, &t);
  float x = a.acceleration.x, y = a.acceleration.y, z = a.acceleration.z;

  // Lecture I2C ratée : tout à zéro ou valeur hors de la plage +-8 g (78 m/s²)
  bool zero = (x == 0 && y == 0 && z == 0);
  bool outOfRange = fabsf(x) > 80 || fabsf(y) > 80 || fabsf(z) > 80;
  if (zero || outOfRange) {
    if (++badReads >= REINIT_AFTER_BAD) {
      badReads = 0;
      begin();  // tente de relancer le capteur
    }
    return;  // on garde la dernière bonne valeur
  }
  badReads = 0;

  ax = x; ay = y; az = z;
  if (hasPrev) {
    float d = sqrtf((x - prevX) * (x - prevX) + (y - prevY) * (y - prevY) + (z - prevZ) * (z - prevZ));
    smoothActivity = 0.9f * smoothActivity + 0.1f * d;
  }
  prevX = x; prevY = y; prevZ = z;
  hasPrev = true;
}

bool ready() { return isReady; }
float accelX() { return ax; }
float accelY() { return ay; }
float accelZ() { return az; }
float activity() { return smoothActivity; }

Level level() {
  if (smoothActivity >= THRESHOLD_AGITE) return AGITE;
  if (smoothActivity >= THRESHOLD_LEGER) return LEGER;
  return IMMOBILE;
}

const char* levelLabel() {
  switch (level()) {
    case AGITE: return "Agite";
    case LEGER: return "Leger mouvement";
    default: return "Immobile";
  }
}

}
