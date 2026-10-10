# Agentic backend integration review

Reviewed `origin/agentic-backend` at `ca64f2c` on 2026-10-10. The combined work is on the local `codex/integrate-agentic-backend` branch. The previous D3/browser implementation is preserved in checkpoint `df1509f`.

## What the teammate implemented

| Component | Current implementation |
|---|---|
| Investigation | Custom resumable LLM tool loop; database state, evidence tools, questions/photos/measurement requests, budgets, deadlines and fallbacks |
| Evidence report | Schema and observation-ID validation, patient/device source separation, stored reading quality and rule-built fallback |
| Daily check-in | Structured form submission, urgent gate, worsening detection and one clarification question |
| Medication tracking | Deterministic reminders, dose logging and missed-dose flags |
| Caregiver digest | Permission-filtered inputs, checked LLM summary and template fallback |
| Monitoring and alerts | Reading-quality checks, deterministic demo urgent rules, deviation detection, routing and acknowledgement timeout escalation |
| Persistence and scheduling | SQLModel/SQLite, audit events, patient requests, scheduler and background worker threads |
| UI | Connected patient check-in, home, request list and family home; separate patient/family/clinic web dashboard |
| LLM access | Shared provider wrapper for Mistral, Groq and OpenRouter; per-feature routes, stub and off modes |

## Integration decisions

- `/app/` keeps the existing React Native screens rendered on web.
- `/agent-demo/` serves the teammate's agent dashboard and clinic controls.
- `/demo` and `/v1/demo` retain the earlier synthetic D3 workflow and its LangGraph investigation.
- The new agents remain on their existing custom loop. Replacing it with LangGraph is a separate architecture change; tools, state models and safety rules can be reused.
- Photo prompts now refer to dressing changes permitted by the care plan. The previous daily-photo instruction was removed from the investigation and chat prompts.
- Local inspection runs in stub mode to avoid live LLM calls.

## Remaining work affecting our Developer 3 scope

1. **Dressing-change timing:** wording is aligned, but the request tool still only checks `allowed_tests`; scheduling, eligibility and deferring photo requests need structured plan fields and code enforcement. Demo request timeouts are seconds, not real recovery timescales.
2. **D1/D2 contracts:** photo comparison is precomputed demo data; uploaded photos have no real D1 analysis. Care plans and chat context are seeded/static rather than supplied by D2.
3. **Follow-up verification:** the new alert API accepts a clinician resolution reason and permits direct resolution; it does not require the verification evidence enforced by the earlier D3 demo.
4. **Reliable background execution:** investigation state is stored, but work is dispatched to an in-process thread pool. Restart recovery and coordinated state transitions need further work before durable orchestration.
5. **Honest UI state:** the teammate's check-in screen confirms locally even if submission fails; clarification choices are marked answered before the response succeeds. The photo request button submits the synthetic `day3` asset. These need explicit failure/simulation states and real upload integration.
6. **Evidence strength:** a valid observation ID and source are checked, but these checks alone do not prove the model's description accurately reflects the observation. Clinician review remains necessary.
7. **Prototype access:** actor IDs and roles are supplied by callers; authentication and authorization for real patient data are not implemented.

Recommended next implementation: enforce care-plan photo eligibility and follow-up verification, then introduce LangGraph persistence/recovery around the existing investigation tools if LangGraph remains the team's chosen orchestrator.

## Validation

- `python -m pytest -q tests test_d3_demo.py`: **110 passed** (offline stub mode).
- `npm run build:web`: passed.
- Local HTTP checks: `/health`, `/app/`, `/app/app.js`, `/agent-demo/`, `/demo`, `/patients/sarah/today` and `/patients/sarah/requests` all returned 200.
- Windows application control blocked SQLAlchemy's compiled DLL. The environment now uses SQLAlchemy 2.1.4 built with its supported `DISABLE_SQLALCHEMY_CEXT=1` option. No Windows security settings were changed.

## Update: 2026-10-11

Remaining-work items 1 and 3 above are now implemented. Structured dressing windows govern both requests and uploads, require confirmation, and permit one collection per window. Photo collection can outlast an investigation deadline. The seeded schedule is fictional pending D2 integration.

The new alert workflow now enforces contact, action, post-action evidence, clinician verification and resolution. Failed verification keeps the alert open. The clinic UI exposes these steps; the patient web preview links to it. Home now uses backend photo timing, and Requests shows schedule, confirmation, explicit simulation labels and errors. Real uploads and the check-in failure states in item 5 remain outstanding.

Validation: 110 offline backend tests passed; web bundle built successfully; dashboard JavaScript syntax checked.
