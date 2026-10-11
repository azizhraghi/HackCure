"""Ankle Pumps (Pompes de Cheville) Exercise Tracker.

Tracks active dorsiflexion and plantarflexion excursion for calf venous return
and deep vein thrombosis (DVT) prophylaxis.
"""

from typing import Tuple

from ..angles import calculate_joint_angle_from_landmarks
from ..models import ExercisePrescription, LandmarkIndex, PoseFrame
from .base import BaseExerciseTracker


class AnklePumpsTracker(BaseExerciseTracker):
    """Tracker for ankle dorsiflexion / plantarflexion pumps."""

    def __init__(self, prescription: ExercisePrescription):
        super().__init__(prescription)
        is_left = prescription.target_side.lower() == "left"
        self.knee_idx = LandmarkIndex.LEFT_KNEE if is_left else LandmarkIndex.RIGHT_KNEE
        self.ankle_idx = LandmarkIndex.LEFT_ANKLE if is_left else LandmarkIndex.RIGHT_ANKLE
        self.toe_idx = LandmarkIndex.LEFT_FOOT_INDEX if is_left else LandmarkIndex.RIGHT_FOOT_INDEX

    def extract_joint_angle(self, frame: PoseFrame) -> Tuple[float | None, list[str]]:
        angle, status = calculate_joint_angle_from_landmarks(
            frame.landmarks,
            self.knee_idx,
            self.ankle_idx,
            self.toe_idx,
            min_visibility=0.55,
        )

        if angle is None:
            return None, []

        form_notes: list[str] = []
        return angle, form_notes

    def is_in_starting_position(self, angle: float) -> bool:
        """Neutral ankle position (between 85° and 100°)."""
        return 82.0 <= angle <= 105.0

    def has_reached_peak_target(self, angle: float) -> bool:
        """Excursion into plantarflexion (>= 120°) or deep dorsiflexion (<= 75°)."""
        # An excursion of at least target_rom_deg (e.g. 25-30°) away from neutral 90°
        excursion = abs(angle - 90.0)
        return excursion >= (self.prescription.target_rom_deg - self.prescription.allowed_angle_slack_deg)

    def is_moving_towards_peak(self, current_angle: float, previous_angle: float) -> bool:
        return abs(current_angle - 90.0) > abs(previous_angle - 90.0)

    def _is_more_extreme_peak(self, current: float, current_peak: float) -> bool:
        return abs(current - 90.0) > abs(current_peak - 90.0)
