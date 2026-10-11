"""Rehabilitation Session Runner.

Coordinates exercise execution, frame stream processing, session-level quality gating,
honest abstention for poor camera visibility, and post-session patient feedback.
"""

from datetime import datetime, timezone
import uuid

from .exercises import BaseExerciseTracker, create_exercise_tracker
from .models import (
    ExercisePrescription,
    PatientPersonalizedPlan,
    PoseFrame,
    RehabExerciseMetrics,
    RehabSessionResult,
)


class RehabSessionRunner:
    """Manages an active patient rehabilitation session."""

    def __init__(self, plan: PatientPersonalizedPlan, episode_id: str | None = None):
        self.plan = plan
        self.patient_id = plan.patient_id
        self.episode_id = episode_id or f"ep_{plan.patient_id}"
        self.session_id = f"rehab_sess_{uuid.uuid4().hex[:8]}"
        self.start_time = datetime.now(timezone.utc)

        # Map exercise_id -> Tracker instance
        self.trackers: dict[str, BaseExerciseTracker] = {
            ex.exercise_id: create_exercise_tracker(ex) for ex in plan.exercises
        }
        self.current_exercise_id: str | None = (
            plan.exercises[0].exercise_id if plan.exercises else None
        )

    def set_current_exercise(self, exercise_id: str) -> None:
        """Switch active exercise tracker."""
        if exercise_id in self.trackers:
            self.current_exercise_id = exercise_id
        else:
            raise ValueError(f"Exercise ID '{exercise_id}' not found in active plan.")

    def process_frame(self, frame: PoseFrame, exercise_id: str | None = None) -> dict:
        """Feed a video frame into the active exercise tracker."""
        ex_id = exercise_id or self.current_exercise_id
        if not ex_id or ex_id not in self.trackers:
            raise ValueError("No valid active exercise selected for frame processing.")

        tracker = self.trackers[ex_id]
        return tracker.process_frame(frame)

    def process_frame_sequence(
        self,
        frames: list[PoseFrame],
        exercise_id: str,
    ) -> RehabExerciseMetrics:
        """Convenience method to process a batch or recording of frames for one exercise."""
        self.set_current_exercise(exercise_id)
        tracker = self.trackers[exercise_id]

        for frame in frames:
            tracker.process_frame(frame)

        return tracker.summarize_metrics()

    def finalize_session(
        self,
        patient_pain_eva: int | None = None,
        patient_difficulty: str | None = None,
    ) -> RehabSessionResult:
        """Conclude session, evaluate camera quality, and compile clinical outcome.

        Respects clinical boundary: Pain is exclusively patient-reported (EVA 0-10)
        and never inferred from camera or facial appearance.
        """
        end_time = datetime.now(timezone.utc)
        exercise_results: list[RehabExerciseMetrics] = []
        quality_flags: list[str] = []
        limitations: list[str] = []

        total_session_frames = 0
        usable_session_frames = 0

        for ex_id, tracker in self.trackers.items():
            metrics = tracker.summarize_metrics()
            exercise_results.append(metrics)
            total_session_frames += metrics.quality_summary["total_frames"]
            usable_session_frames += metrics.quality_summary["usable_frames"]

            if metrics.guardrail_warnings:
                for w in metrics.guardrail_warnings:
                    if w not in limitations:
                        limitations.append(w)

        # Determine camera acquisition quality
        coverage_ratio = (
            usable_session_frames / max(1, total_session_frames)
            if total_session_frames > 0
            else 0.0
        )

        status: str = "complete"
        if total_session_frames == 0 or coverage_ratio < 0.35:
            status = "abstained"
            quality_flags.append("camera_coverage_critically_low")
            limitations.append(
                "Visibilité insuffisante des repères anatomiques pour un calcul angulaire fiable."
            )
        elif coverage_ratio < 0.70:
            status = "limited"
            quality_flags.append("camera_coverage_partially_occluded")
            limitations.append(
                "Certaines images présentaient une occlusion partielle du membre inférieur."
            )
        else:
            quality_flags.append("camera_coverage_high_quality")

        # Patient reported symptom check
        if patient_pain_eva is not None:
            if patient_pain_eva >= 6:
                limitations.append(
                    f"Douleur signalée élevée ({patient_pain_eva}/10 EVA). Nécessite surveillance clinique."
                )

        return RehabSessionResult(
            session_id=self.session_id,
            patient_id=self.patient_id,
            episode_id=self.episode_id,
            exercise_results=exercise_results,
            patient_reported_pain_eva=patient_pain_eva,
            patient_reported_difficulty=patient_difficulty,
            session_start_time=self.start_time,
            session_end_time=end_time,
            status=status,  # type: ignore[arg-type]
            quality_flags=quality_flags,
            limitations=limitations,
        )
