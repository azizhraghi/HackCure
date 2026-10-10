"""S2 alert router + S3 lifecycle / escalation state machine.

created -> assigned -> acknowledged -> patient_contacted -> action_taken -> resolved

- Only clinicians acknowledge, progress and resolve; resolve needs a reason.
- A delivered or read notification is never an acknowledgement.
- No code path lowers an alert's level or closes it on behalf of an agent.
- Not acknowledged within ACK_TIMEOUT -> escalate to the plan's backup contact (once) and log it.
"""

from datetime import datetime, timedelta

from . import audit, clock
from . import models as m
from .config import settings
from .db import Repo
from .notifications import notify

ORDER = {s: i for i, s in enumerate(m.ALERT_STATES)}


class AlertError(Exception):
    def __init__(self, message: str, status: int = 409):
        super().__init__(message)
        self.status = status


def _hist(alert: m.Alert, event: str, by: str, note: str | None = None, **extra) -> None:
    alert.history = [*alert.history, {"event": event, "state": alert.state, "by": by, "at": clock.now().isoformat(),
                                      **({"note": note} if note else {}), **extra}]
    alert.updated_at = clock.now()


def create(repo: Repo, patient_id: str, level: str, title: str, reason: str, source: str, rule: str | None = None,
           evidence: dict | None = None, investigation_id: str | None = None, priority: str = "normal",
           actor: str = "system", patient_text: str | None = None) -> m.Alert:
    # De-duplicate: an open alert from the same rule at the same level absorbs repeats.
    if rule:
        existing = repo.first(m.Alert, m.Alert.patient_id == patient_id, m.Alert.rule == rule,
                              m.Alert.level == level, m.Alert.state != "resolved")
        if existing:
            _hist(existing, "repeat", actor, reason)
            repo.add(existing)
            audit.log(repo, patient_id, actor, "alert.repeat", {"reason": reason}, "alert", existing.id)
            return existing

    plan = repo.plan(patient_id)
    routing = plan.get("alert_routing", {}).get(level, {})
    alert = m.Alert(patient_id=patient_id, level=level, title=title, reason=reason, source=source, rule=rule,
                    evidence=evidence or {}, investigation_id=investigation_id, priority=priority)
    _hist(alert, "created", actor, reason)
    if routing.get("assign"):
        alert.assigned_to = routing["assign"]
        alert.state = "assigned"
        _hist(alert, "assigned", "router", assigned_to=alert.assigned_to)
    repo.add(alert)
    audit.log(repo, patient_id, actor, "alert.created",
              {"level": level, "title": title, "reason": reason, "source": source, "rule": rule,
               "assigned_to": alert.assigned_to}, "alert", alert.id)

    for member_id in routing.get("notify", []):
        member = repo.member(member_id)
        if member is None:
            continue
        body = reason
        if member.role == "patient":
            body = patient_text or plan.get("patient_texts", {}).get(
                "urgent" if level == "urgent" else "attention_next_step", reason)
        elif member.role == "caregiver":
            p = repo.patient(patient_id)
            name = p.first_name if p else "The patient"
            body = (f"{name} may need help now. Emergency services were advised; please stay with {name}."
                    if level == "urgent" else f"The care team is reviewing a change in {name}'s recovery.")
        notify(repo, patient_id, member_id, "alert", title, body, "alert", alert.id, category="alerts")
    return alert


def get(repo: Repo, alert_id: str) -> m.Alert:
    a = repo.get(m.Alert, alert_id)
    if a is None:
        raise AlertError(f"unknown alert {alert_id}", 404)
    return a


def _clinician(repo: Repo, alert: m.Alert, actor_id: str) -> m.CareTeamMember:
    member = repo.member(actor_id)
    if member is None or member.patient_id != alert.patient_id:
        raise AlertError(f"unknown actor {actor_id}", 403)
    if member.role != "clinician":
        raise AlertError("only a clinician can do this", 403)
    return member


def _advance(repo: Repo, alert: m.Alert, actor_id: str, target: str, note: str | None) -> m.Alert:
    if alert.state == "resolved":
        raise AlertError("alert already resolved")
    if ORDER[target] <= ORDER[alert.state]:
        raise AlertError(f"cannot go from {alert.state} to {target}")
    alert.state = target
    _hist(alert, target, actor_id, note)
    repo.add(alert)
    audit.log(repo, alert.patient_id, actor_id, f"alert.{target}", {"note": note}, "alert", alert.id)
    return alert


