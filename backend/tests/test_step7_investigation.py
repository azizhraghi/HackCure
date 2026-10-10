import pytest

from app import audit, clock, monitor, requests_service, sweep
from app import models as m
from app.config import settings
from app.tools import investigation_tools as tools
from seed import simulator


def fresh(repo, model, id_):
    repo.s.expire_all()
    return repo.get(model, id_)


def start_infection(repo) -> m.Investigation:
    res = simulator.inject(repo, "infection_pattern")
    inv_id = next(r["investigation_id"] for r in res["results"] if r["investigation_id"])
    return fresh(repo, m.Investigation, inv_id)


def pending(repo, inv_id):
    repo.s.expire_all()
    return repo.all(m.PatientRequest, m.PatientRequest.investigation_id == inv_id, m.PatientRequest.status == "pending")


def drive(repo, inv_id, question_answer=m.RequestAnswer(option_index=1)):
    """Answer every request like the app would: day-3 photo, then the multiple-choice question."""
    for _ in range(5):
        reqs = pending(repo, inv_id)
        if not reqs:
            break
        req = reqs[0]
        body = m.RequestAnswer(photo_asset="day3") if req.kind == "photo" else question_answer
        requests_service.answer(repo, req.id, body)
    return fresh(repo, m.Investigation, inv_id)


def test_infection_pattern_full_investigation(repo):
    inv = start_infection(repo)
    assert inv.status == "waiting_patient"
    (req,) = pending(repo, inv.id)
    assert req.kind == "photo"
    inv = drive(repo, inv.id)

    assert inv.status == "finished"
    assert inv.patient_requests <= settings.max_patient_requests == 2
    assert inv.tool_calls <= settings.max_tool_calls
    s = inv.summary
    assert s["evidence_status"] == "complete"
    # every claim references a real observation of the right source type
    for c in s["patient_reported"]:
        assert fresh(repo, m.Observation, c["observation_id"]).source in ("patient", "caregiver_on_behalf")
    for c in s["device_measured"]:
        o = fresh(repo, m.Observation, c["observation_id"])
        assert o.source == "device" and c["quality"] == o.quality
    assert s["patient_reported"] and s["device_measured"]
    assert "not a diagnosis" in s["ai_interpretation"].lower()
    assert "+22%" in s["what_changed"]
    assert any("Cefuroxime" in c["text"] for c in s["patient_reported"])  # the missed antibiotic dose

    alert = fresh(repo, m.Alert, inv.alert_id)
    assert alert.level == "attention" and alert.investigation_id == inv.id and alert.assigned_to == "dr_ruiz"
    assert repo.first(m.CaregiverTask, m.CaregiverTask.caregiver_id == "ahmed",
                      m.CaregiverTask.dedupe_key == f"inv:{inv.id}")
    assert repo.first(m.Notification, m.Notification.member_id == "sarah", m.Notification.kind == "next_step")
    kinds = [e.kind for e in audit.trail(repo, "investigation", inv.id)]
    assert {"agent.start", "tool.call", "agent.paused", "agent.resumed", "evidence.validated",
            "agent.finished"} <= set(kinds)


def test_timeout_finishes_incomplete_and_escalates(repo):
    inv = start_infection(repo)
    clock.advance(settings.investigation_timeout_s + 1)
    out = sweep.run(repo)
    inv = fresh(repo, m.Investigation, inv.id)
    # the unanswered photo request expires, the agent resumes, sees the deadline and stops
    assert out["expired_requests"] and inv.status == "incomplete"
    assert any(e.kind == "agent.timeout" for e in audit.trail(repo, "investigation", inv.id))
    assert inv.summary["evidence_status"] == "incomplete"
    assert any("incomplete" in x.lower() or "timed out" in x.lower() for x in inv.summary["missing_or_conflicting"])
    alert = fresh(repo, m.Alert, inv.alert_id)
    assert alert and "evidence incomplete" in alert.title and alert.assigned_to == "dr_ruiz"
    assert not pending(repo, inv.id)


def test_red_flag_answer_aborts_and_fires_urgent(repo):
    inv = start_infection(repo)
    drive(repo, inv.id, question_answer=m.RequestAnswer(text="No chills but I fainted this morning"))
    inv = fresh(repo, m.Investigation, inv.id)
    assert inv.status == "aborted_urgent"
    repo.s.expire_all()
    assert repo.first(m.Alert, m.Alert.level == "urgent", m.Alert.rule == "red_flag_text")


def test_llm_down_still_ends_with_rule_summary(repo, monkeypatch):
    monkeypatch.setattr(settings, "llm_mode", "off")
    inv = start_infection(repo)
    assert inv.status == "incomplete" and inv.summary["generated_by"] == "rules (fallback)"
    assert "not a diagnosis" in inv.summary["ai_interpretation"].lower()
    assert fresh(repo, m.Alert, inv.alert_id).level == "attention"


def test_bad_observation_ids_rejected_then_retried(repo):
    inv = monitor.request_investigation(repo, "sarah", {"signals": [], "test_flags": ["bad_ids_first"]})
    inv = drive(repo, inv.id)
    assert inv.status == "finished" and inv.evidence_retries == 1
    assert "obs_doesnotexist" not in str(inv.summary)
    validations = [e.data for e in audit.trail(repo, "investigation", inv.id) if e.kind == "evidence.validated"]
    assert validations[0]["ok"] is False and validations[-1]["ok"] is True


def test_tool_budget_forces_finish(repo):
    inv = monitor.request_investigation(repo, "sarah", {"signals": [], "test_flags": ["never_finish"]})
    inv = fresh(repo, m.Investigation, inv.id)
    assert inv.tool_calls == settings.max_tool_calls and inv.status == "incomplete"


def test_patient_request_limits_enforced_in_code(repo):
    inv = repo.add(m.Investigation(patient_id="sarah", deadline=clock.now(), patient_requests=2))
    ctx = tools.Ctx(repo, inv)
    assert "limit" in tools.ask_followup_question(ctx, "How are you feeling now?", ["ok", "bad"])["error"]
    inv.patient_requests = 0
    plan = repo.plan("sarah")
    plan_row = repo.first(m.SurveillancePlan)
    plan_row.plan = {**plan, "allowed_tests": ["question"]}
    repo.add(plan_row)
    assert "not an allowed test" in tools.request_wound_photo(ctx, "x")["error"]
    assert "not an allowed test" in tools.request_measurement(ctx, "bp", "x")["error"]


def test_question_with_dose_advice_is_rejected(repo):
    inv = repo.add(m.Investigation(patient_id="sarah", deadline=clock.now()))
    ctx = tools.Ctx(repo, inv)
    r = tools.ask_followup_question(ctx, "Did you take an extra antibiotic dose of 500 mg?", ["yes", "no"])
    assert "rejected" in r["error"]


def test_investigation_api_shows_steps(client, repo):
    inv = start_infection(repo)
    drive(repo, inv.id)
    body = client.get(f"/investigations/{inv.id}").json()
    assert body["status"] == "finished" and body["summary"]
    assert any(s["kind"] == "tool.call" for s in body["steps"])
    assert len(body["requests"]) == 2


def test_answer_via_api(client, repo):
    inv = start_infection(repo)
    (req,) = pending(repo, inv.id)
    r = client.post(f"/requests/{req.id}/answer", json={"photo_asset": "day3"})
    assert r.status_code == 200 and r.json()["status"] == "answered"
    assert client.post(f"/requests/{req.id}/answer", json={"photo_asset": "day3"}).status_code == 409
