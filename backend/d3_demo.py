"""Developer 3 vertical slice using synthetic, non-clinical demo rules.

The /v1/demo routes have no authentication or real notification transport. They must
not be used with real patient data or presented as a clinically approved service.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, TypedDict
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field


router = APIRouter(prefix="/v1/demo", tags=["Developer 3 demo"])

# These codes are deliberately synthetic. A real deployment needs a versioned,
# clinician-approved policy and approved patient wording from Developer 2.
POLICY_VERSION = "synthetic-demo-v1"
RULES = {
    "demo_urgent_warning": ("emergency", "synthetic_urgent_instruction"),
    "demo_review_signal": ("clinical_review", "synthetic_review_instruction"),
}
INSTRUCTIONS = {
    "synthetic_urgent_instruction": "DEMO ONLY: An urgent warning was recorded. Follow the instructions in your actual care plan.",
    "synthetic_review_instruction": "DEMO ONLY: This report needs review by the care team.",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db_path() -> Path:
    return Path(os.getenv("SURGIGUARD_DB_PATH", Path(__file__).parent / "data" / "d3-demo.sqlite3"))


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, episode_id TEXT NOT NULL,
            body_hash TEXT NOT NULL, body_json TEXT NOT NULL, response_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS decisions (
            decision_id TEXT PRIMARY KEY, event_id TEXT NOT NULL UNIQUE,
            outcome TEXT NOT NULL, policy_version TEXT NOT NULL, detail_json TEXT NOT NULL,
            FOREIGN KEY(event_id) REFERENCES events(event_id)
        );
        CREATE TABLE IF NOT EXISTS alerts (
            alert_id TEXT PRIMARY KEY, episode_id TEXT NOT NULL,
            decision_id TEXT NOT NULL UNIQUE, category TEXT NOT NULL, created_at TEXT NOT NULL,
            FOREIGN KEY(decision_id) REFERENCES decisions(decision_id)
        );
        CREATE TABLE IF NOT EXISTS followups (
            followup_id TEXT PRIMARY KEY, alert_id TEXT NOT NULL UNIQUE,
            stage TEXT NOT NULL, version INTEGER NOT NULL, acknowledged_by TEXT,
            clinician_decision_id TEXT, verification_evidence_id TEXT, updated_at TEXT NOT NULL,
            FOREIGN KEY(alert_id) REFERENCES alerts(alert_id)
        );
        CREATE TABLE IF NOT EXISTS outbox (
            outbox_id TEXT PRIMARY KEY, alert_id TEXT NOT NULL, recipient_role TEXT NOT NULL,
            status TEXT NOT NULL, instruction_template_id TEXT, created_at TEXT NOT NULL,
            FOREIGN KEY(alert_id) REFERENCES alerts(alert_id)
        );
        CREATE TABLE IF NOT EXISTS followup_actions (
            action_id TEXT PRIMARY KEY, followup_id TEXT NOT NULL,
            action_type TEXT NOT NULL, actor_id TEXT NOT NULL,
            detail_json TEXT NOT NULL, created_at TEXT NOT NULL,
            FOREIGN KEY(followup_id) REFERENCES followups(followup_id)
        );
        CREATE TABLE IF NOT EXISTS investigations (
            investigation_id TEXT PRIMARY KEY, event_id TEXT NOT NULL UNIQUE,
            report_json TEXT NOT NULL, created_at TEXT NOT NULL,
            FOREIGN KEY(event_id) REFERENCES events(event_id)
        );
    """)
    return db


class EventIn(BaseModel):
    event_id: str = Field(min_length=1)
    patient_id: str = Field(min_length=1)
    kind: Literal["structured_warning", "measurement", "wound_observation"]
    code: str = Field(min_length=1)
    answer: Literal["yes", "no", "unknown"] | None = None
    value: str | None = None
    quality: Literal["usable", "limited", "unusable", "unknown"] = "unknown"
    source: Literal["patient", "caregiver", "device", "analysis"]
    occurred_at: datetime


class VersionedAction(BaseModel):
    actor_id: str = Field(min_length=1)
    expected_version: int = Field(ge=1)


