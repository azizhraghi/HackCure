"""Bridge from D2's approved protocol to the physiology pipeline's settings."""

from datetime import timedelta
from typing import Any

from ...physiology.models import ApprovedReference, CodeConfig, PhysiologyConfig
from ..trajectory_model.dossier import flatten
from ..trajectory_model.model import ExpectedTrajectory, TrajectoryModel
from .models import ProtocolView


def physiology_config(protocol: ProtocolView, rr_enabled: bool = False) -> PhysiologyConfig:
    """Use the approved ranges, baselines and intervals; add nothing of our own."""
    return PhysiologyConfig(
        protocol_version=protocol.version,
        rr_enabled=rr_enabled,
        codes={
            code: CodeConfig(
                max_gap=(
                    timedelta(minutes=r.expected_interval_minutes)
                    if r.expected_interval_minutes is not None
                    else None
                ),
                reference=ApprovedReference(
                    reference_id=r.reference_id, version=r.version,
                    lower=r.lower, upper=r.upper, baseline=r.baseline,
                ),
            )
            for code, r in protocol.metric_references.items()
        },
    )


def dossier_from_protocol(protocol: ProtocolView) -> dict[str, Any]:
    """Fallback when D2's dossier JSON is not supplied: build one from the protocol."""
    dossier: dict[str, Any] = {}
    if protocol.procedure is not None:
        dossier["procedure"] = protocol.procedure
    for c in protocol.patient_context:
        if c.code.startswith("condition."):
            dossier[c.code] = c.value in ("present", "yes", True, 1)
        elif c.value is not None:
            dossier[c.code] = c.value
    baselines = {m: r.baseline for m, r in protocol.metric_references.items() if r.baseline is not None}
    if baselines:
        dossier["baseline"] = baselines
    return dossier


def predict_expected(
    model: TrajectoryModel, dossier: dict[str, Any], metrics: list[str], days: list[float]
) -> list[ExpectedTrajectory]:
    """Predict the patient's normal recovery curve per metric from his medical dossier."""
    profile = flatten(dossier)
    return [model.predict(profile, m, days) for m in metrics]
