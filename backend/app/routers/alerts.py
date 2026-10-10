from fastapi import APIRouter, Depends, HTTPException, Query

from .. import alerts, notifications
from .. import models as m
from ..db import Repo, get_repo

router = APIRouter(tags=["alerts"])


def _run(fn, *args):
    try:
        return fn(*args)
    except alerts.AlertError as e:
        raise HTTPException(e.status, str(e)) from e


@router.get("/alerts")
def list_alerts(role: str = Query("clinician", pattern="^(patient|caregiver|clinician)$"),
                member_id: str | None = None, patient_id: str | None = "sarah", open_only: bool = False,
                repo: Repo = Depends(get_repo)):
    rows = alerts.visible_to(repo, role, member_id, patient_id)
    if open_only:
        rows = [a for a in rows if a.state != "resolved"]
    return [alerts.public(a, role) for a in rows]


@router.get("/alerts/{alert_id}")
def get_alert(alert_id: str, repo: Repo = Depends(get_repo)):
    a = _run(alerts.get, repo, alert_id)
    out = alerts.public(a)
    out["verifications"] = [v.model_dump() for v in repo.all(m.FollowupVerification,
                            m.FollowupVerification.alert_id == a.id, order=m.FollowupVerification.created_at)]
    action_at = next((h["at"] for h in reversed(a.history) if h["event"] == "action_taken"), None)
    if action_at:
        from datetime import datetime
        out["followup_observations"] = [o.model_dump() for o in repo.observations(a.patient_id,
                                       since=datetime.fromisoformat(action_at), limit=50)
                                       if o.source != "ai" and o.quality == "good"]
    else:
        out["followup_observations"] = []
    if a.investigation_id:
        inv = repo.get(m.Investigation, a.investigation_id)
        out["evidence_summary"] = inv.summary if inv else None
    return out


@router.post("/alerts/{alert_id}/ack")
def ack(alert_id: str, body: m.ActorBody, repo: Repo = Depends(get_repo)):
    return alerts.public(_run(alerts.acknowledge, repo, alert_id, body.actor, body.note))


@router.post("/alerts/{alert_id}/contacted")
def contacted(alert_id: str, body: m.ActorBody, repo: Repo = Depends(get_repo)):
    return alerts.public(_run(alerts.patient_contacted, repo, alert_id, body.actor, body.note))


@router.post("/alerts/{alert_id}/action")
def action(alert_id: str, body: m.ActorBody, repo: Repo = Depends(get_repo)):
    return alerts.public(_run(alerts.action_taken, repo, alert_id, body.actor, body.note))


@router.post("/alerts/{alert_id}/resolve")
def resolve(alert_id: str, body: m.ResolveBody, repo: Repo = Depends(get_repo)):
    return alerts.public(_run(alerts.resolve, repo, alert_id, body.actor, body.reason, body.verification_id))


@router.post("/alerts/{alert_id}/verify")
def verify(alert_id: str, body: m.VerificationIn, repo: Repo = Depends(get_repo)):
    return _run(alerts.verify, repo, alert_id, body).model_dump()


@router.get("/notifications")
def list_notifications(member_id: str, unread_only: bool = False, limit: int = 50, repo: Repo = Depends(get_repo)):
    where = [m.Notification.member_id == member_id]
    if unread_only:
        where.append(m.Notification.read_at == None)  # noqa: E711
    return repo.all(m.Notification, *where, order=m.Notification.created_at.desc(), limit=limit)


@router.post("/notifications/{notification_id}/read")
def read_notification(notification_id: str, body: m.ActorBody, repo: Repo = Depends(get_repo)):
    n = notifications.mark_read(repo, notification_id, body.actor)
    if n is None:
        raise HTTPException(404, "unknown notification for this member")
    return n
