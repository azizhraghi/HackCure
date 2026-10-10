"""Inputs and outputs of the Patient Recovery Twin.

The Twin is a versioned description of what is currently known about one
episode. It is not a simulation and carries no overall recovery score.
"""

from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from ..forecast.models import Forecast
from ..physiology.models import Evidence, Quality
from ..trajectory.model import ExpectedTrajectory

# ---------------------------------------------------------------- inputs


class _Input(BaseModel):
    model_config = ConfigDict(frozen=True)


class Episode(_Input):
    patient_id: str
    episode_id: str
    surgery_at: AwareDatetime
    discharge_at: AwareDatetime | None
    timezone: str  # patient's IANA timezone, e.g. "Africa/Algiers"


class ApprovedMilestone(_Input):
    """A clinician-approved recovery expectation published by D2."""

    milestone_id: str
    version: str
    label: str
    expected_from_day: int | None = None  # postoperative days, inclusive
    expected_to_day: int | None = None


class ContextItem(_Input):
    """One fact about the patient from the clinical record, e.g. age or a condition."""

    code: str
    label: str
    value: int | float | str | None = None
    unit: str | None = None


class MetricReference(_Input):
    """What the clinician approved for one vital sign, for this patient."""

    reference_id: str
    version: str
    lower: float | None = None
    upper: float | None = None
    baseline: float | None = None  # the patient's own pre-discharge value
    expected_interval_minutes: float | None = None


class ProtocolView(_Input):
    """The parts of D2's active approved protocol the Twin reads.

    D2 personalises this from the surgical report, age, conditions and risks,
    and a clinician approves it. The Twin never derives expectations from the
    patient's background itself.
    """

    protocol_id: str
    version: str
    procedure: str | None = None
    patient_context: list[ContextItem] = []
    metric_references: dict[str, MetricReference] = {}  # keyed by metric code
    milestones: list[ApprovedMilestone] = []
    # dimension name -> id of the approved reference it is compared against
    dimension_references: dict[str, str] = {}


AnalysisType = Literal["physiology", "neurological_motor", "rehabilitation", "wound"]


class AnalysisInput(_Input):
    """An `analysis.completed` payload from any D1 analysis module."""

    analysis_id: str
    analysis_type: AnalysisType
    status: Literal["complete", "limited", "abstained"]
    observations: list[dict[str, Any]]
    quality: Quality
    evidence: list[Evidence]
    limitations: list[str]
    model_version: str | None
    created_at: AwareDatetime
    input_watermark: AwareDatetime | None = None

    @classmethod
    def from_payload(cls, payload: BaseModel, input_watermark=None) -> "AnalysisInput":
        return cls.model_validate(
            {**payload.model_dump(mode="json"), "input_watermark": input_watermark}
        )


class SymptomItem(_Input):
    code: str
    assertion: Literal["present", "absent", "uncertain"]
    onset_at: AwareDatetime | None = None
    severity: str | float | None = None
    source_span: str | None = None


class WarningAnswer(_Input):
    question_id: str
    answer: Literal["yes", "no", "unknown"]


class SymptomReport(_Input):
    """A `symptoms.structured` event from D2 (envelope times + payload)."""

    event_id: str
    occurred_at: AwareDatetime
    received_at: AwareDatetime
    report_id: str
    original_report_ref: str
    mood_label: Literal["very_good", "good", "okay", "unwell", "very_unwell"] | None
    pain_score: int | None = Field(ge=0, le=10)
    items: list[SymptomItem]
    warning_answers: list[WarningAnswer]
    extraction_status: Literal["structured", "needs_clarification", "unavailable"]
    confirmed_by_patient: bool


class MedicationReport(_Input):
    """A `medication.reported` event from D2. A report, not proof of ingestion."""

    event_id: str
    occurred_at: AwareDatetime
    received_at: AwareDatetime
    report_id: str
    prescription_id: str
    scheduled_dose_id: str | None
    reported_status: Literal["taken", "missed", "unsure"]
    reported_taken_at: AwareDatetime | None
    reporter_id: str
    symptom_report_ids: list[str]


class TwinInputs(_Input):
    episode: Episode
    protocol: ProtocolView | None = None
    # The patient's medical dossier, as the JSON Developer 2 provides.
    dossier: dict[str, Any] | None = None
    analyses: list[AnalysisInput] = []
    symptom_reports: list[SymptomReport] = []
    medication_reports: list[MedicationReport] = []
    # Normal recovery curves predicted for this patient by the trajectory model.
    expected: list[ExpectedTrajectory] = []
    # Near-term forecasts of this patient's own readings.
    forecasts: list[Forecast] = []


# --------------------------------------------------------------- outputs

# Where a value comes from. Kept on every summary so a measurement, something
# the patient said, a calculation, a model output and a clinician-approved
# expectation can never be confused in storage or on screen.
Basis = Literal[
    "observation", "reported", "derived_summary", "model_estimate",
    "approved_expectation", "clinical_record",
]

DimensionName = Literal[
    "physiological_trends",
    "motor_performance",
    "wound_visual_changes",
    "pain_symptoms",
    "medication",
    "functional_recovery",
    "recovery_timeline",
]

RecomputeReason = Literal[
    "initial", "new_input", "late_event", "correction", "protocol_change", "time_advanced"
]


class MetricSummary(BaseModel):
    code: str
    basis: Basis
    value: int | float | str | None
    unit: str | None = None
    observed_at: AwareDatetime | None = None
    reference_id: str | None = None
    detail: dict[str, Any] = {}


class Dimension(BaseModel):
    name: DimensionName
    status: Literal["observed", "limited", "no_data"]
    metric_summaries: list[MetricSummary]
    latest_observed_at: AwareDatetime | None
    reference_id: str | None
    quality: Quality
    evidence_ids: list[str]
    missing: list[str]
    limitations: list[str]


class PatientContext(BaseModel):
    """Who the patient is, as stated in the approved protocol. Background only."""

    procedure: str | None
    items: list[MetricSummary]
    evidence_ids: list[str]
    missing: list[str]


class TwinSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_id: str
    snapshot_version: int = Field(ge=1)
    patient_id: str
    episode_id: str
    as_of: AwareDatetime
    input_watermark: AwareDatetime | None
    protocol_version: str | None
    context: PatientContext
    dimensions: list[Dimension]
    expected_trajectories: list[ExpectedTrajectory]
    forecasts: list[Forecast]
    evidence: list[Evidence]
    limitations: list[str]
    # bookkeeping beyond the event contract
    pipeline_versions: dict[str, str | None]
    recompute_reason: RecomputeReason
    changed_dimensions: list[str]
    previous_snapshot_id: str | None
    content_hash: str

    def dimension(self, name: str) -> Dimension:
        return next(d for d in self.dimensions if d.name == name)

    def event_payload(self) -> dict[str, Any]:
        """The `twin.updated` payload defined in the shared contract."""
        return self.model_dump(
            mode="json",
            include={
                "snapshot_id", "snapshot_version", "as_of", "input_watermark",
                "protocol_version", "dimensions", "forecasts", "evidence", "limitations",
            },
        )
