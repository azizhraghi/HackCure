"""SurgiGuard AI - D1-E: Rehabilitation Pose Estimation & Personalized Exercise Tracking.

Clinician-approved postoperative rehabilitation monitoring with computer vision pose estimation,
deterministic joint angle calculation, finite state machine repetition tracking with hysteresis,
incomplete repetition detection, and clinical safety guardrails.
"""

from .angles import calculate_angle_2d, calculate_angle_3d, AngleSmoother
from .evaluator import format_analysis_payload
from .models import (
    ExercisePrescription,
    PatientPersonalizedPlan,
    PatientClinicalProfile,
    PoseLandmark,
    PoseFrame,
    RepetitionRecord,
    RehabSessionResult,
)
from .prescription import build_personalized_rehab_plan
from .session import RehabSessionRunner

__all__ = [
    "calculate_angle_2d",
    "calculate_angle_3d",
    "AngleSmoother",
    "ExercisePrescription",
    "PatientPersonalizedPlan",
    "PatientClinicalProfile",
    "PoseLandmark",
    "PoseFrame",
    "RepetitionRecord",
    "RehabSessionResult",
    "build_personalized_rehab_plan",
    "RehabSessionRunner",
    "format_analysis_payload",
]
