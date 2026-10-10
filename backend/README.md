# SurgiGuard AI — backend (FastAPI)

Prototype backend for the mobile app. It proxies the **Recovery Assistant** chat to **Mistral**, so the API key never ships inside the app. It also contains a **synthetic Developer 3 demo** for independent safety decisions, a LangGraph evidence workflow, alerts, and follow-up. The mobile Check-in screen has a separate demo entry that calls these routes and opens a live result screen.

## Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env      # then put your MISTRAL_API_KEY in .env
.\.venv\Scripts\uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Build the browser preview from `mobile` with `npm run build:web`, then open `http://localhost:8000/app/` for the actual patient and caregiver screens. The preview reuses the React Native UI at a phone-sized browser viewport; device-only camera capture, haptics, and the 3D WebView use browser-safe preview behavior. Open `http://localhost:8000/demo` for the separate Developer 3 workflow panel or `http://localhost:8000/docs` for the interactive API. Check `http://localhost:8000/health`; `"configured": true` means the optional Mistral chat key is present. The Developer 3 demo works without that key.

## Endpoints

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/health` | – | `{ status, llm, model, configured }` |
| POST | `/chat` | `{ messages: [{role, content}], lang: "en" \| "fr" }` | `{ reply, escalate }` |

`escalate` is `true` when the model says a professional should assess the situation. The app then shows a "Contact care team" card.

## Developer 3 synthetic demo

Everything under `/v1/demo` uses fictional records and two **synthetic, non-clinical** codes. It has no authentication, clinical approval, real notification delivery, or live D1/D2 integrations. Never enter real patient information. The SQLite file is created at `backend/data/d3-demo.sqlite3` and is ignored by Git; set `SURGIGUARD_DB_PATH` to change that location.

1. In the browser demo, select a synthetic rule and answer, then choose **Run synthetic safety check**. Or in Swagger (`http://localhost:8000/docs`), call `POST /v1/demo/episodes/{episode_id}/events` with `episode_id=ep_demo_001` and this body:

   ```json
   {
     "event_id": "ev_demo_001",
     "patient_id": "pt_demo_001",
     "kind": "structured_warning",
     "code": "demo_urgent_warning",
     "answer": "yes",
     "quality": "unknown",
     "source": "patient",
     "occurred_at": "2026-10-10T08:00:00Z"
   }
   ```

   The response includes a safety decision, synthetic instruction, alert ID, and follow-up ID. It is produced before any investigation or Mistral call. Replaying the exact event ID and content returns the same result; changing its content returns `409`.
2. Call `GET /v1/demo/episodes/ep_demo_001/alerts` and `GET /v1/demo/episodes/ep_demo_001/outbox`. The outbox records **queued delivery intents**, not sent notifications.
3. Call `POST /v1/demo/episodes/ep_demo_001/investigations?event_id=ev_demo_001`. LangGraph collects the event and safety decision, creates an evidence-linked report, and marks it `partial` because D1/D2 are not connected. It uses no LLM yet.
4. Use the returned follow-up ID with `POST /v1/demo/followups/{followup_id}/acknowledgements`, then `/clinical-decisions`, then `/verifications`. Each request requires the current `expected_version` (initially `1`). `GET /v1/demo/followups/{followup_id}` shows the action history. Acknowledgement alone cannot close the follow-up.

Run the backend checks with `python -m unittest -v test_d3_demo` from `backend` after activating `.venv`.

## Connecting the app

- **Android emulator**: the default URL `http://10.0.2.2:8000` points at your PC.
- **Physical phone**: put the phone on the same Wi-Fi as your PC. In the app, open **Profile → Settings & language → AI server** and set `http://<your-PC-LAN-IP>:8000`. You may also need to allow port 8000 through the Windows firewall.

The recovery plan in `main.py` belongs to the fictional demo patient (Sarah Miller). The assistant follows safety rules: it never diagnoses or changes doses, it sends warning signs to the care team, and it sends emergency symptoms to emergency services.
