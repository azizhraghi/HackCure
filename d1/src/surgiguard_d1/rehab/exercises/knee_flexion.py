"""Knee Flexion (Heel Slides) Exercise Tracker.

Tracks knee flexion angle (Hip - Knee - Ankle), monitors ROM against clinician targets,
detects over-flexion safety violations, and verifies starting extension.
"""

from typing import Tuple

from ..angles import calculate_joint_angle_from_landmarks
from ..models import ExercisePrescription, LandmarkIndex, PoseFrame
from .base import BaseExerciseTracker


class KneeFlexionTracker(BaseExerciseTracker):
    """Tracker for Knee Flexions / Heel Slides (e.g. for Total Knee Replacement PTG)."""

    def __init__(self, prescription: ExercisePrescription):
        super().__init__(prescription)
        is_left = prescription.target_side.lower() == "left"
        self.hip_idx = LandmarkIndex.LEFT_HIP if is_left else LandmarkIndex.RIGHT_HIP
        self.knee_idx = LandmarkIndex.LEFT_KNEE if is_left else LandmarkIndex.RIGHT_KNEE
        self.ankle_idx = LandmarkIndex.LEFT_ANKLE if is_left else LandmarkIndex.RIGHT_ANKLE

    def extract_joint_angle(self, frame: PoseFrame) -> Tuple[float | None, list[str]]:
        angle, status = calculate_joint_angle_from_landmarks(
            frame.landmarks,
            self.hip_idx,
            self.knee_idx,
            self.ankle_idx,
            min_visibility=0.60,
        )

        if angle is None:
            return None, []

        form_notes: list[str] = []

        # Check alignment (detect extreme lateral deviation / valgus / varus)
        hip = frame.landmarks[self.hip_idx]
        knee = frame.landmarks[self.knee_idx]
        ankle = frame.landmarks[self.ankle_idx]

        lateral_dev = abs((knee.x - hip.x) - (ankle.x - knee.x))
        if lateral_dev > 0.18:
            form_notes.append("deviation_laterale_genou")

        return angle, form_notes

    def is_in_starting_position(self, angle: float) -> bool:
        """Starting position is near full extension (e.g. >= 155°)."""
        threshold = max(145.0, self.prescription.min_start_angle_deg - 12.0)
        return angle >= threshold

    def has_reached_peak_target(self, angle: float) -> bool:
        """Flexion target reached when knee angle bends below or equal to target ROM + slack."""
        # Note: 180° = extension, 90° = 90° flexion. Smaller angle = deeper flexion.
        threshold = self.prescription.target_rom_deg + self.prescription.allowed_angle_slack_deg
        return angle <= threshold

    def is_moving_towards_peak(self, current_angle: float, previous_angle: float) -> bool:
        # Bending the knee means decreasing angle
        return current_angle < previous_angle

    def _is_more_extreme_peak(self, current: float, current_peak: float) -> bool:
        # Deeper flexion corresponds to lower angle
        return current < current_peak

    def check_safety_guardrails(self, angle: float) -> str | None:
        """Guardrail against excessive flexion beyond prescribed safety ceiling."""
        if self.prescription.max_safety_angle_deg is not None:
            # If clinician specified max flexion (e.g. 90°), bending beyond that (< 85°) triggers warning
            if angle < (self.prescription.max_safety_angle_deg - 5.0):
                return (
                    f"Avertissement sécurité : flexion de {round(180.0 - angle)}° "
                    f"(angle du genou {round(angle, 1)}°) dépassant le plafond prescrit de "
                    f"{round(180.0 - self.prescription.max_safety_angle_deg)}° de flexion."
                )
        return None
