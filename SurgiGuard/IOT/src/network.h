#ifndef NETWORK_H
#define NETWORK_H

// WiFi + MQTT (actif seulement si ENABLE_MQTT == 1 dans config.h)
namespace Network {
void begin();
void publish(float temp, float hum, float bpm, int spo2, float activity, const char* motion);
}

#endif
