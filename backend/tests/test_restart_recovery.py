"""Recovery must preserve patient requests, budgets, deadlines and urgent precedence."""

import os
import subprocess
import sys
from datetime import timedelta

import pytest

from app import audit, clock, db, llm, monitor, requests_service, runner
from app import models as m
from app.agents import evidence, investigation
from app.config import settings


def checkpoint(repo, name="ask_followup_question", arguments=None):
    inv = repo.add(m.Investigation(patient_id="sarah", deadline=clock.now() + timedelta(seconds=120)))
    arguments = arguments or {"text": "How are you feeling today?", "options": ["About the same", "More tired"]}
    call = llm.ToolCall("restart-call", name, arguments)
    messages = [{"role": "system", "content": investigation.SYSTEM},
                {"role": "user", "content": investigation.context_message(repo, inv)},
                llm.Reply(content="Gather evidence", tool_calls=[call]).message]
    inv.tool_calls = 1
    investigation._save(repo, inv, messages, {"phase": "executing", "tool_call_id": call.id,
                                              "tool": name, "arguments": arguments})
    return inv, call, messages


def test_request_and_checkpoint_rollback_together_then_recover_once(repo, monkeypatch):
    inv, call, messages = checkpoint(repo)
    original = investigation._save

    def crash(*args, **kwargs):
        raise RuntimeError("Process interrupted after request creation")

    monkeypatch.setattr(investigation, "_save", crash)
    with pytest.raises(RuntimeError):
        investigation._execute_tool(repo, inv, messages, call)
    repo.s.expire_all()
    assert not repo.all(m.PatientRequest, m.PatientRequest.investigation_id == inv.id)
    assert repo.get(m.Investigation, inv.id).state["pending"]["phase"] == "executing"
    monkeypatch.setattr(investigation, "_save", original)
    assert investigation.recover(repo) == [inv.id]
    repo.s.expire_all()
    recovered = repo.get(m.Investigation, inv.id)
    assert recovered.status == "waiting_patient"
    assert recovered.tool_calls == 1 and recovered.patient_requests == 1
    assert investigation.recover(repo) == []
    assert len(repo.all(m.PatientRequest, m.PatientRequest.investigation_id == inv.id)) == 1


def test_saved_answer_resumes_when_dispatch_was_lost(repo, monkeypatch):
    inv, call, messages = checkpoint(repo)
    investigation._execute_tool(repo, inv, messages, call)
    req = repo.get(m.PatientRequest, inv.state["pending"]["request_id"])
    monkeypatch.setattr(investigation, "resume", lambda *args: None)
    requests_service.answer(repo, req.id, m.RequestAnswer(option_index=0))
    assert inv.status == "waiting_patient" and req.status == "answered"
    investigation.recover(repo)
    repo.s.expire_all()
    restored = repo.get(m.Investigation, inv.id)
    results = [msg for msg in restored.state["messages"] if msg.get("tool_call_id") == call.id]
    assert len(results) == 1 and req.answer_observation_id in results[0]["content"]
    assert len(repo.all(m.PatientRequest, m.PatientRequest.tool_call_id == call.id)) == 1


def test_expired_investigation_goes_to_review_without_llm(repo, monkeypatch):
    inv, _, _ = checkpoint(repo)
    clock.advance(121)
    monkeypatch.setattr(llm, "chat_tools", lambda *a, **k: pytest.fail("Deadline recovery called the LLM"))
    investigation.recover(repo)
    repo.refresh(inv)
    assert inv.status == "incomplete" and inv.alert_id
    assert repo.get(m.Alert, inv.alert_id).state != "resolved"
    assert investigation.recover(repo) == []


def test_server_startup_recovers_persisted_work(repo):
    from fastapi.testclient import TestClient
    from app.main import app
    inv, _, _ = checkpoint(repo)
    with TestClient(app):
        repo.refresh(inv)
        assert inv.status == "waiting_patient"
        assert len(repo.all(m.PatientRequest, m.PatientRequest.investigation_id == inv.id)) == 1


def test_deadline_arriving_during_llm_call_discards_late_tool(repo, monkeypatch):
    inv = repo.add(m.Investigation(patient_id="sarah", deadline=clock.now() + timedelta(seconds=1)))

    def late_reply(*args, **kwargs):
        clock.advance(2)
        return llm.Reply(content="Next", tool_calls=[llm.ToolCall("late", "get_wound_photos", {})])

    monkeypatch.setattr(llm, "chat_tools", late_reply)
    investigation.run(inv.id)
    repo.refresh(inv)
    assert inv.status == "incomplete" and inv.alert_id
    assert not [e for e in audit.trail(repo, "investigation", inv.id) if e.kind == "tool.call"]


def test_urgent_alert_blocks_recovery(repo, monkeypatch):
    inv, _, _ = checkpoint(repo)
    # Simulate an urgent alert persisted before the old worker was interrupted.
    repo.add(m.Alert(patient_id="sarah", level="urgent", title="Urgent demo", reason="Demo", source="rule"))
    monkeypatch.setattr(llm, "chat_tools", lambda *a, **k: pytest.fail("Urgent recovery called the LLM"))
    investigation.recover(repo)
    repo.refresh(inv)
    assert inv.status == "aborted_urgent"
    assert not repo.all(m.PatientRequest, m.PatientRequest.investigation_id == inv.id)


