# SurgiGuard AI

**Smarter Recovery. Safer Care.** A HackCure hackathon prototype for post-operative recovery at home: an ESP32 wearable, a .NET + MongoDB API, AI agents, mobile apps and one page that tells the whole story.

> Fictional patient only (Sarah Miller, 64, right total knee replacement). Not a medical device. Medical decisions stay with clinicians. WhatsApp and push notifications are **simulated** unless you enable them.

## How the pieces fit

```
ESP32 (MAX30102, MPU6050, DHT11) --MQTT--> SurgiGuard API (.NET 8 + MongoDB)         <- source of truth
                                                 |  ^
              pull telemetry / meds (X-Api-Key)  |  |  POST /api/alerts/trigger  (family: push / WhatsApp)
                                                 v  |
                                   AI backend (FastAPI, Python)
                          Monitor + urgent rules . D1 recovery/twin/rehab/movement tests
                          D2 documents -> care plan + RAG assistant . D3 investigation + follow-up
                                                 |
                       /story  (the whole story)  /prototype  /agent-demo  /app (patient/family web app)
```

| Folder | What it is |
|---|---|
| `SurgiGuard/IOT` | ESP32 firmware (PlatformIO). See `SurgiGuard/IOT/CLAUDE.md`. |
| `SurgiGuard/Backend/API` | REST API ASP.NET Core 8 + MongoDB (auth, patients, telemetry, medications, alerts, family). |
| `SurgiGuard/Backend/Infrastructure_hackathon` | `docker-compose.yml`: MongoDB 7 + the API on port 8080. |
| `SurgiGuard/Backend/scripts` | `seed_story.py` (demo accounts), `simulate_esp32.py` (stands in for the board). |
| `SurgiGuard/MoniteurAndroid` | Native Android app (Kotlin / Compose), medication alarms. |
| `SurgiGuard/AppMobile/SurgiGuardApp` | React Native app wired to the .NET API. |
| `backend/` | **AI backend** (FastAPI): agents D1/D2/D3, `/story`, `/hub`. |
| `d1/` | Developer 1 Python package: trajectory prediction, Patient Twin, rehabilitation, guided movement tests. |
| `mobile/` | React Native patient/family app (web build served at `/app`). |
| `contexte/` | Specifications of the three developer roles. |

## What you need

| Need | For | Notes |
|---|---|---|
| **Python 3.11 or 3.12** | AI backend, `d1/`, helper scripts | The backend needs `fastapi`, `langgraph`, `faiss-cpu`... (all in `backend/requirements.txt`). |
| **.NET SDK 8** | SurgiGuard API (if not using Docker for it) | `dotnet --version` -> 8.x |
| **Docker Desktop** | MongoDB (and optionally the API) | Keep it running. |
| Node.js 20+ | only to rebuild the `/app` web app (`mobile/`) | optional |
| PlatformIO + an ESP32 DevKit | real sensor data | optional: `simulate_esp32.py` replaces the board |
| Android Studio | only for `MoniteurAndroid` | optional |
| A Groq **or** Mistral **or** OpenRouter key | live AI answers (chat, plan extraction, investigation, expected recovery) | optional: without a key everything runs in **stub** mode (canned AI, all safety rules are real) |
| Internet access | MQTT broker (EMQX cloud), LLM provider, MediaPipe CDN for the live camera | the rest works offline |

Free ports: **27017** (Mongo), **8080** or **5051** (API), **8000** (AI backend).

## Run it (5 steps)

### 1. MongoDB and the SurgiGuard API

Option A, everything in Docker:

```bash
cd SurgiGuard/Backend/Infrastructure_hackathon
docker compose up -d --build            # mongo + api on http://localhost:8080  (Swagger: /swagger)
```

Option B, API from source (port 5051), Mongo in Docker:

```bash
cd SurgiGuard/Backend/Infrastructure_hackathon && docker compose up -d mongo
cd ../API && dotnet run                 # http://localhost:5051
```

