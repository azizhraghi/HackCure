"""Coordinate clinician-defined follow-up, never invent an action or resolve it."""
from datetime import datetime
from .. import alerts, audit, clock, models as m
from ..db import Repo
from ..notifications import notify


def create(repo: Repo, alert_id: str, body: m.FollowupTaskIn):
    alert = alerts.get(repo, alert_id)
    alerts._clinician(repo, alert, body.actor)
    if alert.state != "action_taken":
        raise alerts.AlertError("record the clinician action before scheduling follow-up", 409)
    if body.due_at <= clock.now():
        raise alerts.AlertError("follow-up due time must be in the future", 422)
    task = repo.add(m.FollowupTask(patient_id=alert.patient_id, alert_id=alert_id, actor=body.actor,
                                 instruction=body.instruction.strip(), due_at=body.due_at,
                                 evidence_types=list(dict.fromkeys(body.evidence_types))))
    notify(repo, alert.patient_id, alert.patient_id, "next_step", "Follow-up requested by your care team",
           task.instruction, "followup", task.id, dedupe_key=f"followup:{task.id}")
    audit.log(repo, alert.patient_id, body.actor, "followup.scheduled", task.model_dump(mode="json"), "alert", alert_id)
    return task


def sweep(repo: Repo):
    updated = []
    now = clock.now()
    for task in repo.all(m.FollowupTask, m.FollowupTask.status.in_(["waiting", "overdue", "evidence_ready"])):
        alert = repo.get(m.Alert, task.alert_id)
        if not alert:
            continue
        if alert.state == "resolved":
            task.status = "completed"
        else:
            action_at = max([task.created_at, *[
                datetime.fromisoformat(h["at"]) for h in alert.history if h["event"] == "action_taken"]])
            observations = [o for o in repo.observations(task.patient_id, since=action_at, until=now)
                            if o.type in task.evidence_types and o.source in ("patient", "caregiver_on_behalf", "device")
                            and o.quality == "good" and o.received_at >= action_at]
            task.observation_ids = [o.id for o in observations]
            available = {o.type for o in observations}
            task.status = "evidence_ready" if set(task.evidence_types) <= available else "overdue" if now >= task.due_at else "waiting"
            if task.status == "overdue":
                notify(repo, task.patient_id, alert.assigned_to or task.actor, "reminder", "Follow-up evidence overdue",
                       task.instruction, "followup", task.id, dedupe_key=f"followup-overdue:{task.id}")
        repo.add(task)
        updated.append(task.id)
    return updated