def acknowledge(repo: Repo, alert_id: str, actor_id: str, note: str | None = None) -> m.Alert:
    alert = get(repo, alert_id)
    _clinician(repo, alert, actor_id)
    if alert.ack_at is not None:
        raise AlertError("alert already acknowledged")
    alert.ack_by, alert.ack_at = actor_id, clock.now()
    return _advance(repo, alert, actor_id, "acknowledged", note)


def _require_ack(alert: m.Alert):
    if alert.ack_at is None:
        raise AlertError("acknowledge the alert first")


def patient_contacted(repo: Repo, alert_id: str, actor_id: str, note: str | None = None) -> m.Alert:
    alert = get(repo, alert_id)
    _clinician(repo, alert, actor_id)
    _require_ack(alert)
    return _advance(repo, alert, actor_id, "patient_contacted", note)


def action_taken(repo: Repo, alert_id: str, actor_id: str, note: str | None = None) -> m.Alert:
    alert = get(repo, alert_id)
    _clinician(repo, alert, actor_id)
    _require_ack(alert)
    return _advance(repo, alert, actor_id, "action_taken", note)


def resolve(repo: Repo, alert_id: str, actor_id: str, reason: str) -> m.Alert:
    alert = get(repo, alert_id)
    _clinician(repo, alert, actor_id)
    if not reason or len(reason.strip()) < 3:
        raise AlertError("a resolution reason is required", 422)
    if alert.ack_at is None:  # resolving implies the clinician has reviewed it
        alert.ack_by, alert.ack_at = actor_id, clock.now()
        _hist(alert, "acknowledged", actor_id, "implicit on resolve")
    alert.resolution_reason = reason.strip()
    return _advance(repo, alert, actor_id, "resolved", reason.strip())


def escalate(repo: Repo, alert: m.Alert, reason: str, actor: str = "system") -> m.Alert:
    plan = repo.plan(alert.patient_id)
    backup = plan.get("alert_routing", {}).get(alert.level, {}).get("backup")
    previous = alert.assigned_to
    alert.escalated = True
    alert.escalated_to = backup
    if backup:
        alert.assigned_to = backup
    _hist(alert, "escalated", actor, reason, escalated_to=backup, previous_assignee=previous)
    repo.add(alert)
    audit.log(repo, alert.patient_id, actor, "alert.escalated",
              {"reason": reason, "escalated_to": backup, "previous_assignee": previous}, "alert", alert.id)
    for member_id in filter(None, {backup, previous}):
        notify(repo, alert.patient_id, member_id, "escalation", f"ESCALATED: {alert.title}", reason, "alert",
               alert.id, dedupe_key=f"esc:{alert.id}:{member_id}")
    return alert


def escalate_overdue(repo: Repo, now: datetime | None = None) -> list[m.Alert]:
    now = now or clock.now()
    cutoff = now - timedelta(seconds=settings.ack_timeout_s)
    out = []
    for a in repo.all(m.Alert, m.Alert.state.in_(["created", "assigned"]), m.Alert.escalated == False,  # noqa: E712
                      m.Alert.level.in_(["attention", "urgent"]), m.Alert.created_at <= cutoff):
        out.append(escalate(repo, a, f"Not acknowledged within {settings.ack_timeout_s} s", "rule:ack_timeout"))
    return out


def visible_to(repo: Repo, role: str, member_id: str | None, patient_id: str | None) -> list[m.Alert]:
    where = []
    if patient_id:
        where.append(m.Alert.patient_id == patient_id)
    alerts = repo.all(m.Alert, *where, order=m.Alert.created_at.desc())
    if role == "clinician":
        return alerts
    if role == "caregiver":
        plan = repo.plan(patient_id or "sarah")
        from .notifications import caregiver_allowed
        return alerts if member_id and caregiver_allowed(plan, member_id, "alerts") else []
    if role == "patient":
        return [a for a in alerts if a.level in ("urgent", "attention", "info")]
    return []


def public(alert: m.Alert, role: str = "clinician") -> dict:
    d = alert.model_dump()
    if role != "clinician":  # patients/caregivers see status, not clinical detail
        d = {k: d[k] for k in ("id", "patient_id", "level", "state", "title", "created_at", "updated_at", "escalated")}
    return d
