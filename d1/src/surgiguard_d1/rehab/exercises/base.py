"""Base Exercise Tracker with Finite State Machine, Hysteresis, and Safety Checks.

Tracks repetitions, ROM excursion, hold duration, form deviations, and incomplete repetitions.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Tuple

from ..angles import AngleSmoother
from ..models import (
    ExercisePrescription,
    PoseFrame,
    RepetitionRecord,
    RehabExerciseMetrics,
)


class TrackerState(str, Enum):
    IDLE = "IDLE"
    MOVING_TO_PEAK = "MOVING_TO_PEAK"
    HOLDING_AT_PEAK = "HOLDING_AT_PEAK"
    RETURNING = "RETURNING"


class BaseExerciseTracker(ABC):
    """Abstract finite-state-machine tracker for rehabilitation exercises."""

    def __init__(self, prescription: ExercisePrescription):
        self.prescription = prescription
        self.smoother = AngleSmoother(window_size=5, alpha=0.45)
        self.state = TrackerState.IDLE

        # Repetition counters
        self.completed_reps: list[RepetitionRecord] = []
        self.incomplete_reps: list[RepetitionRecord] = []
        self.current_rep_number = 1

        # Current rep state tracking
        self.rep_start_time_ms: float = 0.0
        self.rep_start_angle: float = 0.0
        self.rep_peak_time_ms: float = 0.0
        self.rep_peak_angle: float = 0.0
        self.hold_start_time_ms: float | None = None
        self.hold_accumulated_seconds: float = 0.0
        self.rep_form_notes: list[str] = []
        self.rep_safety_alert: str | None = None

        # Frame telemetry & quality
        self.total_frames = 0
        self.usable_frames = 0
        self.low_visibility_frames = 0
        self.guardrail_warnings: list[str] = []

    @abstractmethod
    def extract_joint_angle(self, frame: PoseFrame) -> Tuple[float | None, list[str]]:
        """Extract primary joint angle and form check notes from pose landmarks.

        Returns:
            (angle_deg, form_notes): angle is None if key landmarks are not visible.
        """
        pass

    @abstractmethod
    def is_in_starting_position(self, angle: float) -> bool:
        """Check if joint is at its baseline resting angle (within hysteresis)."""
        pass

    @abstractmethod
    def has_reached_peak_target(self, angle: float) -> bool:
        """Check if joint has reached the prescribed target ROM."""
        pass

    @abstractmethod
    def is_moving_towards_peak(self, current_angle: float, previous_angle: float) -> bool:
        """Check if angle is progressing in the direction of exercise peak."""
        pass

    def check_safety_guardrails(self, angle: float) -> str | None:
        """Verify whether angle violates safety ceiling."""
        return None

    def process_frame(self, frame: PoseFrame) -> dict:
        """Process a single video pose frame and update state machine.

        Returns a dictionary with current tracking telemetry.
        """
        self.total_frames += 1
        raw_angle, form_notes = self.extract_joint_angle(frame)

        if raw_angle is None:
            self.low_visibility_frames += 1
            return {
                "frame_index": frame.frame_index,
                "timestamp_ms": frame.timestamp_ms,
                "state": self.state.value,
                "status": "low_visibility",
                "angle": None,
                "completed_reps": len(self.completed_reps),
                "incomplete_reps": len(self.incomplete_reps),
                "current_hold_sec": 0.0,
                "safety_alert": None,
            }

        self.usable_frames += 1
        smoothed_angle = self.smoother.add(raw_angle)
        ts = frame.timestamp_ms

        # Check safety guardrails
        safety_violation = self.check_safety_guardrails(smoothed_angle)
        if safety_violation and safety_violation not in self.guardrail_warnings:
            self.guardrail_warnings.append(safety_violation)

        # Update Finite State Machine first
        self._update_fsm(smoothed_angle, ts)

        # Record form notes and safety alert for the active rep
        if safety_violation:
            self.rep_safety_alert = safety_violation

        if form_notes:
            for note in form_notes:
                if note not in self.rep_form_notes:
                    self.rep_form_notes.append(note)

        return {
            "frame_index": frame.frame_index,
            "timestamp_ms": ts,
            "state": self.state.value,
            "status": "ok",
            "angle": round(smoothed_angle, 1),
            "peak_angle": round(self.rep_peak_angle, 1) if self.state != TrackerState.IDLE else None,
            "completed_reps": len(self.completed_reps),
            "incomplete_reps": len(self.incomplete_reps),
            "current_hold_sec": round(self.hold_accumulated_seconds, 2),
            "safety_alert": self.rep_safety_alert,
        }

    def _update_fsm(self, angle: float, ts_ms: float) -> None:
        """State machine transitions with hysteresis."""
        if self.state == TrackerState.IDLE:
            if not self.is_in_starting_position(angle):
                # Movement initiated
                self.state = TrackerState.MOVING_TO_PEAK
                self.rep_start_time_ms = ts_ms
                self.rep_start_angle = angle
                self.rep_peak_time_ms = ts_ms
                self.rep_peak_angle = angle
                self.hold_accumulated_seconds = 0.0
                self.hold_start_time_ms = None
                self.rep_form_notes = []
                self.rep_safety_alert = None

        elif self.state == TrackerState.MOVING_TO_PEAK:
            # Update peak if closer to peak
            if self._is_more_extreme_peak(angle, self.rep_peak_angle):
                self.rep_peak_angle = angle
                self.rep_peak_time_ms = ts_ms

            if self.has_reached_peak_target(angle):
                self.state = TrackerState.HOLDING_AT_PEAK
                self.hold_start_time_ms = ts_ms
            elif self.is_in_starting_position(angle):
                # Premature abort before reaching target! Incomplete rep
                self._record_rep(completed=False, end_angle=angle, end_time_ms=ts_ms, reason="insufficient_rom")
                self.state = TrackerState.IDLE

        elif self.state == TrackerState.HOLDING_AT_PEAK:
            # Accumulate hold time
            if self.hold_start_time_ms is not None:
                self.hold_accumulated_seconds = (ts_ms - self.hold_start_time_ms) / 1000.0

            if self._is_more_extreme_peak(angle, self.rep_peak_angle):
                self.rep_peak_angle = angle
                self.rep_peak_time_ms = ts_ms

            # Check if moving back towards start
            if not self.has_reached_peak_target(angle):
                self.state = TrackerState.RETURNING
                # Check if also already back at starting baseline (e.g. fast return)
                if self.is_in_starting_position(angle):
                    self._complete_return_cycle(angle, ts_ms)

        elif self.state == TrackerState.RETURNING:
            if self.is_in_starting_position(angle):
                self._complete_return_cycle(angle, ts_ms)
            elif self.has_reached_peak_target(angle):
                # Turned back to peak
                self.state = TrackerState.HOLDING_AT_PEAK

    def _complete_return_cycle(self, angle: float, ts_ms: float) -> None:
        """Handle completion of the return phase back to baseline."""
        target_met = self.has_reached_peak_target(self.rep_peak_angle)
        hold_met = self.hold_accumulated_seconds >= self.prescription.min_hold_duration_sec

        if target_met and hold_met:
            self._record_rep(completed=True, end_angle=angle, end_time_ms=ts_ms)
        elif not hold_met:
            self._record_rep(completed=False, end_angle=angle, end_time_ms=ts_ms, reason="insufficient_hold_time")
        else:
            self._record_rep(completed=False, end_angle=angle, end_time_ms=ts_ms, reason="insufficient_rom")

        self.state = TrackerState.IDLE

    @abstractmethod
    def _is_more_extreme_peak(self, current: float, current_peak: float) -> bool:
        pass

    def _record_rep(self, completed: bool, end_angle: float, end_time_ms: float, reason: str | None = None) -> None:
        """Create and store RepetitionRecord."""
        duration_s = max(0.1, (end_time_ms - self.rep_start_time_ms) / 1000.0)
        rom_achieved = abs(self.rep_peak_angle - self.rep_start_angle)

        form_score = 1.0
        if self.rep_form_notes:
            form_score = max(0.4, 1.0 - (len(self.rep_form_notes) * 0.20))
        if not completed:
            form_score = min(form_score, 0.7)

        record = RepetitionRecord(
            rep_number=self.current_rep_number,
            start_time_ms=self.rep_start_time_ms,
            peak_time_ms=self.rep_peak_time_ms,
            end_time_ms=end_time_ms,
            duration_seconds=round(duration_s, 2),
            start_angle_deg=round(self.rep_start_angle, 1),
            peak_angle_deg=round(self.rep_peak_angle, 1),
            end_angle_deg=round(end_angle, 1),
            rom_achieved_deg=round(rom_achieved, 1),
            hold_duration_seconds=round(self.hold_accumulated_seconds, 2),
            target_met=completed,
            completed=completed,
            incomplete_reason=reason,
            safety_violation=self.rep_safety_alert,
            form_score=round(form_score, 2),
            form_notes=list(self.rep_form_notes),
        )

        if completed:
            self.completed_reps.append(record)
        else:
            self.incomplete_reps.append(record)

        self.current_rep_number += 1

    def summarize_metrics(self) -> RehabExerciseMetrics:
        """Summarize exercise session into structured clinical metrics."""
        all_reps = self.completed_reps + self.incomplete_reps
        all_reps.sort(key=lambda r: r.rep_number)

        n_completed = len(self.completed_reps)
        n_incomplete = len(self.incomplete_reps)

        if all_reps:
            max_rom = max(r.rom_achieved_deg for r in all_reps)
            mean_rom = sum(r.rom_achieved_deg for r in all_reps) / len(all_reps)
            mean_hold = sum(r.hold_duration_seconds for r in all_reps) / len(all_reps)
            mean_form = sum(r.form_score for r in all_reps) / len(all_reps)
        else:
            max_rom = 0.0
            mean_rom = 0.0
            mean_hold = 0.0
            mean_form = 1.0

        target_met = n_completed >= self.prescription.target_reps

        quality_summary = {
            "total_frames": self.total_frames,
            "usable_frames": self.usable_frames,
            "low_visibility_frames": self.low_visibility_frames,
            "usable_ratio": round(self.usable_frames / max(1, self.total_frames), 3),
        }

        return RehabExerciseMetrics(
            exercise_id=self.prescription.exercise_id,
            exercise_name=self.prescription.name,
            target_side=self.prescription.target_side,
            target_reps=self.prescription.target_reps,
            completed_reps=n_completed,
            incomplete_reps=n_incomplete,
            target_rom_deg=self.prescription.target_rom_deg,
            max_rom_achieved_deg=round(max_rom, 1),
            mean_rom_achieved_deg=round(mean_rom, 1),
            mean_hold_duration_sec=round(mean_hold, 2),
            average_form_score=round(mean_form, 2),
            target_met=target_met,
            reps_data=all_reps,
            quality_summary=quality_summary,
            guardrail_warnings=self.guardrail_warnings,
        )
