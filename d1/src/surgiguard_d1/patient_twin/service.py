"""Near-term forecast of one patient's own vital sign, or an abstention.

Forecasts are supplementary evidence. They never give a "safe until" time,
never change a schedule, and never delay or downgrade a safety decision.
"""

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np

from ..physiology.series import Point
from .methods import COVERAGE, Forecaster
from .models import Forecast, Interval


@dataclass(frozen=True)
class ForecastConfig:
    # Only continuously measured signals; a few manual BP entries are not a series.
    targets: tuple[str, ...] = ("hr", "spo2")
    horizons_hours: tuple[int, ...] = (6, 12, 24)
    history_hours: int = 72
    min_observed_hours: int = 12  # hours with at least one reading
    min_recent_coverage: float = 0.5  # share of the last 24 h with readings
    max_staleness_hours: float = 3.0


def to_hourly(points: list[Point], as_of: datetime, history_hours: int) -> np.ndarray:
    """Median per hour up to as_of; NaN for hours with no usable reading."""
    bins: list[list[float]] = [[] for _ in range(history_hours)]
    for p in points:
        age = (as_of - p.occurred_at).total_seconds() / 3600
        if p.usable and 0 <= age < history_hours:
            bins[history_hours - 1 - int(age)].append(p.value)
    return np.array([np.median(b) if b else np.nan for b in bins])


def forecast_metric(
    code: str, unit: str, points: list[Point], as_of: datetime,
    forecaster: Forecaster, config: ForecastConfig = ForecastConfig(),
) -> list[Forecast]:
    """One forecast per horizon. Abstains whenever the history cannot support one."""
    usable = [p for p in points if p.usable and p.occurred_at <= as_of]
    hourly = to_hourly(usable, as_of, config.history_hours)
    observed = ~np.isnan(hourly)

    reasons: list[str] = []
    if code not in config.targets:
        reasons.append(f"Forecasting is not enabled for '{code}'.")
    elif not usable:
        reasons.append("No usable readings.")
    else:
        if observed.sum() < config.min_observed_hours:
            reasons.append(
                f"Only {int(observed.sum())} hours with readings; {config.min_observed_hours} needed.")
        if observed[-24:].mean() < config.min_recent_coverage:
            reasons.append(
                f"Readings cover {observed[-24:].mean():.0%} of the last 24 hours; "
                f"{config.min_recent_coverage:.0%} needed.")
        stale = (as_of - usable[-1].occurred_at) / timedelta(hours=1)
        if stale > config.max_staleness_hours:
            reasons.append(f"Latest reading is {stale:.1f} hours old.")
        if len({(p.method, p.device_id) for p in usable[-200:]}) > 1:
            reasons.append("Measurement device changed during the history used.")

    evidence = sorted({f"evref_{p.observation_id}_{code}" for p in usable[-24:]})
    predictions = None
    if not reasons:
        predictions = forecaster.predict(hourly, max(config.horizons_hours))

    out: list[Forecast] = []
    for h in config.horizons_hours:
        fid = "fc_" + hashlib.sha256(
            repr((code, as_of.isoformat(), h, forecaster.version, evidence)).encode()
        ).hexdigest()[:16]
        if predictions is None:
            out.append(Forecast(
                forecast_id=fid, target_code=code, unit=unit, issued_at=as_of, horizon_hours=h,
                status="abstained", point=None, interval=None, method_version=None,
                evidence_ids=evidence, limitations=reasons,
            ))
            continue
        lower, point, upper = predictions[h - 1]
        has_band = not (np.isnan(lower) or np.isnan(upper))
        out.append(Forecast(
            forecast_id=fid, target_code=code, unit=unit, issued_at=as_of, horizon_hours=h,
            status="available", point=round(float(point), 2),
            interval=Interval(lower=round(float(min(lower, point)), 2),
                              upper=round(float(max(upper, point)), 2), coverage=COVERAGE)
            if has_band else None,
            method_version=forecaster.version,
            evidence_ids=evidence,
            limitations=[
                "Supplementary estimate from this patient's own recent readings; not a "
                "prediction of recovery or of safety.",
                forecaster.interval_note if has_band
                else "No band: too little history to estimate one.",
            ],
        ))
    return out