class ClinicalDecisionIn(VersionedAction):
    note: str = Field(min_length=1, max_length=1000)


class VerificationIn(VersionedAction):
    evidence_id: str = Field(min_length=1)


def _evaluate(event: EventIn) -> dict:
    outcome = "no_match"
    rule_ids: list[str] = []
    instruction_id = None
    limitations = ["Synthetic demo policy; not approved for clinical use."]
    if event.kind == "structured_warning":
        if event.answer is None or event.answer == "unknown":
            outcome = "indeterminate"
            limitations.append("The structured answer is missing or unknown.")
        elif event.answer == "yes" and event.code in RULES:
            outcome, instruction_id = RULES[event.code]
            rule_ids = [event.code]
    elif event.quality in ("unusable", "unknown"):
        outcome = "indeterminate"
        limitations.append("Observation quality cannot support an interpretation.")
    return {
        "decision_id": f"sd_{uuid4().hex}",
        "input_event_ids": [event.event_id],
        "policy_version": POLICY_VERSION,
        "outcome": outcome,
        "matched_rule_ids": rule_ids,
        "instruction_template_id": instruction_id,
        "instruction": INSTRUCTIONS.get(instruction_id),
        "limitations": limitations,
        "evaluated_at": _now(),
        "demo_only": True,
    }


@router.post("/episodes/{episode_id}/events", status_code=201)
def record_event(episode_id: str, event: EventIn):
    if event.kind == "structured_warning" and event.answer is None:
        raise HTTPException(422, "Structured warning requires an answer, including 'unknown'.")
    body = event.model_dump(mode="json")
    body_json = json.dumps(body, sort_keys=True, separators=(",", ":"))
    body_hash = hashlib.sha256(body_json.encode()).hexdigest()
    db = _connect()
    try:
        db.execute("BEGIN IMMEDIATE")
        old = db.execute("SELECT * FROM events WHERE event_id = ?", (event.event_id,)).fetchone()
        if old:
            if old["body_hash"] != body_hash or old["episode_id"] != episode_id:
                raise HTTPException(409, "Event ID already used for different content.")
            db.rollback()
            return json.loads(old["response_json"])

        decision = _evaluate(event)
        alert_id = None
        followup_id = None
        if decision["outcome"] in ("emergency", "clinical_review"):
            alert_id = f"al_{uuid4().hex}"
            followup_id = f"fu_{uuid4().hex}"
        response = {
            "event_id": event.event_id,
            "episode_id": episode_id,
            "safety_decision": decision,
            "alert_id": alert_id,
            "followup_id": followup_id,
            "investigation_status": "not_started",
            "demo_only": True,
        }
        db.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?)",
            (event.event_id, event.patient_id, episode_id, body_hash, body_json, json.dumps(response)),
        )
        db.execute(
            "INSERT INTO decisions VALUES (?, ?, ?, ?, ?)",
            (decision["decision_id"], event.event_id, decision["outcome"], POLICY_VERSION, json.dumps(decision)),
        )
        if alert_id:
            now = _now()
            db.execute(
                "INSERT INTO alerts VALUES (?, ?, ?, ?, ?)",
                (alert_id, episode_id, decision["decision_id"], decision["outcome"], now),
            )
            db.execute(
                "INSERT INTO followups VALUES (?, ?, 'open', 1, NULL, NULL, NULL, ?)",
                (followup_id, alert_id, now),
            )
            for role in ("patient", "clinician"):
                db.execute(
                    "INSERT INTO outbox VALUES (?, ?, ?, 'queued', ?, ?)",
                    (f"ob_{uuid4().hex}", alert_id, role, decision["instruction_template_id"], now),
                )
        db.commit()
        return response
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


class InvestigationState(TypedDict, total=False):
    event: dict
    decision: dict
    evidence: list[dict]
    missing_data: list[str]
    findings: list[dict]
    report: dict


