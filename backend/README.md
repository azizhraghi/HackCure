# SurgiGuard AI: backend (FastAPI)

This is the agentic backend for the SurgiGuard prototype: safety rules, the Monitor, the alert lifecycle, five agents, and the REST API used by the mobile app and the clinician dashboard. The LLM is **Mistral**. All patient data is **fictional** and all device data is **simulated**. This is not a medical device, and the thresholds are demo values, not clinical advice.

## Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env      # put MISTRAL_API_KEY in .env (optional: stub mode needs no key)
.\.venv\Scripts\uvicorn main:app --host 0.0.0.0 --port 8000
```

- `http://localhost:8000/health` reports `llm_mode` and whether a key is configured.
- `http://localhost:8000/docs` has the interactive API (OpenAPI). The dashboard teammate can start there.
- On first start the SQLite file `surgiguard.db` is created and seeded with Sarah's data. `POST /demo/reset` re-seeds it at any time.
- Run the tests with `.\.venv\Scripts\python -m pytest -q`. They always run in stub mode, offline.

### Environment

| Variable | Default | Meaning |
|---|---|---|
| `MISTRAL_API_KEY` | – | Needed for `LLM_MODE=live` and for `/chat` |
| `LLM_PROVIDER` | `mistral` | `mistral`, `openrouter` (set `OPENROUTER_API_KEY`, optional `OPENROUTER_MODEL`, default `poolside/laguna-s-2.1:free`) or `groq` (OpenAI-compatible; set `GROQ_API_KEY`, optional `GROQ_MODEL`, default `openai/gpt-oss-120b`). `/chat` uses the same layer (route `CHAT`) |
| `MISTRAL_MODEL` | `mistral-medium-latest` | Model used by every agent |
| `LLM_MODE` | `live` if a key is set, else `stub` | `live` = Mistral, `stub` = canned deterministic agent output, `off` = the LLM is "down" (agents fall back to rules and templates) |
| `LLM_MIN_INTERVAL_S` / `LLM_RATE_WAIT_MAX_S` | `1.1` / `60` | Minimum gap between LLM calls; how long one call may wait out provider rate limits (Groq's free tier allows 8,000 tokens/min, about 2 investigation steps per minute) |
| `LLM_ROUTE_<AGENT>` | – | Per-feature `provider:model` for `INVESTIGATION`, `CHECKIN_CLARIFY`, `DIGEST`, `CHAT` (spreads free-tier quotas). Tested setup: investigation on `openrouter:poolside/laguna-s-2.1:free`, the other two on `groq:openai/gpt-oss-20b`. `GET /health` shows the active routes |
| `ACK_TIMEOUT_S` | `60` | An alert not acknowledged within this time escalates to the backup contact |
| `INVESTIGATION_TIMEOUT_S` | `120` | Past this, the investigation finishes with "evidence incomplete" and goes to the clinician anyway |
| `REQUEST_TIMEOUT_S` | `90` | An unanswered patient request expires and the agent continues with "unknown" |
| `DB_URL` | `sqlite:///./surgiguard.db` | Any SQLAlchemy URL. `db.py` is the only module that talks to the DB, so swapping to Postgres or Supabase is local to it |
| `SCHEDULER_ENABLED` | `1` | APScheduler: 5 s sweep (timeouts and escalations), minute medication reminders, 08:00/20:00 check-in reminders, 20:05 digest |

The LLM mode can also be switched at runtime: `POST /demo/llm_mode/{live|stub|off}`.

## Demo script (about 2 minutes)

Use `/docs`, curl or the app. Without a phone, `POST /demo/answer_pending` answers Sarah's requests: the day-3 wound photo, then the second option of each question.

1. `POST /demo/reset`: Sarah Miller, total knee replacement (right), **day 3** after discharge. The seed holds 2 days of normal history, a slow HR/temperature drift over the last 24 h, and one missed cefuroxime (antibiotic) dose yesterday evening.
2. `POST /demo/scenario/infection_pattern`. This submits Sarah's check-in: fatigue 7/10, which is 4/5 against yesterday's 2/5. The **Check-in Agent** asks one clarification. Then it streams HR 88 → 91 and a temperature of 37.9 °C, and the **Monitor** opens an investigation. This is not urgent.
3. `GET /patients/sarah/requests` lists the clarification and the **Investigation Agent**'s wound-photo request. Answer them with `POST /requests/{id}/answer`, or call `/demo/answer_pending`. The agent compares the photos (redness +22 %), asks one follow-up question (its second and last patient request), then finishes.
4. `GET /investigations/{id}` returns the evidence summary: patient-reported, device-measured, AI interpretation and missing evidence, every claim linked to an observation. `steps` holds the full reasoning and audit trail. The clinician gets an **attention** alert, Ahmed gets a support task, and Sarah gets a next step (in `GET /patients/sarah/today`, under `next_step`).
5. Alert lifecycle:
   - `POST /alerts/{id}/ack` with `{"actor":"dr_ruiz"}`, then `/contacted`, then `/action`, then `/resolve` with `{"actor":"dr_ruiz","reason":"..."}`.
   - If you don't acknowledge it, the alert is escalated to `dr_oncall` after 60 s. `POST /demo/clock/advance?seconds=61` gets there instantly.
6. Urgent contrast: `POST /demo/llm_mode/off`, then `POST /demo/scenario/urgent_breathless` (severe breathlessness plus SpO₂ 88 %). The urgent alert fires in under 1 s **with no LLM call**, and any running investigation is aborted.
7. `GET /caregiver/ahmed/digest?refresh=true` returns Ahmed's evening summary: at most 80 words, only the categories Sarah shares.
8. `POST /medications/dose` with `{"med_id":"m5","scheduled_for":"<today>T14:00:00","status":"not_taken"}`. This is the second missed dose in 48 h, so Ahmed gets a task and the clinician gets an attention flag. The missed-dose text comes from the plan only.

Other scenarios:
- `normal`
- `bad_signal`: unusable SpO₂ readings are flagged as "unreliable" and raise no alert.
- `no_data`: removes the last 6 h of device data, so the twin shows "unknown".

The ESP32 simulator streams to the API like the real device would:

```powershell
.\.venv\Scripts\python -m seed.simulator --url http://localhost:8000 --scenario normal --every 5
```

## Architecture

```
app/safety/urgent_rules.py   S1 urgent rules: pure functions, no I/O, no LLM (SpO2 < 90 good signal, temp >= 38.5 / 39.5, red-flag phrases/chips)
app/safety/quality.py        reading quality (good / questionable / unusable), "unknown" for missing/stale data, gap detection
app/safety/output_guard.py   blocks doses, medication changes and diagnosis wording in LLM text
app/monitor.py               quality -> urgent rules -> deviation signals -> investigation_request (synchronous, LLM-free)
app/alerts.py                S2 routing + S3 lifecycle: created -> assigned -> acknowledged -> patient_contacted -> action_taken -> resolved
app/agents/checkin.py        B1 Daily Check-in (LLM writes the one clarification; template fallback)
app/agents/investigation.py  A2 Investigation: resumable Mistral tool loop, paused while waiting for the patient
app/agents/evidence.py       A3 evidence validation (observation ids, source separation, no diagnosis) + rule-built fallback
app/agents/digest.py         B7 Caregiver Digest (permission-filtered input, checked output, template fallback)
app/agents/medication.py     B2 Medication (rules only)
app/tools/                   the 9 investigation tools (JSON schemas sent to Mistral)
app/llm.py                   the only module that calls Mistral: timeout, 1 retry, stub/off modes
app/audit.py                 append-only log of every agent step, tool call, rule decision and human action
app/runner.py                agents run in a worker thread so API calls never wait for the LLM
seed/                        demo plan (plan_sarah.json), history, photos, scenario simulator
```

### Safety guarantees (each one has a test)
- **Urgent alerts never depend on the LLM.** They are evaluated synchronously in the request that delivered the data, before any agent. Tests cover the LLM raising and `LLM_MODE=off`.
- **Every answer is checked first.** Each patient or caregiver answer (check-in, request answer, chat message) goes through `urgent_rules` before an agent sees it. A red flag stops the agent and fires the urgent path. Matching is conservative: "no chest pain" still fires.
- **Hard limits in code, not in the prompt:**
  - at most 8 tool calls (the finish call is always allowed);
  - at most 2 patient requests per investigation;
  - only tests listed in the plan;
  - a deadline, after which the investigation ends as "evidence incomplete" and is escalated anyway.
- **Agents cannot** change medication, suggest doses, close or downgrade alerts, or acknowledge. Only a clinician acknowledges or resolves, and resolving requires a reason. A delivered or read notification is never an acknowledgement.
- **Evidence summaries** cite real observation IDs, in the right section (patient vs device). The stored quality wins over the model's. The summary always says it is not a diagnosis. Bad citations are rejected and retried once, then replaced by a rule-built summary.
- **Missing data is "unknown", never "normal".** Unusable readings are "unreliable". Both are listed in `missing_or_conflicting`.
- **Patient text is data.** It reaches the LLM only inside tool results or JSON data blocks, and the prompts say so.

## API

The actor is passed in the body (`{"actor": "dr_ruiz"}`) or as `?actor=`. Members are `sarah` (patient), `ahmed` (caregiver), `dr_ruiz` (clinician) and `dr_oncall` (backup clinician). There is no authentication: this is a prototype.

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | |
| POST | `/chat` | Unchanged contract `{messages, lang}` → `{reply, escalate}`. A red-flag message now returns the emergency text and fires an urgent alert **without calling Mistral** |
| GET | `/patients/{id}/today` | Day number, today's tasks (check-ins, doses with status, rehab), appointments, pending requests, latest next step |
| GET | `/patients/{id}/twin?role=&member_id=&hours=24` | Vitals (status ok/questionable/unknown/unreliable, baseline, expected range, gaps, series), check-ins, adherence, wound, alerts. Caregivers only get shared categories |
| POST | `/observations` | `{type, value, unit?, measured_at?, source, simulated?}`: ESP32 or simulator readings. The response includes the Monitor decision |
| GET | `/patients/{id}/observations?type=` | |
| POST | `/checkin` | The app's form: `{pain, fatigue, mobility (0-10), chips: [..], comment?, submitted_by?}` → `{status: ok\|urgent, clarification?, worsened, investigation_id?}` |
| GET | `/patients/{id}/requests` | Pending questions, photo and measurement requests (poll every few seconds) |
| POST | `/requests/{id}/answer` | `{option_index}` or `{text}` / `{photo_asset:"day3"}` or `{photo_base64}` / `{value}` |
| GET | `/alerts?role=clinician\|caregiver\|patient&member_id=&open_only=` | Non-clinicians get a reduced view |
| GET | `/alerts/{id}` | Includes `evidence_summary` |
| POST | `/alerts/{id}/ack` · `/contacted` · `/action` · `/resolve` | Clinician only. `resolve` needs `reason` |
| GET | `/notifications?member_id=` · POST `/notifications/{id}/read` | Delivered messages (reading one ≠ acknowledging an alert) |
| GET | `/investigations/{id}?include_messages=` | Summary, requests, and `steps` (audit trail for the "AI reasoning" panel) |
| GET | `/patients/{id}/investigations` · `/audit?patient_id=&ref_type=&ref_id=` | |
| GET | `/patients/{id}/medications` · POST `/medications/dose` | `{med_id, scheduled_for, status: taken\|not_taken\|postponed\|unknown, actor}` |
| GET | `/caregiver/{id}/digest?refresh=` · `/caregiver/{id}/tasks` · POST `/caregiver/tasks/{id}/done` | |
| POST | `/demo/reset` · `/demo/scenario/{name}` · `/demo/run/{checkin\|medication\|digest\|sweep}` · `/demo/answer_pending` · `/demo/clock/advance?seconds=` · `/demo/llm_mode/{mode}` · GET `/demo/status` | |

## Connecting the app

- **Android emulator:** the default URL `http://10.0.2.2:8000` points at your PC.
- **Physical phone:** put the phone on the same Wi-Fi as your PC. In the app, open **Profile → Settings & language → AI server** and set `http://<your-PC-LAN-IP>:8000`. You may also need to allow port 8000 through the Windows firewall.

Changes the mobile app needs to use these endpoints (not done yet):
- **`CheckInScreen`:** POST the form to `/checkin`. Send chips as keys, not translated labels:
  - `redness, swelling, warmth, drainage, bad_smell` (wound chips, in screen order);
  - `chills, fever, nausea, dizziness, shortness_of_breath, calf_pain` (other chips).

  If the response has `clarification`, show it, then answer it via `/requests/{id}/answer`.
- **Requests:** poll `GET /patients/sarah/requests` and show questions and photo requests. `WoundScanScreen` can send `photo_base64`.
- **Family screens:** read `GET /caregiver/ahmed/digest`, `/caregiver/ahmed/tasks` and `/alerts?role=caregiver&member_id=ahmed`.
- **Demo data:** `src/data/mock.ts` still says day 6 and has no cefuroxime. The backend uses day 3 and adds cefuroxime 500 mg at 08:00/14:00/20:00 (fictional, not a penicillin).
