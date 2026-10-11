# Projet IOT : moniteur patient ESP32 (PlatformIO)

Langue de travail : **français**. Objectif actuel : afficher dans le **moniteur série** (115200) les mesures d'un patient et de sa chambre. MQTT/WiFi viennent plus tard.

## Matériel
- ESP32 DevKit (`esp32dev`, framework Arduino, PlatformIO). Port série : COM3.
- **MAX30102** (pouls, SpO2, température de puce) : I2C, SDA=GPIO21, SCL=GPIO22.
- **MPU6050** (mouvement du patient) : même bus I2C, adresse 0x68.
- **DHT11** (température/humidité de la chambre) : GPIO **4**. Ne jamais utiliser les GPIO 34-39 (entrée seule) ni 21/22 (I2C).

## Structure (`src/`)
- `config.h` : broches, baud, `ENABLE_MQTT` (0 pour l'instant), `DEBUG_VITALS`, identifiants WiFi/MQTT.
- `main.cpp` : `setup()` + `loop()` non bloquant, `printReport()` chaque seconde.
- `vitals.cpp/.h` : MAX30102 (namespace `Vitals`).
- `motion.cpp/.h` : MPU6050 (namespace `Motion`).
- `ambient.cpp/.h` : DHT11 (namespace `Ambient`).
- `network.cpp/.h` : WiFi + MQTT (EMQX, topic `Hackcure/data`), compilé seulement si `ENABLE_MQTT 1`.

## Décisions techniques (à respecter)
- **Pouls** : `checkForBeat()` (SparkFun `heartRate.h`) + moyenne de 5 battements valides (45-180 BPM). Méthode du tutoriel Random Nerd Tutorials (esp32-max30102-oximeter-heart-rate-sensor).
- **SpO2** : `maxim_heart_rate_and_oxygen_saturation()` sur fenêtre glissante de 100 échantillons à 25 Hz. Le capteur tourne à 100 Hz (400 Hz, moyenne 4) et on décime 1 échantillon sur 4 pour l'algo SpO2. Ne PAS redéfinir `BUFFER_SIZE` (macro de `spo2_algorithm.h`). Ne pas réinventer une formule SpO2 maison (l'ancienne affichait toujours 91 %).
- **Saturation IR** : IR = 262143 signifie ADC saturé, plus de pouls. La puissance LED s'auto-ajuste (IR visé 40k-180k), plage ADC 16384, seuil doigt 20000.
- **Mouvement** : activité = variation de l'accélération entre deux lectures (indépendant de l'orientation). Les lectures nulles ou hors plage sont ignorées, ré-init du MPU après 20 échecs. Seuils 0,3 (léger) et 1,5 m/s² (agité), à ajuster.
- **Température MAX30102** = température de la puce, pas du corps (elle monte avec le chauffage des LED). Pour le patient il faudrait un DS18B20 ou MAX30205 (non ajouté).
- Dans les scripts Python qui écrivent du C++, attention aux `\n` dans les chaînes (ils sont interprétés).

## État / problèmes connus
- Compilation : `pio` n'est pas dans le PATH du terminal ; utiliser `C:\Users\Fares\.platformio\penv\Scripts\platformio.exe` ou les boutons PlatformIO de VS Code. Le code n'a pas été compilé par l'assistant (seulement par l'utilisateur).
- Erreurs I2C (`Error -1`, `263`), capteurs « introuvables » au boot et resets `POWERON_RESET` : mauvais contacts de câblage/alimentation (souder les broches, fils courts, éventuellement pull-ups 4,7 kΩ). Pas un bug logiciel.
- Le MPU6050 mesure ~6,7 m/s² de norme au repos au lieu de 9,81 (valeurs absolues peu fiables, les différences restent utilisables).
- À valider après le dernier flash : le pouls doit apparaître (ligne `[debug]` : IR < 262143, `battements` monte à 5/5).

## Prochaines étapes possibles
Réactiver MQTT (`ENABLE_MQTT 1`, payload JSON temp/hum/bpm/spo2/activity), ajouter un capteur de température corporelle, calibrer les seuils de mouvement.
