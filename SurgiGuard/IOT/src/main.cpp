#include <Arduino.h>
#include <Wire.h>
#include "config.h"
#include "ambient.h"
#include "motion.h"
#include "vitals.h"
#include "network.h"

unsigned long lastPrint = 0;

void printReport() {
  Serial.println("==========================================");

  float t = Ambient::temperature();
  float h = Ambient::humidity();
  if (isnan(t)) {
    Serial.println("Chambre      : lecture DHT11 invalide");
  } else {
    Serial.printf("Chambre      : %.1f C | humidite %.0f %%\n", t, h);
  }

  if (!Vitals::ready()) {
    Serial.println("MAX30102     : capteur non detecte");
  } else if (!Vitals::fingerPresent()) {
    Serial.println("Pouls / SpO2 : placez le doigt sur le capteur...");
  } else {
    if (Vitals::bpm() > 0) Serial.printf("Pouls        : %.0f BPM\n", Vitals::bpm());
    else Serial.println("Pouls        : mesure en cours, doigt immobile...");
    if (Vitals::spo2() > 0) Serial.printf("SpO2         : %d %%\n", Vitals::spo2());
    else Serial.println("SpO2         : mesure en cours (~5 s)...");
  }

#if DEBUG_VITALS
  if (Vitals::ready()) {
    Serial.printf("[debug] IR=%ld Rouge=%ld battements=%d/5 spo2brut=%d\n", Vitals::lastIR(),
                  Vitals::lastRed(), Vitals::beatsCount(), Vitals::rawSpo2Status());
  }
#endif

  if (Vitals::ready() && !isnan(Vitals::dieTemperature())) {
    Serial.printf("Temp MAX30102: %.1f C (puce, pas corporelle)\n", Vitals::dieTemperature());
  }

  if (!Motion::ready()) {
    Serial.println("MPU6050      : capteur non detecte");
  } else {
    Serial.printf("Mouvement    : %s (activite %.2f m/s2)\n", Motion::levelLabel(), Motion::activity());
    Serial.printf("Accel        : X=%.1f Y=%.1f Z=%.1f m/s2\n", Motion::accelX(), Motion::accelY(), Motion::accelZ());
  }
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(500);
  Serial.println("\n--- Initialisation du systeme ---");

  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
  Wire.setClock(100000);

  Ambient::begin();
  Serial.println(Motion::begin() ? "MPU6050 OK" : "MPU6050 introuvable !");
  Serial.println(Vitals::begin() ? "MAX30102 OK" : "MAX30102 introuvable !");

  Network::begin();
}

void loop() {
  Vitals::update();  // doit tourner en continu pour ne pas perdre d'echantillons
  Motion::update();
  Ambient::update();

  if (millis() - lastPrint >= PRINT_PERIOD_MS) {
    lastPrint = millis();
    printReport();
    Network::publish(Ambient::temperature(), Ambient::humidity(), Vitals::bpm(),
                     Vitals::spo2(), Motion::activity(), Motion::levelLabel());
  }
}
