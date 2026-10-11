#include <Arduino.h>
#include <DHT.h>
#include "ambient.h"
#include "config.h"

namespace {
DHT dht(PIN_DHT, DHT_TYPE);
float temp = NAN;
float hum = NAN;
unsigned long lastRead = 0;
const unsigned long READ_PERIOD_MS = 2000;  // le DHT11 ne supporte pas plus vite
}

namespace Ambient {

void begin() {
  dht.begin();
}

void update() {
  if (millis() - lastRead < READ_PERIOD_MS) return;
  lastRead = millis();
  temp = dht.readTemperature();
  hum = dht.readHumidity();
}

float temperature() { return temp; }
float humidity() { return hum; }

}
