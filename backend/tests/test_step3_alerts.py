import pytest

from app import alerts, audit, clock, notifications, sweep
from app import models as m


def _urgent(repo):
    return alerts.create(repo, "sarah", "urgent", "Low oxygen", "SpO2 88%", "rule", rule="spo2_low")


def test_created_alert_is_routed_and_notified(repo):
    a = _urgent(repo)
    assert a.state == "assigned" and a.assigned_to == "dr_ruiz"
    who = {n.member_id for n in repo.all(m.Notification, m.Notification.ref_id == a.id)}
    assert who == {"dr_ruiz", "sarah", "ahmed"}


def test_unacked_alert_escalates_after_timeout(repo):
    a = _urgent(repo)
    clock.advance(59)
    assert sweep.run(repo)["escalated_alerts"] == []
    clock.advance(2)
    assert sweep.run(repo)["escalated_alerts"] == [a.id]
    a = repo.refresh(a)
    assert a.escalated and a.assigned_to == "dr_oncall"
    assert any(e.kind == "alert.escalated" for e in audit.trail(repo, "alert", a.id))
    assert repo.first(m.Notification, m.Notification.member_id == "dr_oncall", m.Notification.kind == "escalation")
    # escalation happens once
    clock.advance(120)
    assert sweep.run(repo)["escalated_alerts"] == []


def test_notification_read_is_not_ack(repo):
    a = _urgent(repo)
    n = repo.first(m.Notification, m.Notification.member_id == "dr_ruiz", m.Notification.ref_id == a.id)
    notifications.mark_read(repo, n.id, "dr_ruiz")
    assert repo.refresh(a).ack_at is None
    clock.advance(61)
    assert sweep.run(repo)["escalated_alerts"] == [a.id]


def test_acked_alert_does_not_escalate(repo):
    a = _urgent(repo)
    alerts.acknowledge(repo, a.id, "dr_ruiz")
    clock.advance(300)
    assert sweep.run(repo)["escalated_alerts"] == []


def test_only_clinician_acks_and_resolves(repo):
    a = _urgent(repo)
    for who in ("ahmed", "sarah", "agent:investigation"):
        with pytest.raises(alerts.AlertError) as e:
            alerts.acknowledge(repo, a.id, who)
        assert e.value.status == 403
        with pytest.raises(alerts.AlertError):
            alerts.resolve(repo, a.id, who, "fine now")
    with pytest.raises(alerts.AlertError) as e:
        alerts.resolve(repo, a.id, "dr_ruiz", "")
    assert e.value.status == 422


def test_full_lifecycle(repo):
    a = _urgent(repo)
    with pytest.raises(alerts.AlertError):
        alerts.patient_contacted(repo, a.id, "dr_ruiz")  # must ack first
    alerts.acknowledge(repo, a.id, "dr_ruiz")
    alerts.patient_contacted(repo, a.id, "dr_ruiz", "called Sarah")
    alerts.action_taken(repo, a.id, "dr_ruiz", "sent to ED")
    a = alerts.resolve(repo, a.id, "dr_ruiz", "Assessed in ED, discharged")
    assert a.state == "resolved" and a.resolution_reason
    events = [h["event"] for h in a.history]
    assert events == ["created", "assigned", "acknowledged", "patient_contacted", "action_taken", "resolved"]
    with pytest.raises(alerts.AlertError):
        alerts.acknowledge(repo, a.id, "dr_ruiz")


def test_repeat_is_deduplicated(repo):
    a1 = _urgent(repo)
    a2 = _urgent(repo)
    assert a1.id == a2.id and repo.refresh(a1).history[-1]["event"] == "repeat"


def test_api_lifecycle(client):
    from app.db import session_scope
    with session_scope() as r:
        a = _urgent(r)
    assert client.post(f"/alerts/{a.id}/ack", json={"actor": "ahmed"}).status_code == 403
    assert client.post(f"/alerts/{a.id}/ack", json={"actor": "dr_ruiz"}).json()["state"] == "acknowledged"
    assert client.post(f"/alerts/{a.id}/resolve", json={"actor": "dr_ruiz"}).status_code == 422
    r = client.post(f"/alerts/{a.id}/resolve", json={"actor": "dr_ruiz", "reason": "Reviewed, safe"})
    assert r.json()["state"] == "resolved"
    caregiver_view = client.get("/alerts", params={"role": "caregiver", "member_id": "ahmed"}).json()
    assert caregiver_view and "reason" not in caregiver_view[0]
