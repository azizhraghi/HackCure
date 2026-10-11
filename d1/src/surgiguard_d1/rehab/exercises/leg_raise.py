"""Straight Leg Raise (SLR) Exercise Tracker.

Tracks hip elevation while strictly validating active quadriceps extension lock.
Flags quadriceps lag if the knee bends during the leg raise.
"""

from typing import Tuple

from ..angles import calculate_joint_angle_from_landmarks
from ..models import ExercisePrescription, LandmarkIndex, PoseFrame
from .base import BaseExerciseTracker


class StraightLegRaiseTracker(BaseExerciseTracker):
    """Tracker for Straight Leg Raises (Élévations jambe tendue)."""

    def __init__(self, prescription: ExercisePrescription):
        super().__init__(prescription)
        is_left = prescription.target_side.lower() == "left"
        self.shoulder_idx = LandmarkIndex.LEFT_SHOULDER if is_left else LandmarkIndex.RIGHT_SHOULDER
        self.hip_idx = LandmarkIndex.LEFT_HIP if is_left else LandmarkIndex.RIGHT_HIP
        self.knee_idx = LandmarkIndex.LEFT_KNEE if is_left else LandmarkIndex.RIGHT_KNEE
        self.ankle_idx = LandmarkIndex.LEFT_ANKLE if is_left else LandmarkIndex.RIGHT_ANKLE

    def extract_joint_angle(self, frame: PoseFrame) -> Tuple[float | None, list[str]]:
        # 1. Hip elevation angle (Shoulder - Hip - Knee)
        hip_angle, status = calculate_joint_angle_from_landmarks(
            frame.landmarks,
            self.shoulder_idx,
            self.hip_idx,
            self.knee_idx,
            min_visibility=0.60,
        )

        if hip_angle is None:
            return None, []

        form_notes: list[str] = []

        # Convert trunk-hip-knee angle into hip elevation degrees (0° = resting flat)
        elevation_angle = max(0.0, 180.0 - hip_angle)

        # 2. Vital clinical check: verify active knee extension locking
        knee_angle, knee_status = calculate_joint_angle_from_landmarks(
            frame.landmarks,
            self.hip_idx,
            self.knee_idx,
            self.ankle_idx,
            min_visibility=0.60,
        )

        if knee_angle is not None and elevation_angle > 10.0:
            # If knee bends during elevation, quad lag is present!
            if knee_angle < 162.0:
                form_notes.append("verrouillage_extension_insuffisant_quadriceps")

        return elevation_angle, form_notes

    def is_in_starting_position(self, angle: float) -> bool:
        """Leg is resting on bed or mat (elevation <= 8°)."""
        return angle <= 8.0

    def has_reached_peak_target(self, angle: float) -> bool:
        """Target elevation reached (e.g. >= 35°)."""
        threshold = self.prescription.target_rom_deg - self.prescription.allowed_angle_slack_deg
        return angle >= threshold

    def is_moving_towards_peak(self, current_angle: float, previous_angle: float) -> bool:
        return current_angle > previous_angle

    def _is_more_extreme_peak(self, current: float, current_peak: float) -> bool:
        return current > current_peak

    def check_safety_guardrails(self, angle: float) -> str | None:
        if self.prescription.max_safety_angle_deg is not None:
            if angle > (self.prescription.max_safety_angle_deg + 5.0):
                return (
                    f"Avertissement élévation : jambe levée à {round(angle, 1)}° "
                    f"(limite maximale recommandée {self.prescription.max_safety_angle_deg}° pour préserver le rachis lombaire)."
                )
        return None
