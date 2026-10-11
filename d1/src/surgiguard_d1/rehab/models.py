"""Data contracts and schemas for SurgiGuard Rehabilitation Pose Estimation.

Covers MediaPipe landmark representations, personalized exercise prescriptions,
stateful repetition metrics, patient clinical profiles, and standardized session results.
"""

from datetime import datetime, timezone
from enum import IntEnum
from typing import Any, Literal
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class LandmarkIndex(IntEnum):
    """MediaPipe Pose 33 key landmark indices used for orthopedic rehabilitation."""

    NOSE = 0
    LEFT_EYE_INNER = 1
    LEFT_EYE = 2
    LEFT_EYE_OUTER = 3
    RIGHT_EYE_INNER = 4
    RIGHT_EYE = 5
    RIGHT_EYE_OUTER = 6
    LEFT_EAR = 7
    RIGHT_EAR = 8
    MOUTH_LEFT = 9
    MOUTH_RIGHT = 10
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_PINKY = 17
    RIGHT_PINKY = 18
    LEFT_INDEX = 19
    RIGHT_INDEX = 20
    LEFT_THUMB = 21
    RIGHT_THUMB = 22
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28
    LEFT_HEEL = 29
    RIGHT_HEEL = 30
    LEFT_FOOT_INDEX = 31
    RIGHT_FOOT_INDEX = 32


class PoseLandmark(BaseModel):
    """Normalized 3D pose landmark with visibility confidence."""

    model_config = ConfigDict(frozen=True)

    x: float
    y: float
    z: float = 0.0
    visibility: float = 1.0
    presence: float = 1.0


class PoseFrame(BaseModel):
    """Single camera frame containing extracted pose landmarks."""

    model_config = ConfigDict(frozen=True)

    frame_index: int
    timestamp_ms: float
    landmarks: dict[int, PoseLandmark]
    is_usable: bool = True
    quality_note: str | None = None


class RepetitionRecord(BaseModel):
    """Metrics recorded for an individual exercise repetition."""

    rep_number: int
    start_time_ms: float
    peak_time_ms: float
    end_time_ms: float
    duration_seconds: float
    start_angle_deg: float
    peak_angle_deg: float
    end_angle_deg: float
    rom_achieved_deg: float
    hold_duration_seconds: float
    target_met: bool
    completed: bool
    incomplete_reason: str | None = None
    safety_violation: str | None = None
    form_score: float = Field(ge=0.0, le=1.0, default=1.0)
    form_notes: list[str] = Field(default_factory=list)


class ExercisePrescription(BaseModel):
    """Clinician-approved prescription for a specific rehabilitation exercise."""

    exercise_id: str
    name: str
    category: Literal[
        "knee_flexion",
        "straight_leg_raise",
        "ankle_pumps",
        "hip_abduction",
        "seated_knee_extension",
    ]
    target_side: Literal["left", "right", "bilateral"]
    target_reps: int = 10
    target_sets: int = 2
    target_rom_deg: float
    min_start_angle_deg: float
    max_safety_angle_deg: float | None = None
    min_hold_duration_sec: float = 1.5
    allowed_angle_slack_deg: float = 5.0
    cadence_target_bpm: float = 12.0
    clinical_rationale: str = ""
    precautions: list[str] = Field(default_factory=list)
    forbidden_movements: list[str] = Field(default_factory=list)


class PatientClinicalProfile(BaseModel):
    """Patient medical file facts used to personalize rehabilitation plans."""

    patient_id: str
    patient_name: str | None = None
    age: int
    sex: Literal["M", "F", "other"]
    surgery_type: str  # e.g., "PTG droite", "PTG gauche", "PTH droite", "LCA"
    affected_side: Literal["left", "right", "bilateral"]
    surgery_date: str  # ISO string or YYYY-MM-DD
    postop_day: int
    bmi: float | None = None
    comorbidities: list[str] = Field(default_factory=list)
    mobility_level: Literal["independent", "crutches", "walker", "bedrest"] = "crutches"
    clinician_restrictions: list[str] = Field(default_factory=list)
    doctor_notes: str | None = None


class PatientPersonalizedPlan(BaseModel):
    """Full personalized rehabilitation protocol approved for a specific patient."""

    plan_id: str
    patient_id: str
    surgery_type: str
    affected_side: Literal["left", "right", "bilateral"]
    postop_phase: str
    postop_day: int
    daily_sessions: int = 2
    exercises: list[ExercisePrescription]
    general_guardrails: list[str] = Field(default_factory=list)
    approved_by: str = "Clinician Protocol Team"
    approval_status: Literal["approved", "draft", "modified_by_clinician"] = "approved"
    created_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class RehabExerciseMetrics(BaseModel):
    """Aggregated session metrics for a single exercise."""

    exercise_id: str
    exercise_name: str
    target_side: str
    target_reps: int
    completed_reps: int
    incomplete_reps: int
    target_rom_deg: float
    max_rom_achieved_deg: float
    mean_rom_achieved_deg: float
    mean_hold_duration_sec: float
    average_form_score: float
    target_met: bool
    reps_data: list[RepetitionRecord]
    quality_summary: dict[str, Any]
    guardrail_warnings: list[str] = Field(default_factory=list)


class RehabSessionResult(BaseModel):
    """Overall outcome of a patient rehabilitation session."""

    session_id: str
    patient_id: str
    episode_id: str
    exercise_results: list[RehabExerciseMetrics]
    patient_reported_pain_eva: int | None = None  # 0 - 10 EVA scale
    patient_reported_difficulty: str | None = None
    session_start_time: AwareDatetime
    session_end_time: AwareDatetime
    status: Literal["complete", "limited", "abstained"]
    quality_flags: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
