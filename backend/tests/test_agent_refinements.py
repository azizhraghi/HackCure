"""Scenario checks for evidence grounding, request burden, follow-up and account isolation."""
import io
import pytest
from datetime import timedelta
from PIL import Image
from app import alerts, clock, models as m
from app.agents import evidence, evidence_review, followup, medication
from app.tools import investigation_tools as tools


def test_reviewer_replaces_unsupported_claim_with_recorded_fact_and_flags_quality(repo):
    inv = repo.add(m.Investigation(patient_id="sarah", deadline=clock.now()))
    summary = evidence.fallback(repo, inv, "test")
    obs = repo.add(m.Observation(patient_id="sarah", type="temp", value={"value": 37.2},
                                 unit="C", quality="questionable", measured_at=clock.now() - timedelta(hours=10)))
    summary.device_measured = [m.DeviceClaim(text="Temperature is 99 C and normal", observation_id=obs.id)]
    result = evidence_review.review(repo, "sarah", summary)
    assert "99 C" not in summary.device_measured[0].text
    assert "37.2" in summary.device_measured[0].text
    assert result["status"] == "needs_review" and result["checks"][-1]["freshness"] == "stale"
    assert result["checks"][-1]["quality"] == "questionable"


def test_reviewer_retains_conflicts_instead_of_averaging(repo):
    inv = repo.add(m.Investigation(patient_id="sarah", deadline=clock.now()))
    summary = evidence.fallback(repo, inv, "test")
    summary.device_measured = []
    for value in (72, 110):
        obs = repo.add(m.Observation(patient_id="sarah", type="hr", value={"value": value}))
        summary.device_measured.append(m.DeviceClaim(text="same", observation_id=obs.id))
    result = evidence_review.review(repo, "sarah", summary)
    assert any("Conflicting" in issue for issue in result["issues"])


def test_repeated_answered_question_does_not_consume_patient_budget(repo):
    inv = repo.add(m.Investigation(patient_id="sarah", deadline=clock.now() + timedelta(minutes=5)))
    ctx = tools.Ctx(repo, inv)
    first = tools.ask_followup_question(ctx, "Do you feel more tired today?", ["Yes", "No"])
    req = repo.get(m.PatientRequest, first["request_id"])
    req.status, req.answer = "answered", {"text": "No"}
    repo.add(req)
    result = tools.ask_followup_question(ctx, "Do you feel more tired today?", ["Yes", "No"])
    assert result["status"] == "already_available" and result["answer"]["text"] == "No"
    assert inv.patient_requests == 1


def test_recent_usable_measurement_avoids_reasking(repo):
    obs = repo.add(m.Observation(patient_id="sarah", type="temp", value={"value": 37.1}))
    inv = repo.add(m.Investigation(patient_id="sarah", deadline=clock.now() + timedelta(minutes=5)))
    result = tools.request_measurement(tools.Ctx(repo, inv), "temp")
    assert result["status"] == "already_available" and result["observation_id"] == obs.id
    assert inv.patient_requests == 0


def test_followup_needs_all_requested_post_action_evidence_and_never_closes(repo):
    alert = alerts.create(repo, "sarah", "attention", "Review", "demo", "test")
    alerts.acknowledge(repo, alert.id, "dr_ruiz")
    alerts.patient_contacted(repo, alert.id, "dr_ruiz", "Called demo patient")
    alerts.action_taken(repo, alert.id, "dr_ruiz", "Review a later check-in and temperature")
    task = followup.create(repo, alert.id, m.FollowupTaskIn(actor="dr_ruiz", instruction="Submit the requested check-in and reading",
                           due_at=clock.now() + timedelta(minutes=5), evidence_types=["checkin", "temp"]))
    followup.sweep(repo)
    assert task.status == "waiting" and not task.observation_ids
    clock.advance(301)
    followup.sweep(repo)
    assert task.status == "overdue"
    for kind in ("checkin", "temp"):
        repo.add(m.Observation(patient_id="sarah", type=kind, source="patient", value={"value": 3}))
    followup.sweep(repo)
    assert task.status == "evidence_ready" and len(task.observation_ids) == 2
    assert alert.state == "action_taken"
    with pytest.raises(alerts.AlertError, match="every evidence type"):
        alerts.verify(repo, alert.id, m.VerificationIn(actor="dr_ruiz", summary="Incomplete selection", outcome="resolved",
                                                     observation_ids=task.observation_ids[:1]))
    alerts.verify(repo, alert.id, m.VerificationIn(actor="dr_ruiz", summary="Both requested evidence types reviewed",
                                                outcome="resolved", observation_ids=task.observation_ids))
    assert alert.state == "verified"


