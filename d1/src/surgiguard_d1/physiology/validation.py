"""Domain validation for physiology observations (the 422 checks).

Rejects only what is malformed or physically impossible. Unusual but possible
values are accepted and flagged later, so the safety lane always sees them.
"""

from .codes import BP_CODES, CONVERSIONS, canonical_unit
from .models import FieldError, Metric, ObservationPayload, PhysiologyConfig, UnitProvenance


def normalize_units(
    payload: ObservationPayload,
) -> tuple[ObservationPayload, list[UnitProvenance]]:
    """Convert known non-canonical units, returning what the originals were."""
    metrics: list[Metric] = []
    provenance: list[UnitProvenance] = []
    for m in payload.metrics:
        convert = CONVERSIONS.get((m.code, m.unit))
        if convert is None:
            metrics.append(m)
            continue
        target = canonical_unit(m.code, rr_enabled=True)
        metrics.append(Metric(code=m.code, value=convert(m.value), unit=target))
        provenance.append(
            UnitProvenance(code=m.code, original_value=m.value, original_unit=m.unit)
        )
    return payload.model_copy(update={"metrics": metrics}), provenance


def validate_physiology(
    payload: ObservationPayload, config: PhysiologyConfig
) -> list[FieldError]:
    """Return field errors; an empty list means the observation is accepted."""
    errors: list[FieldError] = []

    def err(field: str, code: str, message: str) -> None:
        errors.append(FieldError(field=field, code=code, message=message))

    if payload.kind != "physiology":
        err("kind", "wrong_kind", "not a physiology observation")
        return errors
    if not payload.metrics:
        err("metrics", "empty", "a physiology observation needs at least one metric")

    codes = [m.code for m in payload.metrics]
    for code in sorted({c for c in codes if codes.count(c) > 1}):
        err("metrics", "duplicate_code", f"'{code}' appears more than once")

    for i, m in enumerate(payload.metrics):
        expected = canonical_unit(m.code, config.rr_enabled)
        if expected is None:
            err(f"metrics[{i}].code", "unsupported_code", f"'{m.code}' is not accepted")
        elif m.unit != expected:
            err(f"metrics[{i}].unit", "wrong_unit", f"'{m.code}' must be in {expected}")
        elif m.value < 0:
            err(f"metrics[{i}].value", "negative", "value cannot be negative")
        elif m.code == "spo2" and m.value > 100:
            err(f"metrics[{i}].value", "over_100_percent", "SpO2 is a percentage")

    # One BP measurement carries both pressures and is always entered manually;
    # a camera or the wearable never estimates BP.
    present = BP_CODES & set(codes)
    if present and present != BP_CODES:
        err("metrics", "unpaired_bp", "sbp and dbp must come from one measurement")
    if present and payload.source.method != "manual":
        err("source.method", "bp_not_manual", "blood pressure must be a manual entry")

    return errors
