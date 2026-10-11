# Investigation restart recovery

The main LangGraph investigation resumes from SQLite on server startup. The periodic sweep also requeues
work whose dispatch was interrupted. This covers the main `/patients` investigation workflow;
the older `/v1/demo` LangGraph workflow remains separate.

See [LANGGRAPH_INVESTIGATION.md](LANGGRAPH_INVESTIGATION.md) for graph stages and the clinician follow-up boundary.

## Recovery behavior

- A running investigation continues with its saved messages and existing tool/request budgets.
- A patient request still awaiting an answer stays open with its original ID and expiry.
- If the answer was stored before the worker was dispatched, recovery consumes that saved answer once.
- Expired requests become unknown evidence. An elapsed investigation deadline produces an incomplete
  report for clinician review. A scheduled photo can remain independent until its dressing window closes.
- An urgent alert aborts recovery. Urgent status and deadlines are checked again after a provider call.
- A tool call is checkpointed before execution. Its local database effects and result checkpoint then commit
  in one transaction. Interruption rolls back both; recovery executes the same call without charging a
  second tool call or creating a second patient request.
- Summary, alert, support tasks and notifications commit together. Retrying completion cannot create
  a second set of effects for an already completed investigation.
- An inconsistent or legacy ambiguous checkpoint goes to clinician review with incomplete evidence.

The runner coalesces identical queued/running jobs within one process. Run one Uvicorn worker for this
prototype. This is not a distributed queue: multiple server processes require database claims/leases.
The investigation tools currently write only to the local database; adding external delivery or other
external effects requires an outbox and idempotency keys. Protocol and digest job recovery is not included.

## This Windows machine

The NumPy 2.5.4 wheel was blocked by Windows application control. NumPy 2.3.5 loads successfully in the
existing Python 3.14 `backend/.venv` environment. SQLAlchemy uses its supported pure Python build.
The browser preview uses this existing environment.

Start the offline browser preview from the repository root:

```powershell
cd backend
$env:LLM_MODE='stub'
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Open `http://localhost:8000/prototype` for the integrated story, `/app/` for the patient app,
and `/agent-demo/` for the clinic workflow. Expected recovery generation needs live model access;
offline mode displays its unavailable state.

If frontend source changes, run `npm run build:web` from `mobile` before refreshing the patient app.
Tests run in stub mode; the restart tests include recovery in two fresh Python processes against the same
SQLite file and fault injection between request creation and checkpoint persistence.

Validation: `python -m pytest -q tests test_d3_demo.py` passed **145 tests** in offline mode,
and `npm run build:web` passed. The integrated prototype and its D1 patient forecast were checked in
the browser. One D2 retrieval check failed on the first suite run, passed in isolation, and passed on
the final complete run; no D2 source changes were required.
