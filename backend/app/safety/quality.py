"""Reading quality and missing-data checks. Missing data is "unknown", never "normal"."""

from datetime import datetime, timedelta
from typing import Any

PLAUSIBLE = {"hr": (25, 230), "spo2": (50, 100), "temp": (33.0, 43.0)}


def assess(obs_type: str, value: Any, reported: str | None = None) -> str:
    """good | questionable | unusable. A device-reported quality can only make things worse."""
    order = ["good", "questionable", "unusable"]
    q = "good"
    if obs_type in PLAUSIBLE:
        v = value.get("value") if isinstance(value, dict) else value
        try:
            v = float(v)
        except (TypeError, ValueError):
            return "unusable"
        lo, hi = PLAUSIBLE[obs_type]
        if not lo <= v <= hi:
            q = "unusable"
        sig = value.get("signal_quality") if isinstance(value, dict) else None
        if sig is not None:
            sig = float(sig)
            q = max(q, "unusable" if sig < 0.3 else "questionable" if sig < 0.6 else "good", key=order.index)
    if obs_type == "bp" and isinstance(value, dict):
        s, d = value.get("systolic"), value.get("diastolic")
        if not (isinstance(s, (int, float)) and isinstance(d, (int, float)) and 50 <= s <= 260 and 30 <= d <= 160):
            q = "unusable"
    if reported in order:
        q = max(q, reported, key=order.index)
    return q


def metric_status(readings: list, now: datetime, stale_after_min: int = 240) -> dict:
    """Summarise the latest reading of a metric (readings: Observations, any order).

    status: ok | unknown (no data / stale) | unreliable (latest readings unusable)
    """
    if not readings:
        return {"status": "unknown", "reason": "no readings", "value": None, "observation_id": None}
    rs = sorted(readings, key=lambda o: o.measured_at, reverse=True)
    latest = rs[0]
    age_min = (now - latest.measured_at).total_seconds() / 60
    good = next((o for o in rs if o.quality == "good"), None)
    if age_min > stale_after_min:
        return {"status": "unknown", "reason": f"no reading for {age_min / 60:.1f} h", "value": None,
                "last_value": latest.value, "last_at": latest.measured_at.isoformat(), "observation_id": latest.id}
    if latest.quality == "unusable":
        return {"status": "unreliable", "reason": "latest reading unusable (poor signal)", "value": None,
                "last_good_value": good.value if good else None, "observation_id": latest.id,
                "at": latest.measured_at.isoformat()}
    return {"status": "ok" if latest.quality == "good" else "questionable", "value": latest.value,
            "quality": latest.quality, "observation_id": latest.id, "at": latest.measured_at.isoformat(),
            "age_min": round(age_min)}


def find_gaps(readings: list, start: datetime, end: datetime, expected_every_min: int) -> list[dict]:
    """Periods longer than 3x the expected interval without a usable reading."""
    times = sorted(o.measured_at for o in readings if o.quality != "unusable")
    limit = timedelta(minutes=expected_every_min * 3)
    gaps, prev = [], start
    for t in times + [end]:
        if t - prev > limit:
            gaps.append({"from": prev.isoformat(), "to": t.isoformat(), "hours": round((t - prev).total_seconds() / 3600, 1)})
        prev = max(prev, t)
    return gaps
