"""Remplace le boitier ESP32 quand il est eteint : envoie des mesures a POST /api/telemetry/ingest (cle Iot),
exactement ce que fait le pont MQTT. A utiliser sur une base jetable : l'API ne distingue pas ces mesures de celles du vrai boitier.

    python simulate_esp32.py [--api http://localhost:8080] [--device ESP32_001] [--seconds 60] [--profile normal|desat|tachy|nofinger|fall]
"""
import argparse
import json
import random
import time
import urllib.error
import urllib.request


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8080")
    ap.add_argument("--device", default="ESP32_001")
    ap.add_argument("--key", default="dev-iot-key")
    ap.add_argument("--seconds", type=int, default=60)
    ap.add_argument("--profile", default="normal", choices=["normal", "desat", "tachy", "nofinger", "fall"])
    a = ap.parse_args()
    rnd = random.Random()
    for i in range(a.seconds):
        bpm = round(74 + rnd.uniform(-3, 3))
        spo2 = round(97 + rnd.uniform(-1, 1))
        motion, fall = "IMMOBILE", False
        if a.profile == "desat":
            spo2 = round(87 + rnd.uniform(-1, 1))
        elif a.profile == "tachy":
            bpm = round(128 + rnd.uniform(-3, 3))
        elif a.profile == "nofinger":
            bpm, spo2 = 0, 0
        elif a.profile == "fall" and i == a.seconds // 2:
            motion, fall = "AGITE", True
        body = {"device_id": a.device, "bpm": bpm, "spo2": spo2, "room_temp": round(23 + rnd.uniform(-.3, .3), 1),
                "room_humidity": round(48 + rnd.uniform(-1, 1)), "motion_state": motion, "fall_detected": fall}
        req = urllib.request.Request(a.api + "/api/telemetry/ingest", method="POST", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "X-Api-Key": a.key})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                print(i, r.status, body)
        except urllib.error.HTTPError as e:
            print(i, e.code, e.read()[:200])
        time.sleep(1)


if __name__ == "__main__":
    main()
