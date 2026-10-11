# Agent refinements and connected patient UI

The teammate's `mobile/` UI remains the frontend. These additions support postoperative patients generally; age and family involvement are not prerequisites.

## Workflow

1. LangGraph collects context, reads evidence, and requests permitted missing information.
2. Question selection is instructed to focus on the trigger. Code prevents repeating matching questions/options within the investigation or reusing an already pending request. Recent usable measurements avoid another measurement request. Unknown evidence stays unknown.
3. An independent `review_evidence` node renders cited facts directly from saved observations, with units, timestamps, quality and simulation labels. It flags stale/future evidence and differing same-time measurements. Original model paraphrases remain in the review audit. Free-text trends, handover and interpretation are explicitly **not semantically or clinically validated** by this check.
4. Clinicians record contact and action, then optionally schedule follow-up with an instruction, deadline and required evidence types. The coordinator tracks waiting, overdue and evidence-ready states. Resolution requires clinician verification and all requested evidence types collected after the task/action. Evidence collection alone never resolves an alert.
5. Protocol warnings become focused clarification questions with the documents used by the draft. These are document references, not independently verified sentence citations. A request is saved to the care team's local inbox; it does not remove warnings. Unresolved questions are preserved in the confirmed plan.

## Frontend

- Upload PDF, sample document and Analyze now call the existing document/compiler routes. Unreadable image scans show the backend's OCR limitation instead of pretending success.
- Protocol review polls the actual draft and confirms its saved ID. Clarification questions can be sent to the local care-team inbox.
- Medication cards use the active plan and dose log. Due reminders appear on Home; taken/not-taken/postponed responses are persisted. As-needed and expired courses do not generate timed doses when course dates are available.
- Optional package photos are attached manually to a medicine after checking its name/strength. Images are decoded, resized and saved as JPEG; changing the medicine identity invalidates the old association. Photos do not identify medicines or prove ingestion.
- Requests displays clinician-defined follow-up tasks.
- Family Access saves sharing categories separately for each linked family member. Account linking starts with no AI sharing permissions. Revocation also hides existing support tasks and invalidates older digests when a new plan revision is saved.

## Account identity

`POST /account/ai-context` verifies the bearer token against the configured .NET account service's `GET /api/auth/me`. Patient AI IDs are `acct_<profile id>` and family memberships are scoped to the selected patient. Account records require authentication, including indirect draft/request/alert IDs. Family reads use permission-filtered views. Account errors never fall back to Sarah's seeded record.

The local browser defaults to the local account API on port 8080. The FastAPI `SURGIGUARD_API_URL` must identify the same account service used to sign in. With multiple followed patients, explicit selection is required; the AI context currently reports that requirement rather than choosing one silently.

New accounts begin with an empty AI plan and placeholder database profile fields; no demo medications or baselines are copied. Clinical profile completeness and clinician assignment still need to be configured before real use. Public fictional demo routes remain available locally. This is a prototype, not production authentication or clinical certification.

## Testing and preview

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests -q
```

`tests/test_agent_refinements.py` covers unsupported measurement paraphrases, stale evidence, conflicts, duplicate questions, fresh measurement reuse, follow-up timing/types, package-photo association, expired/as-needed schedules, document clarification, account isolation and sharing revocation. Existing suites cover urgent model-independent handling, LLM failure, restart recovery and the full demo lifecycle. These are offline/stub evaluations, not a benchmark of live model medical quality.

`GET /patients/{patient_id}/agent-metrics` reports up to 100 investigations, separated by execution mode: finished/incomplete cases, tool calls, patient requests, report-validation retries, review issues and elapsed time. Time includes patient waits and demo clock advances. These operational measurements are not a clinical accuracy score.

```powershell
cd mobile
npx tsc --noEmit
npm run build:web
```

Open `http://localhost:8000/app/`, then **Medications** to add a package photo and record an answer for a due dose. The clinic at `/agent-demo/#clinic` exposes follow-up scheduling after a clinician action. `./scripts/start-local.ps1 -NoBrowser -AiMode live` launches the local services with external notifications disabled.

Reminders currently use the in-app UI/local notification inbox. Push delivery, browser notifications while the app is closed, and native camera/document selection for these new uploads need a separate delivery integration. Use fictional data with the configured live provider.
