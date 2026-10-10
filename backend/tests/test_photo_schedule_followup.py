from datetime import timedelta

import pytest

from app import alerts, clock, requests_service, wound_photos
from app import models as m
from app.agents import investigation


def test_photo_timing_boundaries_and_no_daily_requests(repo):
    assert wound_photos.eligibility(repo, "sarah")["status"] == "due"
    clock.advance(-7 * 3600)  # 08:30, before the permitted 09:00 opening
    assert not wound_photos.eligibility(repo, "sarah")["permitted"]
    assert not wound_photos.sweep(repo)
    clock.advance(30 * 60)
    assert wound_photos.eligibility(repo, "sarah")["permitted"]
    first = wound_photos.sweep(repo)
    assert first and wound_photos.sweep(repo) == first
    assert len(repo.pending_requests("sarah")) == 1
    clock.advance(11 * 3600)  # exact closing boundary: 20:00
    assert not wound_photos.eligibility(repo, "sarah")["permitted"]
    with pytest.raises(requests_service.RequestError):
        requests_service.answer(repo, first[0], m.RequestAnswer(photo_asset="day3", dressing_change_confirmed=True))
    clock.advance(19 * 3600)  # next day at 15:00: no dressing change on day 4
    assert wound_photos.eligibility(repo, "sarah")["status"] == "not_due"
    assert wound_photos.sweep(repo) == []


def test_missing_or_invalid_plan_does_not_authorize_photos(repo):
    row = repo.first(m.SurveillancePlan)
    for policy in (None, {"mode": "permitted_dressing_changes", "windows": [{"id": "bad", "day_offset": 2, "start": "20:00", "end": "09:00"}]}):
        row.plan = {**row.plan, "wound_photo_schedule": policy}
        repo.add(row)
        assert not wound_photos.eligibility(repo, "sarah")["permitted"]
        assert not wound_photos.sweep(repo)


def test_photo_confirmation_single_collection_and_plan_revalidation(repo):
    req_id = wound_photos.request(repo, "sarah")["request_id"]
    with pytest.raises(requests_service.RequestError, match="Confirm"):
        requests_service.answer(repo, req_id, m.RequestAnswer(photo_asset="day3"))
    assert repo.get(m.PatientRequest, req_id).status == "pending"
    row = repo.first(m.SurveillancePlan)
    original = row.plan
    row.plan = {**original, "version": 999}
    repo.add(row)
    with pytest.raises(requests_service.RequestError, match="not linked"):
        requests_service.answer(repo, req_id, m.RequestAnswer(photo_asset="day3", dressing_change_confirmed=True))
    row.plan = original
    repo.add(row)
    result = requests_service.answer(repo, req_id, m.RequestAnswer(photo_asset="day3", dressing_change_confirmed=True))
    assert result["status"] == "answered"
    assert wound_photos.eligibility(repo, "sarah")["status"] == "completed"
    assert not wound_photos.sweep(repo)
    with pytest.raises(requests_service.RequestError):
        requests_service.answer(repo, req_id, m.RequestAnswer(photo_asset="day3", dressing_change_confirmed=True))


def test_investigation_timeout_preserves_scheduled_photo(repo):
    inv = repo.add(m.Investigation(patient_id="sarah", deadline=clock.now() + timedelta(seconds=1)))
    req_id = wound_photos.request(repo, "sarah", inv.id)["request_id"]
    clock.advance(2)
    investigation.timeout(repo, inv)
    req = repo.get(m.PatientRequest, req_id)
    assert req.status == "pending" and req.investigation_id is None
    assert requests_service.answer(repo, req_id, m.RequestAnswer(photo_asset="day3", dressing_change_confirmed=True))["status"] == "answered"


def test_generic_photo_endpoint_cannot_bypass_schedule(client):
    r = client.post("/observations", json={"type": "photo", "source": "patient", "value": {"asset": "day3"}})
    assert r.status_code == 422


def _alert(repo):
    a = alerts.create(repo, "sarah", "attention", "Review", "Demo change", "monitor")
    alerts.acknowledge(repo, a.id, "dr_ruiz")
    return a


def _action(repo, a):
    alerts.patient_contacted(repo, a.id, "dr_ruiz", "Contact recorded")
    alerts.action_taken(repo, a.id, "dr_ruiz", "Clinician decision recorded")


def _verify(actor="dr_ruiz", ids=None, outcome="resolved"):
    return m.VerificationIn(actor=actor, summary="Follow-up assessment recorded", outcome=outcome, observation_ids=ids or ["missing"])


def test_alert_steps_and_verification_cannot_be_skipped(repo):
    a = _alert(repo)
    with pytest.raises(alerts.AlertError):
        alerts.action_taken(repo, a.id, "dr_ruiz", "Decision without contact")
    with pytest.raises(alerts.AlertError):
        alerts.resolve(repo, a.id, "dr_ruiz", "Looks resolved")
    with pytest.raises(alerts.AlertError):
        alerts.verify(repo, a.id, _verify())
    _action(repo, a)
    for who in ("sarah", "ahmed", "agent:investigation"):
        with pytest.raises(alerts.AlertError) as err:
            alerts.verify(repo, a.id, _verify(actor=who))
        assert err.value.status == 403
    assert a.state == "action_taken"


def test_verification_rejects_invalid_old_cross_patient_or_ai_evidence(repo):
    a = _alert(repo)
    old = repo.add(m.Observation(patient_id="sarah", type="checkin", source="patient", value={}, measured_at=clock.now() - timedelta(seconds=1)))
    foreign = repo.add(m.Observation(patient_id="another", type="checkin", source="patient", value={}))
    ai = repo.add(m.Observation(patient_id="sarah", type="checkin", source="ai", value={}))
    bad = repo.add(m.Observation(patient_id="sarah", type="temp", source="device", quality="unusable", value={}))
    _action(repo, a)
    for oid in ("missing", old.id, foreign.id, ai.id, bad.id):
        with pytest.raises(alerts.AlertError):
            alerts.verify(repo, a.id, _verify(ids=[oid]))
    assert repo.all(m.FollowupVerification) == []


def test_needs_review_stays_open_successful_verification_is_required(repo):
    a = _alert(repo)
    _action(repo, a)
    clock.advance(1)
    obs = repo.add(m.Observation(patient_id="sarah", type="checkin", source="patient", value={"comment": "Follow-up evidence"}))
    v = alerts.verify(repo, a.id, _verify(ids=[obs.id], outcome="needs_review"))
    assert a.state == "action_taken"
    with pytest.raises(alerts.AlertError):
        alerts.resolve(repo, a.id, "dr_ruiz", "Close", v.id)
    good = alerts.verify(repo, a.id, _verify(ids=[obs.id]))
    assert a.state == "verified"
    with pytest.raises(alerts.AlertError):
        alerts.resolve(repo, a.id, "dr_ruiz", "Close", v.id)
    assert alerts.resolve(repo, a.id, "dr_ruiz", "Follow-up verified", good.id).state == "resolved"
