// Copier ce fichier en config.h (ignoré par git) et renseigner le Wi-Fi.
#ifndef CONFIG_H
#define CONFIG_H

// ---------- Broches ----------
#define PIN_I2C_SDA 21 // MPU6050 + MAX30102
#define PIN_I2C_SCL 22
#define PIN_DHT 4 // DHT11 : doit etre une broche de sortie (PAS 34-39)
#define DHT_TYPE DHT11

// ---------- Moniteur série ----------
#define SERIAL_BAUD 115200
#define PRINT_PERIOD_MS 1000
#define DEBUG_VITALS 1 // affiche IR/rouge bruts pour verifier le signal

// ---------- Réseau ----------
#define ENABLE_MQTT 1

// Identifiant du boitier : a enregistrer sur le patient (PUT /api/patients/me/device)
#define DEVICE_ID "ESP32_001"
#define MQTT_CLIENT_ID "ESP32_SurgiGuard_001"

// Wi-Fi 2,4 GHz uniquement (l'ESP32 ne voit pas le 5 GHz)
#define WIFI_SSID "VOTRE_RESEAU_2_4GHZ"
#define WIFI_PASSWORD "VOTRE_MOT_DE_PASSE"

#define MQTT_BROKER "h1211a42.ala.eu-central-1.emqxsl.com"
#define MQTT_PORT 8883
#define MQTT_USER "HackcureUser"
#define MQTT_PASS "Hackcure"
#define MQTT_TOPIC_DATA "Hackcure/data"

#endif