Use a throw-away database for tests so you never touch real data:
`MongoDbSettings__DatabaseName=DB_story dotnet run --no-launch-profile` (and `ASPNETCORE_URLS=http://localhost:5051`).
The API subscribes to the MQTT topic `Hackcure/data` (EMQX, TLS 8883, credentials in `appsettings.json`); set `Mqtt__Enabled=false` to turn it off.

### 2. Create the demo accounts (patient with the ESP32, family member, doctor)

```bash
python SurgiGuard/Backend/scripts/seed_story.py --api http://localhost:8080     # or 5051
```

Logins (password `Story2026!`): `sarah@story.test` (patient, device `ESP32_001`), `ahmed@story.test` (family, WhatsApp opt-in), `dr.ruiz@story.test` (doctor). The script is idempotent.

### 3. The AI backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate                  # Windows   (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env                  # optional: add GROQ_API_KEY / MISTRAL_API_KEY and set LLM_MODE=live
set SURGIGUARD_API_URL=http://localhost:8080      # 5051 if you used option B   (PowerShell: $env:SURGIGUARD_API_URL="...")
uvicorn main:app --port 8000
```

On first start it seeds the fictional patient in a local SQLite file (`surgiguard.db`). Reset it any time with `POST /demo/reset`.

### 4. Open the story

**http://localhost:8000/story** : header chips show the link to the API, the ESP32 (online or silent), the LLM mode and open alerts.

### 5. Feed it data

- **Real board:** flash `SurgiGuard/IOT` (below), power it, put a finger on the MAX30102. Readings flow ESP32 -> MQTT -> API -> AI.
- **No board:** replay what the board sends:

```bash
python SurgiGuard/Backend/scripts/simulate_esp32.py --api http://localhost:8080 --seconds 60 --profile normal
# profiles: normal | desat | tachy | nofinger | fall
```

This writes to the same endpoint as the board (`/api/telemetry/ingest`): use it on a throw-away database only.

## This Windows workspace

Once the local runtimes are installed in `backend/.cache/tools`, start the demo from the repository root:

```powershell
./scripts/start-local.ps1
```

This starts MongoDB bound to localhost, the .NET API on 8080 using `DB_story`, and the AI backend on 8000. It creates the fictional story accounts and opens `/story`. The patient app is at `/app/`. MQTT, WhatsApp and Firebase are disabled; AI starts in stub mode. Existing healthy services are reused. Logs and demo database files are under the ignored `backend/.cache` directory.

On this machine, compatible Python wheel constraints are recorded in `backend/requirements-windows-local.txt`. Windows application control may reject unsigned portable MongoDB binaries; use MongoDB's official signed installer in that case.

## ESP32 firmware

```bash
cd SurgiGuard/IOT
copy src\config.example.h src\config.h        # then edit it (config.h is git-ignored)
```

Set `WIFI_SSID` (2.4 GHz network) and `WIFI_PASSWORD`; keep `DEVICE_ID "ESP32_001"` (the API patient must own this id: `PUT /api/patients/me/device`, or use `seed_story.py`). Wiring: I2C SDA 21 / SCL 22 for MAX30102 + MPU6050, DHT11 on pin 4. Build and upload with PlatformIO (`pio run -t upload`, `pio device monitor`). Details in `SurgiGuard/IOT/CLAUDE.md`.

## What to try on `/story`

1. **Live vitals** (step 3): BPM, SpO2, motion and room climate from the board. 0 = sensor not worn = "unknown", never "normal". The room temperature is never used as body temperature.
2. **Something changes** (step 5): simulated fever / desaturation / tachycardia / fall (orange "simulated" label), or a check-in such as "I feel short of breath".
3. **Alert loop** (step 6): acknowledge -> patient contacted -> decision -> verify (needs fresh **real** board readings) -> resolve.
4. **Family notified** (step 7): what the API recorded and sent (simulated WhatsApp/push).
5. **Rehabilitation and movement tests** (steps 10 and 11): demo sessions through the real D1 engine, heart rate from the ESP32; opt-in tests; "My camera" buttons use MediaPipe in the browser (only joint positions are sent).
6. **Assistants** (step 9): recovery assistant, plan Q&A with sources, family assistant.

Other pages: `/prototype` (D1+D2+D3 console), `/agent-demo/` (clinic dashboard), `/demo` (D3 workflow), `/docs` (AI API), `:8080/swagger` (SurgiGuard API), `/app/` (patient/family web app, after `cd mobile && npm install && npm run build:web`).

## Configuration (AI backend, environment variables or `backend/.env`)

| Variable | Default | Meaning |
|---|---|---|
| `SURGIGUARD_LINK` | `on` | `off` = standalone AI backend on its seed data. |
| `SURGIGUARD_API_URL` | `http://localhost:8080` | The .NET API. |
| `SURGIGUARD_AGENTS_KEY` / `SURGIGUARD_IOT_KEY` | `dev-agents-key` / `dev-iot-key` | Must match `ServiceApiKeys` in the API. **Change before any public demo.** |
| `SURGIGUARD_PATIENT_ID` | `auto` | API patient playing "sarah": a Mongo id, or `auto` = the owner of `ESP32_DEVICE_ID`. |
| `ESP32_DEVICE_ID` | `ESP32_001` | Board id. |
| `ESP32_WINDOW_S` / `ESP32_POLL_S` | `15` / `3` | One AI observation per metric per window; poll period. |
| `LLM_MODE` | `live` if a key is set, else `stub` | `stub` = canned AI; `off` = simulate the LLM being down. |
| `GROQ_API_KEY`, `MISTRAL_API_KEY`, `OPENROUTER_API_KEY` | empty | Never commit them (`.env` is git-ignored). |