def test_package_photo_is_validated_and_does_not_follow_a_changed_medicine(client, repo):
    assert client.post('/patients/sarah/medications/m1/photo', files={"file": ("x.png", b"not an image", "image/png")}).status_code == 422
    data = io.BytesIO()
    Image.new("RGB", (80, 80), "blue").save(data, format="PNG")
    result = client.post('/patients/sarah/medications/m1/photo', files={"file": ("box.png", data.getvalue(), "image/png")})
    assert result.status_code == 200 and result.json()["url"].startswith("data:image/jpeg;base64,")
    med = medication.plan_med(repo.plan("sarah"), "m1")
    assert medication.photo(repo, "sarah", med)
    assert medication.photo(repo, "sarah", {**med, "dose": "different strength"}) is None


def test_expired_and_as_needed_medications_do_not_generate_reminders(repo):
    plan = {"document_info": {"discharge_date": "2026-10-01"}, "medications": [
        {"id": "old", "times": ["14:00"], "duration_days": 3},
        {"id": "prn", "times": ["14:00"], "as_needed": True}]}
    assert medication.slots(plan, clock.now().replace(hour=0), clock.now()) == []


def test_clarification_preserves_sources_and_does_not_resolve_warnings(client, repo):
    from app.agents.protocol import save_document
    doc = save_document(repo, "sarah", "plan.txt", "text/plain", b"Medicine schedule missing")
    draft = repo.add(m.PlanDraft(patient_id="sarah", document_ids=[doc.id], status="ready", plan={},
                                 warnings=[{"level": "medium", "item": "Medicine", "message": "No schedule found"}]))
    body = client.get(f'/plan-drafts/{draft.id}').json()
    assert body["clarifications"][0]["sources"][0]["document_id"] == doc.id
    result = client.post(f'/plan-drafts/{draft.id}/clarification-request', json={"actor": "sarah"})
    assert result.status_code == 200 and result.json()["notification_ids"]
    assert draft.warnings and body["clarifications"][0]["status"] == "unresolved"


def test_account_link_does_not_clone_sarah_and_blocks_cross_patient_access(client, repo, monkeypatch):
    from app import account_scope
    from app.routers import account_context
    async def identity(_):
        return {"user": {"role": "PATIENT", "first_name": "Demo", "last_name": "Account"}, "profile_id": "one"}
    monkeypatch.setattr(account_context, "verified", identity)
    monkeypatch.setattr(account_scope, "verified", identity)
    headers = {"Authorization": "Bearer fictional-test-token"}
    response = client.post('/account/ai-context', json={}, headers=headers)
    assert response.status_code == 200 and response.json()["patient_id"] == "acct_one"
    assert repo.plan("acct_one")["medications"] == []
    assert client.get('/patients/sarah/medications', headers=headers).status_code == 403
    assert client.get('/patients/acct_two/medications', headers=headers).status_code == 403
    assert client.get('/patients/acct_one/medications', headers=headers).status_code == 200


def test_account_records_require_auth_even_for_indirect_resource_ids(client, repo):
    draft = repo.add(m.PlanDraft(patient_id="acct_secret", document_ids=[]))
    assert client.get(f'/plan-drafts/{draft.id}').status_code == 401
    assert client.get('/patients/acct_secret/medications').status_code == 401


def test_sharing_switches_persist_and_revocation_hides_existing_support_tasks(client, repo):
    task = repo.add(m.CaregiverTask(patient_id="sarah", caregiver_id="ahmed", category="medications",
                                   text="Help with the scheduled medicine", created_by="test"))
    assert any(t["id"] == task.id for t in client.get('/caregiver/ahmed/tasks').json())
    result = client.put('/patients/sarah/sharing/ahmed', json={"categories": {"medications": False}})
    assert result.status_code == 200
    members = client.get('/patients/sarah/sharing').json()
    assert not next(m for m in members if m["id"] == "ahmed")["categories"]["medications"]
    assert not client.get('/caregiver/ahmed/tasks').json()
    assert client.post(f'/caregiver/tasks/{task.id}/done', json={"actor": "ahmed"}).status_code == 403


def test_patient_cannot_grant_sharing_to_an_unlinked_person(client):
    assert client.put('/patients/sarah/sharing/stranger', json={"categories": {"medications": True}}).status_code == 422


def test_public_dose_route_cannot_impersonate_internal_importer(client):
    response = client.post('/medications/dose', json={"patient_id": "sarah", "actor": "surgiguard-api", "med_id": "m1",
                                                    "scheduled_for": clock.now().replace(hour=14, minute=0, second=0, microsecond=0).isoformat(), "status": "taken"})
    assert response.status_code == 422
