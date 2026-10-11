"""Database tables (SQLModel) and API / agent schemas (Pydantic).

JSON columns are replaced, never mutated in place, so SQLAlchemy notices changes.
"""

from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field as PField, NaiveDatetime
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from . import clock


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


def _json(default=dict):
    return Field(default_factory=default, sa_column=Column(JSON))


Role = Literal["patient", "caregiver", "clinician"]
ObsType = Literal["hr", "spo2", "temp", "bp", "checkin", "photo", "movement", "med_dose"]
Source = Literal["device", "patient", "caregiver_on_behalf", "ai"]
Quality = Literal["good", "questionable", "unusable"]
AlertLevel = Literal["info", "attention", "urgent"]

ALERT_STATES = ["created", "assigned", "acknowledged", "patient_contacted", "action_taken", "verified", "resolved"]


# ---------------------------------------------------------------- tables

class Patient(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    first_name: str
    age: int
    surgery: str
    surgery_date: NaiveDatetime
    discharge_date: NaiveDatetime
    allergies: list = _json(list)
    baselines: dict = _json(dict)


class CareTeamMember(SQLModel, table=True):
    id: str = Field(primary_key=True)
    patient_id: str = Field(index=True)
    name: str
    role: str  # Role
    relation: str = ""
    is_backup: bool = False


class SurveillancePlan(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("plan"), primary_key=True)
    patient_id: str = Field(index=True)
    created_at: NaiveDatetime = Field(default_factory=clock.now)  # the plan comes from the care team
    plan: dict = _json(dict)


class Observation(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("obs"), primary_key=True)
    patient_id: str = Field(index=True)
    type: str = Field(index=True)  # ObsType
    value: dict = _json(dict)
    unit: str = ""
    measured_at: NaiveDatetime = Field(default_factory=clock.now, index=True)
    received_at: NaiveDatetime = Field(default_factory=clock.now)
    source: str = "device"  # Source
    quality: str = "good"  # Quality
    simulated: bool = False


class Investigation(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("inv"), primary_key=True)
    patient_id: str = Field(index=True)
    # running | waiting_patient | finished | incomplete | aborted_urgent
    status: str = "running"
    trigger: dict = _json(dict)
    started_at: NaiveDatetime = Field(default_factory=clock.now)
    deadline: NaiveDatetime
    finished_at: NaiveDatetime | None = None
    tool_calls: int = 0
    patient_requests: int = 0
    evidence_retries: int = 0
    state: dict = _json(dict)  # {"messages": [...], "pending": {...}}
    summary: dict | None = Field(default=None, sa_column=Column(JSON))
    alert_id: str | None = None


class PatientRequest(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("req"), primary_key=True)
    patient_id: str = Field(index=True)
    investigation_id: str | None = Field(default=None, index=True)
    checkin_id: str | None = None
    kind: str  # photo | question | measurement
    prompt: str
    reason: str = ""
    options: list = _json(list)
    metric: str | None = None
    status: str = "pending"  # pending | answered | expired | cancelled
    created_at: NaiveDatetime = Field(default_factory=clock.now)
    expires_at: NaiveDatetime
    answered_at: NaiveDatetime | None = None
    answer: dict | None = Field(default=None, sa_column=Column(JSON))
    answer_observation_id: str | None = None
    tool_call_id: str | None = None


class Alert(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("alt"), primary_key=True)
    patient_id: str = Field(index=True)
    level: str  # AlertLevel
    priority: str = "normal"  # normal | urgent_review (suggested by the investigation)
    state: str = "created"
    title: str
    reason: str
    source: str  # rule | monitor | investigation | medication
    rule: str | None = None
    evidence: dict = _json(dict)  # observation ids, summary pointer
    investigation_id: str | None = None
    assigned_to: str | None = None
    ack_by: str | None = None
    ack_at: NaiveDatetime | None = None
    escalated: bool = False
    escalated_to: str | None = None
    resolution_reason: str | None = None
    created_at: NaiveDatetime = Field(default_factory=clock.now)
    updated_at: NaiveDatetime = Field(default_factory=clock.now)
    history: list = _json(list)


class PhotoCollectionSlot(SQLModel, table=True):
    """One collection per care-plan dressing window; does not change existing tables."""
    id: str = Field(primary_key=True)
    patient_id: str = Field(index=True)
    starts_at: NaiveDatetime
    ends_at: NaiveDatetime
    request_id: str | None = None
    observation_id: str | None = None


class FollowupVerification(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("ver"), primary_key=True)
    patient_id: str = Field(index=True)
    alert_id: str = Field(index=True)
    actor: str
    summary: str
    outcome: str
    observation_ids: list = _json(list)
    created_at: NaiveDatetime = Field(default_factory=clock.now)


class CaregiverTask(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("task"), primary_key=True)
    patient_id: str = Field(index=True)
    caregiver_id: str = Field(index=True)
    text: str
    category: str = "support"
    status: str = "open"  # open | done
    created_by: str  # agent name
    dedupe_key: str | None = None
    created_at: NaiveDatetime = Field(default_factory=clock.now)
    done_at: NaiveDatetime | None = None


class Notification(SQLModel, table=True):
    """A delivered message. Delivery is never an acknowledgement."""
    id: str = Field(default_factory=lambda: new_id("ntf"), primary_key=True)
    patient_id: str = Field(index=True)
    member_id: str = Field(index=True)
    kind: str  # alert | escalation | reminder | request | next_step | digest | task
    title: str
    body: str = ""
    ref_type: str | None = None
    ref_id: str | None = None
    dedupe_key: str | None = None
    created_at: NaiveDatetime = Field(default_factory=clock.now)
    read_at: NaiveDatetime | None = None


class Digest(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("dig"), primary_key=True)
    patient_id: str
    caregiver_id: str = Field(index=True)
    text: str
    task_ids: list = _json(list)
    mode: str  # llm | template
    created_at: NaiveDatetime = Field(default_factory=clock.now)


class Document(SQLModel, table=True):
    """An uploaded medical document (discharge summary, prescription...). Text is extracted by code."""
    id: str = Field(default_factory=lambda: new_id("doc"), primary_key=True)
    patient_id: str = Field(index=True)
    filename: str
    content_type: str = ""
    size: int = 0
    status: str = "ready"  # ready | unreadable
    text: str = ""
    error: str | None = None
    created_at: NaiveDatetime = Field(default_factory=clock.now)


class PlanDraft(SQLModel, table=True):
    """Care plan drafted from documents by the protocol agent; becomes active when the patient confirms it."""
    id: str = Field(default_factory=lambda: new_id("draft"), primary_key=True)
    patient_id: str = Field(index=True)
    document_ids: list = _json(list)
    status: str = "analyzing"  # analyzing | ready | failed | confirmed
    extracted: dict | None = Field(default=None, sa_column=Column(JSON))  # what the AI read (ProtocolExtraction)
    plan: dict | None = Field(default=None, sa_column=Column(JSON))  # the resulting care plan (preview)
    warnings: list = _json(list)
    mode: str = ""
    error: str | None = None
    created_at: NaiveDatetime = Field(default_factory=clock.now)
    confirmed_at: NaiveDatetime | None = None


class AuditEvent(SQLModel, table=True):
    """Append-only: rows are inserted, never updated or deleted (except on demo reset)."""
    id: int | None = Field(default=None, primary_key=True)
    patient_id: str = Field(index=True)
    actor: str  # member id or agent name (agent:investigation, rule:urgent, ...)
    kind: str
    ref_type: str | None = Field(default=None, index=True)
    ref_id: str | None = Field(default=None, index=True)
    data: dict = _json(dict)
    at: NaiveDatetime = Field(default_factory=clock.now)


# ---------------------------------------------------------------- agent / API schemas

class PatientClaim(BaseModel):
    text: str
    observation_id: str


class DeviceClaim(BaseModel):
    text: str
    observation_id: str
    quality: str = "good"


class SummaryMessages(BaseModel):
    patient: str
    caregiver: str
    clinician: str


class EvidenceSummary(BaseModel):
    """Output of the Investigation Agent (finish_investigation input == InvestigationFindings)."""
    what_changed: str
    started_at: datetime | None = None
    persistent: bool
    patient_reported: list[PatientClaim] = []
    device_measured: list[DeviceClaim] = []
    ai_interpretation: str
    missing_or_conflicting: list[str] = []
    suggested_priority: Literal["attention", "urgent_review"]
    messages: SummaryMessages


InvestigationFindings = EvidenceSummary


class ObservationIn(BaseModel):
    patient_id: str = "sarah"
    type: ObsType
    value: dict[str, Any] | float | int | str
    unit: str = ""
    measured_at: datetime | None = None
    source: Source = "device"
    quality: Quality | None = None  # computed when omitted
    simulated: bool = False


class CheckinIn(BaseModel):
    """The app's existing check-in form (0-10 sliders + chips)."""
    patient_id: str = "sarah"
    pain: int = PField(ge=0, le=10)
    fatigue: int = PField(ge=0, le=10)
    mobility: int = PField(ge=0, le=10)
    chips: list[str] = []
    comment: str | None = PField(default=None, max_length=1000)
    submitted_by: Literal["patient", "caregiver_on_behalf"] = "patient"
    # 😄 🙂 😐 😣 😫 (D2 mood codes). A mood is not an urgency level or a pain score.
    mood: Literal["very_good", "good", "okay", "unwell", "very_unwell"] | None = None
    # Daily neurological self-check: item -> "normal" | "different" | "skipped". Any "different" is a red flag.
    neuro: dict[str, Literal["normal", "different", "skipped"]] | None = None
    # Rehabilitation exercises the patient ticked as done today (D1 rehab plan exercise ids)
    rehab_done: list[str] = PField(default_factory=list, max_length=20)


class RequestAnswer(BaseModel):
    option_index: int | None = None
    text: str | None = PField(default=None, max_length=1000)
    value: float | dict[str, float] | None = None  # measurement
    photo_asset: str | None = None  # demo photo name (day3)
    photo_base64: str | None = None
    dressing_change_confirmed: bool = False


class ActorBody(BaseModel):
    actor: str
    note: str | None = None


class ResolveBody(BaseModel):
    actor: str
    reason: str = PField(min_length=3)
    verification_id: str


class VerificationIn(BaseModel):
    actor: str
    summary: str = PField(min_length=3, max_length=2000)
    outcome: Literal["resolved", "needs_review"]
    observation_ids: list[str] = PField(min_length=1, max_length=20)


class DoseIn(BaseModel):
    patient_id: str = "sarah"
    med_id: str
    scheduled_for: datetime
    status: Literal["taken", "not_taken", "postponed", "unknown"]
    actor: str = "sarah"


class ClarificationOut(BaseModel):
    """Check-in agent: one clarification question for a worsened item."""
    text: str = PField(min_length=5, max_length=200)
    options: list[str] = PField(min_length=2, max_length=5)


class DigestTaskOut(BaseModel):
    text: str = PField(min_length=3, max_length=160)
    category: str


class DigestOut(BaseModel):
    summary: str
    tasks: list[DigestTaskOut] = PField(default_factory=list, max_length=3)


class ExtractedMedication(BaseModel):
    name: str
    dose: str
    route: str = ""
    times: list[str] = []  # "HH:MM"
    times_inferred: bool = False  # True when the document gives a frequency but no clock times
    frequency_text: str = ""
    purpose: str = ""
    duration_days: int | None = None
    as_needed: bool = False
    source_quote: str = ""


class ExtractedItem(BaseModel):
    text: str
    times: list[str] = []
    source_quote: str = ""


class ExtractedAppointment(BaseModel):
    title: str
    date: str | None = None  # YYYY-MM-DD
    time: str | None = None  # HH:MM
    source_quote: str = ""


class ProtocolExtraction(BaseModel):
    """What the protocol agent must return: only what the documents say."""
    surgery: str = ""
    side: str = ""
    surgery_date: str | None = None
    discharge_date: str | None = None
    surgeon: str = ""
    allergies: list[str] = []
    medications: list[ExtractedMedication] = []
    missed_dose_instruction: str = ""
    activity_restrictions: list[ExtractedItem] = []
    rehab: list[ExtractedItem] = []
    wound_care: list[str] = []
    appointments: list[ExtractedAppointment] = []
    warning_signs: list[str] = []
    emergency_signs: list[str] = []


class PlanDraftIn(BaseModel):
    document_ids: list[str] = []  # empty = all documents of the patient
    # agent = D3 protocol agent (app/agents/protocol.py) | d2 = Developer 2 compiler (OCR fields + safety graph)
    engine: Literal["agent", "d2"] = "agent"
