#ifndef AMBIENT_H
#define AMBIENT_H

// Température / humidité de la chambre (DHT11)
namespace Ambient {
void begin();
void update();  // à appeler dans loop(), lit le capteur toutes les 2 s
float temperature();  // °C, NAN si lecture invalide
float humidity();     // %, NAN si lecture invalide
}

#endif
