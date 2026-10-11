#include <Arduino.h>
#include "network.h"
#include "config.h"

#if ENABLE_MQTT

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>

namespace {
WiFiClientSecure espClient;
PubSubClient client(espClient);
unsigned long lastAttempt = 0;
const unsigned long RETRY_MS = 5000;  // evite de bloquer la lecture des capteurs

void ensureConnected() {
  if (WiFi.status() != WL_CONNECTED) {  // l'ESP32 se reconnecte seul (WiFi.setAutoReconnect)
    static unsigned long lastWifiLog = 0;
    if (millis() - lastWifiLog > RETRY_MS) {
      lastWifiLog = millis();
      Serial.printf("WiFi : connexion a \"%s\"... (etat %d)\n", WIFI_SSID, (int)WiFi.status());
    }
    return;
  }
  static bool ipShown = false;
  if (!ipShown) { ipShown = true; Serial.printf("WiFi OK : IP %s\n", WiFi.localIP().toString().c_str()); }
  if (client.connected()) return;
  if (millis() - lastAttempt < RETRY_MS) return;
  lastAttempt = millis();
  Serial.print("MQTT : connexion... ");
  if (client.connect(MQTT_CLIENT_ID, MQTT_USER, MQTT_PASS)) Serial.println("OK");
  else Serial.printf("echec (etat %d)\n", client.state());
}

// Valeur JSON valide meme si la mesure est NaN
String num(float v, int decimals) { return isnan(v) ? String("null") : String(v, decimals); }
}

namespace Network {

void begin() {
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  espClient.setInsecure();
  espClient.setTimeout(3);
  client.setServer(MQTT_BROKER, MQTT_PORT);
  client.setSocketTimeout(3);
}

void publish(float temp, float hum, float bpm, int spo2, float activity, const char* motion) {
  ensureConnected();
  if (!client.connected()) return;
  client.loop();

  String payload = String("{\"device_id\":\"") + DEVICE_ID + "\",\"temp\":" + num(temp, 1) +
                   ",\"hum\":" + num(hum, 1) + ",\"bpm\":" + num(bpm, 0) +
                   ",\"spo2\":" + String(spo2) + ",\"activity\":" + num(activity, 2) +
                   ",\"motion\":\"" + motion + "\"}";
  if (!client.publish(MQTT_TOPIC_DATA, payload.c_str())) Serial.println("MQTT : publication echouee");
}

}

#else

namespace Network {
void begin() {}
void publish(float, float, float, int, float, const char*) {}
}

#endif
