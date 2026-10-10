"""Role projections of a snapshot.

These only shape data. Who may call which view, and which dimensions a
caregiver was granted, is decided by the identity service before this runs.
"""

from typing import Any

from .models import Dimension, TwinSnapshot

LABELS = {
    "physiological_trends": "Vital signs",
    "motor_performance": "Movement checks",
    "wound_visual_changes": "Wound photos",
    "pain_symptoms": "How you feel",
    "medication": "Medication",
    "functional_recovery": "Exercises",
    "recovery_timeline": "Recovery timeline",
}

# Patients and caregivers see what was measured, what was reported and what
# the care team expects. Statistics and model outputs stay on the clinician side.
_SIMPLE_BASES = {"observation", "reported", "approved_expectation"}
_SIMPLE_CODES = {"postoperative_day", "days_since_discharge"}


def clinician_view(snapshot: TwinSnapshot) -> dict[str, Any]:
    return snapshot.model_dump(mode="json")


def patient_view(snapshot: TwinSnapshot) -> dict[str, Any]:
    return _simple(snapshot, snapshot.dimensions)


def caregiver_view(snapshot: TwinSnapshot, granted: set[str]) -> dict[str, Any]:
    """Only the dimensions named in the caregiver's active grant."""
    return _simple(snapshot, [d for d in snapshot.dimensions if d.name in granted])


def _simple(snapshot: TwinSnapshot, dims: list[Dimension]) -> dict[str, Any]:
    return {
        "snapshot_id": snapshot.snapshot_id,
        "as_of": snapshot.as_of.isoformat(),
        "dimensions": [
            {
                "name": d.name,
                "label": LABELS[d.name],
                "status": d.status,
                "latest_observed_at": d.latest_observed_at.isoformat() if d.latest_observed_at else None,
                "items": [
                    {"code": s.code, "basis": s.basis, "value": s.value, "unit": s.unit,
                     "observed_at": s.observed_at.isoformat() if s.observed_at else None}
                    for s in d.metric_summaries
                    if (s.basis in _SIMPLE_BASES or s.code in _SIMPLE_CODES) and s.value is not None
                ],
                "missing": d.missing,
            }
            for d in dims
        ],
    }
