"""Persisted, public workflow progress; clinical follow-up comes from the alert ledger.

LangGraph executes the investigation. The existing SQLite transaction is the durable
checkpoint so a tool effect and its continuation cannot disagree after a restart.
No model is allowed to advance clinician follow-up.
"""

from .. import audit, clock
from .. import models as m
from ..db import Repo

ENGINE = "langgraph"
VERSION = 1
LABELS = {
    "collect_context": "Collect patient context",
    "assess_evidence": "Identify missing evidence",
    "read_evidence": "Check evidence sources",
    "request_evidence": "Request permitted evidence",
    "waiting_patient": "Waiting for patient evidence",
    "validate_report": "Validate clinician report",
    "await_clinician": "Waiting for clinician review",
    "incomplete": "Incomplete evidence sent for review",
    "aborted_urgent": "Urgent alert takes precedence",
}


def mark(repo: Repo, inv: m.Investigation, stage: str) -> None:
    previous = (inv.state or {}).get("workflow", {})
    progress = {"engine": ENGINE, "version": VERSION, "stage": stage,
                "label": LABELS[stage], "updated_at": clock.now().isoformat()}
    inv.state = {**(inv.state or {}), "workflow": progress}
    repo.add(inv)
    if previous.get("stage") != stage or previous.get("engine") != ENGINE:
        audit.log(repo, inv.patient_id, "agent:investigation", "workflow.stage", progress, "investigation", inv.id)


def public(repo: Repo, inv: m.Investigation) -> dict:
    progress = dict((inv.state or {}).get("workflow") or {})
    progress.setdefault("engine", "legacy")
    progress.setdefault("stage", inv.status)
    progress.setdefault("label", inv.status.replace("_", " "))
    if inv.status in ("incomplete", "aborted_urgent"):
        progress.update(stage=inv.status, label=LABELS[inv.status])
    elif inv.status == "waiting_patient":
        progress.update(stage="waiting_patient", label=LABELS["waiting_patient"])
    alert = repo.get(m.Alert, inv.alert_id) if inv.alert_id else None
    if alert:
        labels = {"created": "Waiting for clinician review", "assigned": "Waiting for clinician review",
                  "acknowledged": "Clinician acknowledged; patient contact pending",
                  "patient_contacted": "Patient contacted; clinician action pending",
                  "action_taken": "Waiting for follow-up evidence and assessment",
                  "verified": "Follow-up verified; clinician closure pending", "resolved": "Follow-up closed"}
        progress["followup"] = {"alert_id": alert.id, "state": alert.state, "label": labels[alert.state],
                                "closed": alert.state == "resolved"}
    else:
        progress["followup"] = None
    context = (inv.state or {}).get("context") or {}
    progress["context_collected"] = bool(context)
    progress["report_ready"] = bool(inv.summary)
    progress["context_sources"] = context.get("sources", [])
    # Public actions and evidence references, never private model reasoning.
    progress["events"] = [{"at": e.at.isoformat(), "stage": e.data["stage"], "label": e.data["label"]}
                          for e in audit.trail(repo, "investigation", inv.id) if e.kind == "workflow.stage"]
    return progress


def patient_progress(repo: Repo, inv: m.Investigation) -> dict:
    """Patient-facing milestones, with no clinician report or internal tool history."""
    alert = repo.get(m.Alert, inv.alert_id) if inv.alert_id else None
    phase = ("urgent" if inv.status == "aborted_urgent" else
             "closed" if alert and alert.state == "resolved" else
             "followup" if alert else "evidence" if inv.state.get("context") else "context")
    return {"id": inv.id, "phase": phase, "context_collected": bool(inv.state.get("context")),
            "report_ready": bool(inv.summary), "report_incomplete": inv.status == "incomplete",
            "followup_state": alert.state if alert else None, "closed": bool(alert and alert.state == "resolved")}
