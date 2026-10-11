"""Factory for instantiating exercise trackers from prescriptions."""

from ..models import ExercisePrescription
from .base import BaseExerciseTracker
from .ankle_pumps import AnklePumpsTracker
from .knee_flexion import KneeFlexionTracker
from .leg_raise import StraightLegRaiseTracker


def create_exercise_tracker(prescription: ExercisePrescription) -> BaseExerciseTracker:
    """Instantiate the appropriate tracker based on exercise category."""
    category = prescription.category.lower()

    if category == "knee_flexion":
        return KneeFlexionTracker(prescription)
    elif category == "straight_leg_raise":
        return StraightLegRaiseTracker(prescription)
    elif category == "ankle_pumps":
        return AnklePumpsTracker(prescription)
    else:
        # Default fallback to KneeFlexionTracker
        return KneeFlexionTracker(prescription)