In the .NET API: WhatsApp (`WhatsApp__Enabled`) and Firebase (`Firebase__Enabled`) are off by default (messages are only logged). `ChatService__BaseUrl` points the API's `/chat` relay to the AI backend (port 8000).

## Tests

```bash
cd backend && python -m pytest tests -q          # 138 tests, offline, no key needed
cd d1 && python -m pytest -q                      # 170 tests (add: pip install -e ".[dev]")
cd SurgiGuard/Backend/API && dotnet build         # API compiles
```

## Troubleshooting

- **"API injoignable" chip / `/hub/status` says not reachable:** wrong `SURGIGUARD_API_URL` (8080 for Docker, 5051 for `dotnet run`), or Docker Desktop stopped.
- **"Aucune patiente liée":** no API patient owns the board id. Run `seed_story.py`, or set the device in the app (`PUT /api/patients/me/device`).
- **ESP32 stays "silencieux":** check Wi-Fi is 2.4 GHz, `ENABLE_MQTT 1`, the same broker credentials as `appsettings.json`, and that only one API instance should consume the topic you care about (each API has its own database).
- **Verification refused in the alert loop:** it needs good-quality **real** board readings received after the clinician's decision; keep the finger on the sensor.
- **Movement tests refused (409):** an urgent alert is open, resolve it first (by design). **403:** tick the consent box.
- **`pip install` fails on Windows with "file in use":** do not run two installs in the same virtualenv.
- **Docker: `docker exec ... /tmp/x` path errors in Git Bash:** prefix with `MSYS_NO_PATHCONV=1`.

## Safety boundary

SurgiGuard must not independently diagnose, change treatment or delay urgent escalation. Urgent rules run without any AI and fire first. Movement-test and rehabilitation findings are prompts for clinician review, never diagnoses; pain is only what the patient reports. All records are fictional and simulated values are labelled. See [PROJECT.md](PROJECT.md) for the product brief and [INTEGRATION.md](INTEGRATION.md) for how the parts were merged and what is still missing.
