# MoniteurAndroid : app Android native (Kotlin + Jetpack Compose)

Langue de travail : **français**. Port natif de `AppMobile/SurgiGuardApp` (React Native) pour pouvoir **déboguer avec Android Studio**. Même parcours, mêmes écrans, mêmes textes (FR/EN), branchée sur l'API .NET **et** sur le broker MQTT.

## Lancer / déboguer
- Ouvrir le dossier `MoniteurAndroid` dans Android Studio, bouton Run/Debug (module `app`). AGP 9.2, Gradle 9.4, `compileSdk 37`, `minSdk 24`.
- Ligne de commande : `JAVA_HOME="C:/Program Files/Android/Android Studio/jbr" ./gradlew.bat :app:assembleDebug` → `app/build/outputs/apk/debug/app-debug.apk`.
- **URL de l'API** (champ « Serveur » de l'écran de connexion et des Réglages, défaut : l'URL ngrok du moment, à changer si ngrok a redémarré) :
  - vrai téléphone sans câble : l'URL ngrok (`https://….ngrok-free.app`) ;
  - émulateur : `http://10.0.2.2:8080` ;
  - téléphone en USB : `adb reverse tcp:8080 tcp:8080` puis `http://localhost:8080` ;
  - téléphone en Wi-Fi : `http://<IP du PC>:8080` ;
  - le HTTP en clair n'est autorisé qu'en **debug** (`app/src/debug/AndroidManifest.xml`) ; en release il faut HTTPS (ngrok).
- Logs MQTT : filtre Logcat `MqttLive` (connexion, et une ligne `message <device> bpm=…` par message reçu).
- Docker Desktop doit tourner pour l'API (`cd Backend/Infrastructure_hackathon && docker compose up -d --build`).

## Données temps réel (ESP32)
- `data/MqttLive.kt` : l'app s'abonne **directement** à `Hackcure/data` (HiveMQ MQTT client, TLS 8883, mêmes identifiants que `IOT/src/config.h`, ~1 mesure/s). `AppViewModel` le démarre à la connexion et l'arrête à la déconnexion.
- `Hooks.kt` → `useLiveTelemetry(patientId, deviceId)` : prend la mesure MQTT si le `device_id` du message est celui du patient et qu'elle a moins de 15 s, sinon la dernière mesure de l'API (poll 2 s). `LiveVitalsCard` affiche la source (« Temps réel · MQTT » ou « via le serveur »).
- Le stockage par patient est fait par l'**API** (`MqttBridgeService`), pas par l'app. Historique des Rapports = `/telemetry/history` (moyennes réelles).
- Le boîtier doit être lié au patient : à l'inscription (champ « ID du boîtier ») ou Réglages → « Boîtier ESP32 » (`PUT /api/patients/me/device`). Valeur du firmware : `DEVICE_ID "ESP32_001"`.

## Médicaments et alarmes
- Le **médecin** prescrit via l'API (Swagger `/swagger`, rôle DOCTOR/NURSE : inscription avec `staff_code` = `Auth:StaffRegistrationCode`) ; l'app n'a pas d'écran médecin (comptes staff refusés à la connexion).
- `screens/PatientMore.kt` → `MedicationsScreen` : planning du jour (API), boutons Prendre/Ignorer (annulable en touchant la pastille), anneau d'adhérence sur 7 jours.
- `alarm/MedAlarms.kt` : planning des 3 prochains jours mis en cache (`sg.medAlarms.v1`) et programmé en **alarmes exactes** (`AlarmManager`). À l'heure : notification d'alarme (canal `med_alarm_v1`, son d'alarme répété `FLAG_INSISTENT`, vibration) avec actions **Pris / Ignorer** qui répondent à l'API sans ouvrir l'app ; appui = ouvre l'écran des médicaments. Resynchronisation à chaque alarme, toutes les 30 min, au redémarrage du téléphone, toutes les 5 min app ouverte (`MedAlarmSync` dans `AppRoot`).
- Permissions : `POST_NOTIFICATIONS` (demandée dans l'écran Médicaments sur Android 13+), `USE_EXACT_ALARM`/`SCHEDULE_EXACT_ALARM`, `RECEIVE_BOOT_COMPLETED`. Les fabricants (Huawei, Xiaomi…) peuvent tuer l'app en arrière-plan : désactiver l'optimisation de batterie pour SurgiGuard si une alarme ne sonne pas.
- Test rapide : prescrire un médicament à l'heure de l'émulateur + 2 min (`adb shell date`), lancer l'app connectée, `adb shell dumpsys alarm | grep moniteur`, puis `dumpsys notification`.

## Structure (`app/src/main/java/com/example/moniteur`)
- `AppViewModel.kt` : session JWT, rôle, langue, thème, URL, pile de navigation (`Route`), MQTT ; persistance SharedPreferences `sg.appState.v1`. `AppRoot.kt` : racine selon l'état (rôle → connexion → onboarding → onglets), onglets, `AlertWatcher` (famille : nouvelle alerte = vibration, gravité 3 = écran d'urgence).
- `data/` : `Api.kt` (HttpURLConnection + org.json, JSON snake_case, `ApiError.status 0` = injoignable ; 401 → déconnexion), `Models.kt`, `MqttLive.kt`, `Mock.kt` (données fictives).
- `ui/` : design system (`Theme`/`Color`, `Components`, `Charts`, `Icons` ; icônes = chemins SVG dessinés en Canvas). `screens/` : `Onboarding`, `PatientMain`, `PatientMore`, `Family`, `Settings`, `LiveVitals`, `Twin3D`, `Common`.
- `I18n.kt` + `res/raw/i18n_{en,fr}.json` : **générés** depuis `AppMobile/SurgiGuardApp/src/i18n/*.ts` (clés à plat, `{{n}}`, listes `a|b|c`). Toute clé ajoutée doit exister dans les deux fichiers.
- `assets/twin.html` : jumeau 3D (three.js + GLB), copie générée de `twinHtml.ts`, dans un WebView. Sur l'**émulateur** le WebGL est refusé : l'app affiche alors la silhouette 2D de secours (normal, OK sur un vrai téléphone).

## Reste en données fictives / non porté
- Jumeau, bilan, médicaments, rééducation, scan de plaie, écrans info/attention : `Mock.kt` et textes, comme l'app RN.
- **Scan de plaie réel** (`screens/WoundScan.kt`) : caméra intégrée CameraX (permission `CAMERA` demandée à l'ouverture), photo vérifiée puis envoyée après confirmation « je change mon pansement » → `POST /api/patients/me/wound-photos` (relais .NET → backend IA : contour OpenCV, qualité, comparaison, lecture par LLM vision). La pose de rééducation utilise encore le visuel de secours ; la jonction famille se fait par le **code à 6 chiffres** (pas de scan QR). Sélecteur de PDF absent.
- Pas de push FCM (alertes famille par polling, 8 s).

## Pièges
- Après avoir **ajouté une permission** au manifeste, désinstaller l'app avant de la réinstaller sur l'émulateur (sinon `Operation not permitted` sur les sockets).
- Les heredocs Bash avec apostrophes échouent : écrire les fichiers avec l'outil Write.
- `adb push` depuis Git Bash : préfixer avec `MSYS_NO_PATHCONV=1`.
- Tests rapides sans passer par l'UI : écrire `shared_prefs/sg.appState.v1.xml` via `run-as` avec un vrai token (un faux token est rejeté en 401 → retour au choix du rôle).
