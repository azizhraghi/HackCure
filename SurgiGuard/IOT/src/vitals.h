#ifndef VITALS_H
#define VITALS_H

// Rythme cardiaque et SpO2 (MAX30102)
namespace Vitals {

bool begin();
void update();  // non bloquant, à appeler le plus souvent possible dans loop()
bool ready();
bool fingerPresent();
float bpm();   // 0 tant que non calibré
float dieTemperature();  // °C, temperature interne du MAX30102 (NAN si inconnue)
long lastIR();
long lastRed();
int beatsCount();     // battements valides collectes (5 requis)
int rawSpo2Status();  // valeur brute de l'algo (-999 = invalide)
int spo2();    // %, 0 tant que non calibré

}

#endif