def test_urgent_arriving_during_llm_call_is_not_overwritten(repo, monkeypatch):
    inv = repo.add(m.Investigation(patient_id="sarah", deadline=clock.now() + timedelta(seconds=120)))

    def reply_after_urgent(*args, **kwargs):
        with db.session_scope() as other:
            monitor.ingest(other, m.ObservationIn(type="spo2", value=88, source="device"))
        return llm.Reply(content="Next", tool_calls=[llm.ToolCall("late-call", "get_wound_photos", {})])

    monkeypatch.setattr(llm, "chat_tools", reply_after_urgent)
    investigation.run(inv.id)
    repo.refresh(inv)
    assert inv.status == "aborted_urgent"
    assert not [e for e in audit.trail(repo, "investigation", inv.id) if e.kind == "tool.call"]


def test_completion_effects_are_atomic_and_retry_does_not_duplicate(repo, monkeypatch):
    inv, _, _ = checkpoint(repo)
    summary = evidence.fallback(repo, inv, "Demo review")
    original = investigation.notify
    monkeypatch.setattr(investigation, "notify", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("Interrupted")))
    with pytest.raises(RuntimeError):
        investigation.complete(repo, inv, summary, "incomplete")
    repo.refresh(inv)
    assert inv.status == "running" and inv.alert_id is None
    assert not repo.all(m.Alert, m.Alert.investigation_id == inv.id)
    monkeypatch.setattr(investigation, "notify", original)
    investigation.complete(repo, inv, summary, "incomplete")
    investigation.complete(repo, inv, summary, "incomplete")
    assert len(repo.all(m.Alert, m.Alert.investigation_id == inv.id)) == 1
    assert len(repo.all(m.CaregiverTask, m.CaregiverTask.dedupe_key == f"inv:{inv.id}")) == 1


def test_runner_coalesces_queued_and_running_jobs_and_releases_failures(repo, monkeypatch):
    callbacks = []

    class Executor:
        def submit(self, callback):
            callbacks.append(callback)

    monkeypatch.setattr(settings, "run_agents_inline", False)
    monkeypatch.setattr(runner, "_executor", Executor())
    calls = []
    monkeypatch.setitem(runner._jobs, "recovery_test", lambda key: calls.append(key))
    assert runner.submit("recovery_test", "same")
    assert not runner.submit("recovery_test", "same")
    assert runner.is_pending("recovery_test", "same")
    callbacks.pop()()
    assert calls == ["same"] and not runner.is_pending("recovery_test", "same")
    monkeypatch.setitem(runner._jobs, "recovery_test", lambda key: (_ for _ in ()).throw(RuntimeError("failed")))
    assert runner.submit("recovery_test", "same")
    callbacks.pop()()
    assert not runner.is_pending("recovery_test", "same")


def test_recovery_in_a_fresh_process_keeps_the_same_request(repo, tmp_path):
    url = "sqlite:///" + (tmp_path / "restart.db").as_posix()
    db.configure(url)
    from seed.demo_seed import load
    with db.session_scope() as stored:
        load(stored)
        inv, _, _ = checkpoint(stored)
        inv_id = inv.id
    script = """
import sys
from datetime import datetime
import app.main
from app import clock, db
from app.agents import investigation
clock.freeze(datetime(2026, 10, 10, 15, 30))
db.configure(sys.argv[1])
with db.session_scope() as repo:
    investigation.recover(repo)
"""
    env = {**os.environ, "LLM_MODE": "stub", "RUN_AGENTS_INLINE": "1", "SCHEDULER_ENABLED": "0"}
    for _ in range(2):
        subprocess.run([sys.executable, "-c", script, url], env=env, check=True, capture_output=True, timeout=45)
    with db.session_scope() as restored:
        inv = restored.get(m.Investigation, inv_id)
        assert inv.status == "waiting_patient" and inv.tool_calls == 1 and inv.patient_requests == 1
        requests = restored.all(m.PatientRequest, m.PatientRequest.investigation_id == inv_id)
        assert len(requests) == 1 and requests[0].id == inv.state["pending"]["request_id"]


@pytest.mark.parametrize("broken", ["missing_request", "legacy_call", "malformed_tool"])
def test_inconsistent_checkpoints_go_to_review(repo, broken):
    inv, _, messages = checkpoint(repo)
    if broken == "missing_request":
        inv.status = "waiting_patient"
        investigation._save(repo, inv, messages, {"request_id": "missing", "tool": "ask_followup_question", "tool_call_id": "x"})
    elif broken == "legacy_call":
        investigation._save(repo, inv, messages)
    else:
        investigation._save(repo, inv, messages, {"phase": "executing"})
    investigation.recover(repo)
    repo.refresh(inv)
    assert inv.status == "incomplete" and inv.alert_id
    assert not repo.all(m.PatientRequest, m.PatientRequest.investigation_id == inv.id)