def _collect(state: InvestigationState) -> InvestigationState:
    event = state["event"]
    evidence = [
        {"evidence_id": f"ev_{event['event_id']}", "kind": event["kind"],
         "source": event["source"], "code": event["code"],
         "observed_at": event["occurred_at"], "quality": event["quality"]},
        {"evidence_id": f"ev_{state['decision']['decision_id']}", "kind": "safety_decision",
         "policy_version": POLICY_VERSION, "outcome": state["decision"]["outcome"]},
    ]
    missing = ["D1 analysis and D2 approved protocol are not connected in this demo slice."]
    if event["quality"] != "usable":
        missing.append(f"Observation quality is {event['quality']}.")
    return {"evidence": evidence, "missing_data": missing}


def _synthesize(state: InvestigationState) -> InvestigationState:
    event = state["event"]
    observation = "A structured answer was recorded" if event["kind"] == "structured_warning" else "An observation was recorded"
    finding = {
        "statement": f"{observation} with code '{event['code']}'.",
        "evidence_ids": [state["evidence"][0]["evidence_id"]],
        "limitations": ["This is a synthetic event, not a clinical interpretation."],
    }
    return {"findings": [finding]}


def _validate(state: InvestigationState) -> InvestigationState:
    ids = {item["evidence_id"] for item in state["evidence"]}
    if any(not set(f["evidence_ids"]).issubset(ids) for f in state["findings"]):
        raise ValueError("Investigation finding has an unknown evidence reference")
    report = {
        "state": "partial" if state["missing_data"] else "complete",
        "domains": ["synthetic_demo"],
        "findings": state["findings"],
        "evidence": state["evidence"],
        "missing_data": state["missing_data"],
        "conflicts": [],
        "uncertainty": ["No clinical conclusion or risk score is produced."],
        "safety_decision_ids": [state["decision"]["decision_id"]],
        "model_version": None,
        "demo_only": True,
    }
    return {"report": report}


builder = StateGraph(InvestigationState)
builder.add_node("collect_evidence", _collect)
builder.add_node("synthesize", _synthesize)
builder.add_node("validate", _validate)
builder.add_edge(START, "collect_evidence")
builder.add_edge("collect_evidence", "synthesize")
builder.add_edge("synthesize", "validate")
builder.add_edge("validate", END)
investigation_graph = builder.compile()


@router.post("/episodes/{episode_id}/investigations", status_code=201)
def investigate(episode_id: str, event_id: str):
    db = _connect()
    try:
        event_row = db.execute(
            "SELECT * FROM events WHERE event_id = ? AND episode_id = ?", (event_id, episode_id)
        ).fetchone()
        if not event_row:
            raise HTTPException(404, "Demo event not found.")
        old = db.execute("SELECT * FROM investigations WHERE event_id = ?", (event_id,)).fetchone()
        if old:
            return json.loads(old["report_json"])
        decision_row = db.execute("SELECT detail_json FROM decisions WHERE event_id = ?", (event_id,)).fetchone()
        state = investigation_graph.invoke({
            "event": json.loads(event_row["body_json"]),
            "decision": json.loads(decision_row["detail_json"]),
        })
        result = {"investigation_id": f"in_{uuid4().hex}", "event_id": event_id,
                  "episode_id": episode_id, **state["report"]}
        db.execute(
            "INSERT INTO investigations VALUES (?, ?, ?, ?)",
            (result["investigation_id"], event_id, json.dumps(result), _now()),
        )
        db.commit()
        return result
    finally:
        db.close()


