# Projet hackathon HackCure : surveillance patient (SurgiGuard)

Langue de travail : **français**. Ce fichier décrit l'ensemble du projet ; chaque sous-dossier peut avoir son propre `CLAUDE.md` plus détaillé (`IOT/CLAUDE.md` existe déjà).

## Vue d'ensemble

```
ESP32 (IOT/) --MQTT EMQX "Hackcure/data"--> API .NET (MqttBridgeService, stockage par patient) ; MoniteurAndroid s'abonne aussi directement au topic (temps réel)
Système Multi-Agent --POST /api/alerts/trigger--> API .NET --> MongoDB (Docker) + notifications WhatsApp/FCM (simulées)
App mobile (AppMobile/SurgiGuardApp) --HTTPS tunnel ngrok--> API .NET --/chat (relais)--> FastAPI + Mistral (AppMobile/backend, port 8000)
```

| Dossier | Contenu |
|---|---|
| `Backend/API` | API REST ASP.NET Core 8 + MongoDB (le cœur du projet) |
| `Backend/Infrastructure_hackathon` | `docker-compose.yml` : `mongo` (7.0) + `api` (port 8080) |
| `AppMobile/SurgiGuardApp` | App React Native 0.87 (CLI, sans Expo), profils patient et famille |
| `MoniteurAndroid` | App Android **native** (Kotlin/Compose), port complet de l'app RN, pour déboguer avec Android Studio : voir `MoniteurAndroid/CLAUDE.md` |
| `AppMobile/backend` | FastAPI qui relaie le chat de l'assistant vers Mistral (port 8000, clé dans `.env`) |
| `AppMobile/Maquette`, `AppMobile/SurgiGuard AI mobile app UI` | Maquettes / prototype web de l'UI |
| `IOT` | Firmware ESP32 PlatformIO (MAX30102, MPU6050, DHT11) : voir `IOT/CLAUDE.md` |

## Backend/API (.NET 8 + MongoDB)

Le prompt d'origine demandait FastAPI/Node, mais le projet existant était en .NET : **on reste en C#**.

