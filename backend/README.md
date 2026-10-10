# SurgiGuard AI — backend (FastAPI)

Minimal backend for the mobile app. Right now it does one thing: it proxies the **Recovery Assistant** chat to **Mistral**, so the API key never ships inside the app. More endpoints (IoT, alerts, recovery plans, the medical dashboard) will be added later.

## Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env      # then put your MISTRAL_API_KEY in .env
.\.venv\Scripts\uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Check that it's running with `http://localhost:8000/health`. It should report `"configured": true`.

## Endpoints

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/health` | – | `{ status, llm, model, configured }` |
| POST | `/chat` | `{ messages: [{role, content}], lang: "en" \| "fr" }` | `{ reply, escalate }` |

`escalate` is `true` when the model says a professional should assess the situation. The app then shows a "Contact care team" card.

## Connecting the app

- **Android emulator**: the default URL `http://10.0.2.2:8000` points at your PC.
- **Physical phone**: put the phone on the same Wi-Fi as your PC. In the app, open **Profile → Settings & language → AI server** and set `http://<your-PC-LAN-IP>:8000`. You may also need to allow port 8000 through the Windows firewall.

The recovery plan in `main.py` belongs to the fictional demo patient (Sarah Miller). The assistant follows safety rules: it never diagnoses or changes doses, it sends warning signs to the care team, and it sends emergency symptoms to emergency services.