def _followup(db: sqlite3.Connection, followup_id: str) -> sqlite3.Row:
    row = db.execute("SELECT * FROM followups WHERE followup_id = ?", (followup_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Demo follow-up not found.")
    return row


def _check_version(row: sqlite3.Row, expected: int) -> None:
    if row["version"] != expected:
        raise HTTPException(409, "Stale follow-up version.")


def _followup_view(row: sqlite3.Row) -> dict:
    return {**dict(row), "demo_only": True}


def _add_action(db: sqlite3.Connection, followup_id: str, action_type: str,
                actor_id: str, detail: dict) -> None:
    db.execute(
        "INSERT INTO followup_actions VALUES (?, ?, ?, ?, ?, ?)",
        (f"fa_{uuid4().hex}", followup_id, action_type, actor_id, json.dumps(detail), _now()),
    )


@router.get("/followups/{followup_id}")
def get_followup(followup_id: str):
    db = _connect()
    try:
        row = _followup(db, followup_id)
        actions = db.execute(
            "SELECT * FROM followup_actions WHERE followup_id = ? ORDER BY created_at",
            (followup_id,),
        ).fetchall()
        return {**_followup_view(row), "actions": [
            {**dict(action), "detail": json.loads(action["detail_json"])} for action in actions
        ]}
    finally:
        db.close()


@router.get("/episodes/{episode_id}/alerts")
def list_alerts(episode_id: str):
    db = _connect()
    try:
        rows = db.execute("""
            SELECT a.*, f.followup_id, f.stage, f.version, f.acknowledged_by,
                   f.clinician_decision_id, f.verification_evidence_id
            FROM alerts a JOIN followups f ON f.alert_id = a.alert_id
            WHERE a.episode_id = ? ORDER BY a.created_at
        """, (episode_id,)).fetchall()
        return {"alerts": [dict(row) for row in rows], "demo_only": True}
    finally:
        db.close()


@router.get("/episodes/{episode_id}/outbox")
def list_outbox(episode_id: str):
    db = _connect()
    try:
        rows = db.execute("""
            SELECT o.* FROM outbox o JOIN alerts a ON a.alert_id = o.alert_id
            WHERE a.episode_id = ? ORDER BY o.created_at
        """, (episode_id,)).fetchall()
        return {"delivery_intents": [dict(row) for row in rows],
                "note": "Queued intents only; no notification provider is connected.", "demo_only": True}
    finally:
        db.close()


@router.post("/followups/{followup_id}/acknowledgements")
def acknowledge(followup_id: str, action: VersionedAction):
    db = _connect()
    try:
        db.execute("BEGIN IMMEDIATE")
        row = _followup(db, followup_id)
        _check_version(row, action.expected_version)
        if row["stage"] != "open":
            raise HTTPException(409, "Follow-up is not open for acknowledgement.")
        db.execute("""
            UPDATE followups SET stage = 'acknowledged', version = version + 1,
                acknowledged_by = ?, updated_at = ? WHERE followup_id = ?
        """, (action.actor_id, _now(), followup_id))
        _add_action(db, followup_id, "acknowledged", action.actor_id, {})
        db.commit()
        return _followup_view(_followup(db, followup_id))
    finally:
        db.close()


@router.post("/followups/{followup_id}/clinical-decisions")
def record_clinical_decision(followup_id: str, action: ClinicalDecisionIn):
    db = _connect()
    try:
        db.execute("BEGIN IMMEDIATE")
        row = _followup(db, followup_id)
        _check_version(row, action.expected_version)
        if row["stage"] not in ("open", "acknowledged"):
            raise HTTPException(409, "Clinical decision cannot be recorded at this stage.")
        decision_id = f"cd_{uuid4().hex}"
        db.execute("""
            UPDATE followups SET stage = 'action_recorded', version = version + 1,
                clinician_decision_id = ?, updated_at = ? WHERE followup_id = ?
        """, (decision_id, _now(), followup_id))
        _add_action(db, followup_id, "clinical_decision", action.actor_id,
                    {"decision_id": decision_id, "note": action.note})
        db.commit()
        return {**_followup_view(_followup(db, followup_id)),
                "decision_note": action.note,
                "note": "Demo actor identity is unverified; clinical decisions require real authorization."}
    finally:
        db.close()


@router.post("/followups/{followup_id}/verifications")
def verify(followup_id: str, action: VerificationIn):
    db = _connect()
    try:
        db.execute("BEGIN IMMEDIATE")
        row = _followup(db, followup_id)
        _check_version(row, action.expected_version)
        if row["stage"] != "action_recorded" or not row["clinician_decision_id"]:
            raise HTTPException(409, "A recorded clinical decision is required before closure.")
        db.execute("""
            UPDATE followups SET stage = 'closed', version = version + 1,
                verification_evidence_id = ?, updated_at = ? WHERE followup_id = ?
        """, (action.evidence_id, _now(), followup_id))
        _add_action(db, followup_id, "verified", action.actor_id,
                    {"evidence_id": action.evidence_id})
        db.commit()
        return _followup_view(_followup(db, followup_id))
    finally:
        db.close()
