# SurgiGuard AI: integrated prototype (D1 + D2 + D3)

`main` (merged from **`integration/prototype`**, 2026-10-11) puts the three developers' work on one backend and one app.
Fictional patient only (Sarah Miller, 64, right total knee replacement). Not a medical device.

## What was merged

| Branch | Owner | What it brings | How it is wired |
|---|---|---|---|
| `codex/photo-schedule-followup-verification` (base) | D3 | Safety rules, investigation agent, alerts + follow-up verification, dressing-window wound photos, RN app as a web build | Base of this branch |
| `agentic-backend` (+2 local commits) | D3 | Protocol agent (documents → plan), real wound photos measured by code | Photo answers: dressing window checked first, then the photo is measured |
| `dev/d2-unified` | D2 (Ines) | OCR, 20+ field extraction, safety graph, RAG assistant, `/v1/*` API | Routers mounted at `/v1`; one shared config and LLM keys |
| `dev/d2b-assistant` | D2 (Wassila) | Hybrid keyword ranking (missing from d2-unified) | Merged into the retriever together with the patient filter |
| `dev/d1-recovery` | D1 (Elaa) | Expected recovery (trajectory_prediction), Patient Twin, physiology | `backend/app/integrations/d1_bridge.py` |
| `feat/esp32-mqtt-medications-android` | Karoui | ESP32 MQTT firmware, native Android monitor, Node/Mongo API, medication alarms, another app copy | In `SurgiGuard/` only: **not connected** to `backend/` yet (next step: MQTT readings → `POST /observations`) |

## Run it

```powershell
cd backend
.\.venv\Scripts\python -m pip install -r requirements.txt   # once (LangChain, faiss, pymupdf, groq…)
cd ..\mobile; npm install; npm run build:web; cd ..\backend  # builds the patient/family app for /app
.\.venv\Scripts\uvicorn main:app --port 8000
```

Keys go in `backend/.env` (see `.env.example`). With `GROQ_API_KEY` set, D2 uses Groq `gpt-oss-20b` and D1 uses `gpt-oss-120b`.
Without keys everything runs in stub mode (canned AI, all rules real).

| URL | What |
|---|---|
| `/prototype` | **Story console**: the scenario below, step by step, with live calls |
| `/app/` | Patient & family app (React Native, web build) |
| `/agent-demo/` | Patient · family · clinic dashboard (alerts, follow-up, verification) |
| `/demo` | D3 event/follow-up workflow (`/v1/demo`) |
| `/docs` | API |

## The scenario (open `/prototype`)

1. **Documents → care plan** (D2 compiler + code grounding). Sample discharge summary → D2 extracts medicines,
   risk factors, missing fields; its safety graph flags celecoxib + enoxaparin; code checks every medicine/dose/date
   is in the text; Sarah confirms. Same flow in the app: onboarding *Upload → Analyze → Review → Confirm*.
2. **What is normal today** (D1). From the plan ("D2 JSON"), D1 writes a 42-day expected recovery (≈3.5 min the
   first time on Groq, then cached); the app's Home shows today's card. Patient Twin forecasts HR/SpO₂ or abstains.
3. **Something changes** (D3). Check-in + vitals → urgent rules (no AI) → investigation agent asks Sarah a question,
   a wound photo only inside a permitted dressing change → evidence report.
4. **Care team closes the loop** (D3). Alert → acknowledge → contact → action → verification evidence → resolve
   (clinic view in `/agent-demo/`). Ahmed's digest only shows what Sarah allowed.
5. **Questions** (D2 RAG + D3 urgent gate). `/v1/chat` retrieves only Sarah's plan passages; an emergency phrase is
   caught by the urgent rules before any AI. `/v1/checkin` (D2 rules) is also recorded by the D3 pipeline.

## How the parts talk

