"""Typed inputs, configuration and outputs for the physiology pipeline.

Input models mirror ObservationV1 from the shared contract. Output models
mirror the `analysis.completed` payload.
"""

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

# ---------------------------------------------------------------- inputs


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Metric(_Strict):
    code: str
    value: float = Field(allow_inf_nan=False)
    unit: str


class Source(_Strict):
    method: Literal["iot", "manual", "smartphone_session"]
    device_id: str | None
    reporter_id: str | None


class Quality(_Strict):
    status: Literal["usable", "limited", "unusable", "unknown"]
    reasons: list[str]
    usable_for: list[str]


class ObservationPayload(_Strict):
    observation_id: str
    kind: Literal["physiology", "neurological_motor", "rehabilitation", "wound"]
    source: Source
    quality: Quality
    metrics: list[Metric]
    artifact_id: str | None
    assessment_id: str | None
    supersedes_id: str | None


class RecordedObservation(_Strict):
    """The parts of an `observation.recorded` event this pipeline needs."""

    event_id: str
    patient_id: str
    episode_id: str
    occurred_at: AwareDatetime  # when the measurement was taken
    received_at: AwareDatetime  # when the server ingested it
    payload: ObservationPayload


# --------------------------------------------------------- configuration


@dataclass(frozen=True)
class ApprovedReference:
    """A clinician-approved expectation, published by D2. Never invented here."""

    reference_id: str
    version: str
    lower: float | None = None
    upper: float | None = None
    baseline: float | None = None


@dataclass(frozen=True)
class CodeConfig:
    # Longest interval between samples that still counts as continuous
    # observation. Comes from the approved cadence; None = not configured.
    max_gap: timedelta | None = None
    # Engineering minimum for reporting dispersion and slope.
    min_samples: int = 3
    # Device/domain plausibility bounds. These prompt a re-check; they are
    # not emergency thresholds and never cause a value to be dropped.
    plausible_low: float | None = None
    plausible_high: float | None = None
    reference: ApprovedReference | None = None


@dataclass(frozen=True)
class PhysiologyConfig:
    codes: dict[str, CodeConfig] = field(default_factory=dict)
    rr_enabled: bool = False
    clock_skew_tolerance: timedelta = timedelta(minutes=5)
    protocol_version: str | None = None

    def for_code(self, code: str) -> CodeConfig:
        return self.codes.get(code, CodeConfig())


# --------------------------------------------------------------- outputs


class FieldError(BaseModel):
    field: str
    code: str
    message: str


class UnitProvenance(BaseModel):
    code: str
    original_value: float
    original_unit: str


class Evidence(BaseModel):
    evidence_id: str
    kind: Literal[
        "observation", "symptom", "medication", "analysis",
        "protocol", "reference", "clinical_decision",
    ] = "observation"
    resource_id: str
    resource_version: str
    observed_at: AwareDatetime | None
    locator: str | None


class GapOut(BaseModel):
    start: AwareDatetime
    end: AwareDatetime
    seconds: float


class LatestValue(BaseModel):
    value: float
    observed_at: AwareDatetime
    observation_id: str


class Slope(BaseModel):
    value: float
    unit: str
    method: str = "theil_sen"
    subsampled: bool = False


class ReferenceComparison(BaseModel):
    reference_id: str
    reference_version: str
    latest: Literal["below", "within", "above"] | None
    window_median: Literal["below", "within", "above"] | None
    change_from_baseline: float | None


FindingState = Literal["summarized", "insufficient_samples", "no_recent_measurement"]


class MetricFinding(BaseModel):
    code: str
    unit: str | None
    state: FindingState
    window_start: AwareDatetime
    window_end: AwareDatetime
    sample_count: int
    usable_count: int
    excluded: dict[str, int]
    flag_counts: dict[str, int]
    latest: LatestValue | None
    seconds_since_latest: float | None
    median: float | None
    mad: float | None
    slope: Slope | None
    min_samples: int
    span_seconds: float | None
    coverage: float | None
    gaps: list[GapOut]
    reference: ReferenceComparison | None
    evidence_ids: list[str]
    limitations: list[str]


class AnalysisPayload(BaseModel):
    """Payload of the `analysis.completed` event. Deliberately no diagnosis field."""

    analysis_id: str
    analysis_type: Literal["physiology"] = "physiology"
    status: Literal["complete", "limited", "abstained"]
    observations: list[MetricFinding]
    quality: Quality
    evidence: list[Evidence]
    limitations: list[str]
    model_version: str | None
    created_at: AwareDatetime