- Packages : `MongoDB.Driver` + `MongoDB.Driver.GridFS` 2.29, `BCrypt.Net-Next`, JWT Bearer, `FirebaseAdmin`, Swashbuckle.
- Structure : `Entites/` (le dossier s'écrit bien sans « i »), `Dtos/`, `Services/`, `Controllers/`, `Security/`, `Data/`, `Settings/AppSettings.cs`.
- **Mongo** : conventions camelCase + enums en chaînes (`Data/MongoConventions.cs`). Ids en `string` avec `[BsonRepresentation(ObjectId)]` : valider avec `Ids.IsValid()` avant de filtrer. Index et collection *time-series* `telemetry` (TTL 90 j) créés au démarrage par `MongoDbContext.EnsureSchemaAsync()`. Les PDF du dossier médical sont dans GridFS (`medicalDocuments`).
- Collections : `medications`, `medicationIntakes` (unique médicament+jour+heure), `users`, `patients` (device_id unique sparse, `link_code` à **6 chiffres**), `familyMembers`, `patientFamilyRelations` (relation, `whatsapp_opt_in`, `is_primary_contact` ; le premier proche lié devient contact principal), `telemetry`, `alerts`.
- **JSON en snake_case**, enums en MAJUSCULES (`FAMILY_MEMBER`, `TACHYCARDIA`) : mêmes noms pour l'ESP32, les agents Python et l'app.
- **Authentification** :
  - JWT (claims `sub`, `role`) pour l'app ;
  - en-tête `X-Api-Key` pour les machines : clé `Iot` pour `/api/telemetry/ingest`, clé `Agents` pour `/api/alerts/trigger` (valeurs dev : `dev-iot-key`, `dev-agents-key`) ;
  - inscription DOCTOR/NURSE seulement avec `Auth:StaffRegistrationCode`.
- Endpoints :
  - auth : `/api/auth/register|login|fcm-token` ;
  - patient : `/api/patients/me`, `me/medical-folder` (multipart, PDF), `me/device`, `{id}/thresholds|telemetry/latest|telemetry/history|alerts|documents/{docId}` ;
  - famille : `/api/family/link-patient|patients` ;
  - médicaments (`api/patients/{id}/medications`, `MedicationsController`) : `GET` liste ; `POST`/`PUT {medId}`/`DELETE {medId}` (DOCTOR/NURSE : prescrire, modifier, arrêter) ; `GET schedule?date=&days=&as_of=` (prises avec statut PENDING/TAKEN/SKIPPED/MISSED) ; `PUT {medId}/intakes` (PATIENT : `{date,time,status:TAKEN|SKIPPED}`, status absent = annuler) ; `GET adherence?from=&to=&as_of=` (avancement : totaux, par médicament, par jour). Heures `HH:mm` et dates `yyyy-MM-dd` **locales au patient** (aucun calcul de fuseau côté serveur) ; `as_of` = heure locale du client `yyyy-MM-ddTHH:mm` (sinon UTC) ;
  - machines : `/api/telemetry/ingest`, `/api/alerts/trigger` ;
  - divers : `/chat` (relais vers FastAPI, rôle PATIENT requis), `/health`, Swagger sur `/swagger`.
- **Règle d'alerte** : gravité 1 → push seulement ; 2 → push + WhatsApp au contact principal ; 3 → push + WhatsApp à tous les proches opt-in. `/ingest` ne crée pas d'alerte : il renvoie seulement `anomalies` (seuils). Les agents décident.
- WhatsApp (Meta Cloud API) et Firebase sont **désactivés par défaut** (`Enabled=false` → envois simulés, juste loggés).

Lancer :
- `cd Backend/Infrastructure_hackathon && docker compose up -d --build api` (Docker Desktop doit tourner : il s'arrête parfois tout seul) ;
- ou `dotnet run` dans `Backend/API` (port 5051, Mongo sur localhost).

## Tunnel ngrok (l'app passe par là, pas par 10.0.2.2)

- Binaire : `%LOCALAPPDATA%\ngrok-bin\ngrok.exe` (v3.39, pas dans le PATH). Le token est déjà enregistré dans `%LOCALAPPDATA%\ngrok\ngrok.yml`. **Ne jamais le recopier dans le dépôt.**
- Commande : `ngrok.exe http 8080`. URL publique : `curl localhost:4040/api/tunnels`.
- Compte gratuit : **l'URL change à chaque redémarrage** (dernière : `https://03f9-196-176-231-29.ngrok-free.app`). Il faut alors :
  - mettre à jour `DEFAULT_API_URL` dans `AppMobile/SurgiGuardApp/src/context/AppState.tsx` ;
  - ou la saisir dans l'app (champ « Serveur » de l'écran de connexion, ou Réglages).
- L'app envoie `ngrok-skip-browser-warning: true` sur chaque requête.

## App mobile (AppMobile/SurgiGuardApp)

- Client API : `src/services/backend.ts` (types snake_case, `ApiError`, status 0 = serveur injoignable).
- Session : `src/context/AppState.tsx` contient `session` (token JWT + user), `api`, `signIn`, et `resetRole` qui déconnecte. Persistance AsyncStorage, clé `sg.appState.v2`.
- Hooks de polling : `src/hooks/useBackend.ts` (`useMyProfile`, `useFollowedPatient`, `useLatestTelemetry` toutes les 5 s, `useAlerts`).
- Parcours : choix du rôle → `AuthScreen` (connexion/inscription ; c'est le rôle renvoyé par le serveur qui décide) → patient : onboarding démo puis onglets ; famille : `JoinPatientScreen` (code à 6 chiffres) puis onglets.
- **Branché sur l'API** :
  - patient : Home (`LiveVitalsCard` + nom), Profil et Accès famille (vrai code, vrais proches), Assistant IA (`api.chat`) ;
  - famille : Home famille (statut selon les alertes + constantes), Actus (liste réelle des alertes), Profil famille ;
  - `AlertWatcher` dans `RootNavigator` : une nouvelle alerte de gravité 3 fait vibrer et ouvre `FamilyUrgent`.
- **Encore en données fictives** (`src/data/mock.ts`, « Sarah Miller ») : jumeau 3D, bilan, médicaments, rapports/graphiques, rééducation, scan de plaie, écrans d'alerte info/attention, upload de documents (pas de sélecteur PDF installé).
- i18n : `src/i18n/en.ts` et `fr.ts`. `fr` est typé `Dict = typeof en` : **toute clé ajoutée doit exister dans les deux**.
- Vérifier : `npx tsc --noEmit -p .` et `npx eslint <fichiers>` (les warnings `no-inline-styles` sont le style du projet).
- Le HTTP en clair n'est **pas** autorisé en release ; c'est voulu, l'utilisateur a refusé de l'activer. Passer par ngrok (HTTPS).

## État actuel / à faire

- **APK release pas encore produit** : `gradlew assembleRelease` a planté par manque de RAM (JVM, `hs_err_pid*.log` à la racine).
  - Relancer avec Docker et Android Studio fermés, et une seule architecture :
    `cd AppMobile/SurgiGuardApp/android && JAVA_HOME="C:\Program Files\Android\Android Studio\jbr" ./gradlew assembleRelease -PreactNativeArchitectures=arm64-v8a --no-daemon`
  - Sortie : `app/build/outputs/apk/release/app-release.apk` (signé avec la debug keystore).
  - Installation : `adb install -r app-release.apk` (adb : `%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe`, débogage USB activé), ou copier l'APK sur le téléphone.
- **Pont MQTT → base : fait** (`Backend/API/Services/MqttBridgeService.cs`, section `Mqtt` d'`appsettings.json`). L'API s'abonne à `Hackcure/data` (EMQX, TLS 8883) et appelle `TelemetryService.IngestAsync` directement (pas de POST HTTP). Champs ESP32 → API : `temp`→`room_temp`, `hum`→`room_humidity`, `bpm`, `spo2`, `activity`→`motion_state` (IMMOBILE/LEGER/AGITE, seuils 0,3/1,5). Le message contient `device_id` (`ESP32_001`, `config.h`) qui doit être enregistré sur le patient (`PUT /api/patients/me/device`), sinon le message est rejeté (log warning). L'app lit les mesures par polling toutes les 2 s (`useLatestTelemetry`).
  - Firmware : `ENABLE_MQTT 1`, compilé OK mais pas encore testé sur la carte.
- Push FCM non intégré côté app (pas de lib Firebase) : les familles reçoivent les alertes par polling.
- Pour que le chat marche : lancer `AppMobile/backend` (`uvicorn main:app --host 0.0.0.0 --port 8000`). Sinon `/chat` répond 502.
- Clés de dev (JWT, API keys) dans `appsettings.json` / compose : à changer avant une démo publique.

## Pièges de l'environnement (Windows, Git Bash)

- Les heredocs Bash contenant des apostrophes (`'`) échouent dans l'outil Bash : écrire les fichiers et scripts avec l'outil Write.
- `docker exec … /tmp/x` : Git Bash réécrit les chemins. Préfixer avec `MSYS_NO_PATHCONV=1`.
- Pour tester l'API, utiliser une base jetable (`MongoDbSettings__DatabaseName=DB_smoketest`) ou des emails `@smoke.test`, puis nettoyer. La base réelle s'appelle `DB`.