```
documents ─► D2 OCR + extraction + safety graph ─► d2_bridge ─► plan draft (code grounding) ─► patient confirms
                                                                                              │
             ┌────────────────────────────── active care plan ◄──────────────────────────────┘
             ├─► D3 agents, reminders, urgent rules, dressing-photo windows, plan chat (/chat)
             ├─► D2 RAG index (per patient, replaced on each new plan) ─► /v1/chat
             └─► "D2 JSON" (/patients/{id}/d2-document) ─► D1 expected recovery ─► app Home card
vitals ─► D3 monitor ─► D1 Patient Twin forecast (/patients/{id}/twin-forecast)
/v1/checkin (D2 rules) ─► D3 check-in pipeline (urgent gate, clarification, investigation)
```

New endpoints: `POST /patients/{id}/plan-drafts {"engine": "d2"}`, `GET /patients/{id}/expected-recovery`,
`/twin-forecast`, `/d2-document`, `/clinical-profile`, `GET /integration/status`.

## Fixes made while integrating

- `app/models/` (D2) would have shadowed `app/models.py` (D3) → moved to `app/d2_models/`.
- D2 graphs were hard-wired to Mistral (no Mistral key) → shared provider (`get_chat_llm`, `LLM_ROUTE_D2`).
- D2 safety graph: English drug/allergy names were unknown (documents are English); interaction pairs were checked
  in one order only (enoxaparin listed after celecoxib was missed); `diabetes: "unknown"` counted as a risk factor.
- D2 RAG: the store was loaded once at startup (new passages never seen), had no patient filter (cross-patient
  leak), and always answered in French.
- D1: files read without UTF-8 (French text and the cache broke on Windows; 3 tests failed).
- Protocol agent dropped the dressing-photo schedule when a new plan was confirmed.
- Camera uploads bypassed the dressing-change schedule; now the same rule applies everywhere.

Tests: backend **132 passed** (offline), D1 **128 passed, 1 skipped**. Live run on Groq/OpenRouter: every step above OK.

## Still missing (by owner)

**Team decisions**
- Day numbering: D1 counts post-operative days, the app counts days since discharge. Pick one.
- D2 spec requires clinician approval of plans; the team chose patient confirmation only. Write the decision down.
- No authentication: actor ids are sent by the caller. One demo patient.

**D1**
- Motor assessment (D1-D) and rehab pose estimation (D1-E) not started; wound-photo analysis is D3's code today.
- Patient Twin is not shown in the app's Twin screen yet (endpoint ready).
- Expected recovery is LLM-written and not reviewed by a clinician (shown as such).

**D2**
- `/v1/checkin` returns a `recovery_score` (0-100): the specs exclude a universal recovery score.
- Safety graph asks an LLM "pharmacist" for extra interactions when no rule fires: unsupported claims (spec D2-C.5).
- Assistant: no citations returned; flags simple questions as `escalate` with a French disclaimer.
- Embeddings are fake without a Mistral key (keyword ranking only); image OCR needs Mistral (Pixtral).
- Extraction has no clock times (frequency only) → times are proposed and flagged. Scheduling engine (D2-B) and
  `protocol.activated` events not built; D2 SQLAlchemy tables are unused.
- D2 test scripts (`test_*.py` in backend/) call live LLMs and are not part of pytest.

**D3**
- Two investigation implementations (`/v1/demo` LangGraph and the agent loop): choose one.
- Investigation jobs now recover from persisted checkpoints on startup and periodic sweeps, with atomic local
  tool effects and completion. One server process is supported; protocol/digest job recovery and coordinated
  workers remain outstanding. See `backend/RESTART_RECOVERY.md`. The event envelope v1 is used only by `/v1/demo`.

**App**
- Twin, Reports, Medications, Rehab screens and parts of Home (pain, score ring, sensor card) are still mock data.
- No native document picker (sample document only on the phone; file picker works in the browser).
- `npm test` (jest) fails on ESM config; `tsc` reports DOM-type errors in `src/web/shims`.
