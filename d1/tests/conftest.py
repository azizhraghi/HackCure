"""Synthetic fixtures. Values demonstrate behaviour only; none is a clinical threshold."""

from datetime import datetime, timedelta, timezone

import pytest

from surgiguard_d1.physiology import RecordedObservation

T0 = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)


def make_obs(
    n: int,
    metrics: dict[str, float],
    minutes: float = 0,
    *,
    received_delay_s: float = 60,
    method: str = "iot",
    device_id: str | None = "dev_demo_001",
    quality: str = "usable",
    reasons: list[str] | None = None,
    supersedes_id: str | None = None,
    units: dict[str, str] | None = None,
) -> RecordedObservation:
    default_units = {
        "spo2": "%", "hr": "beats/min", "sbp": "mmHg", "dbp": "mmHg",
        "temperature": "Cel", "rr": "breaths/min",
    }
    occurred = T0 + timedelta(minutes=minutes)
    return RecordedObservation.model_validate(
        {
            "event_id": f"ev_{n:03d}",
            "patient_id": "pt_demo_001",
            "episode_id": "ep_demo_001",
            "occurred_at": occurred,
            "received_at": occurred + timedelta(seconds=received_delay_s),
            "payload": {
                "observation_id": f"obs_{n:03d}",
                "kind": "physiology",
                "source": {
                    "method": method,
                    "device_id": device_id,
                    "reporter_id": "pt_demo_001" if method == "manual" else None,
                },
                "quality": {"status": quality, "reasons": reasons or [], "usable_for": []},
                "metrics": [
                    {"code": c, "value": v, "unit": (units or {}).get(c, default_units.get(c, "?"))}
                    for c, v in metrics.items()
                ],
                "artifact_id": None,
                "assessment_id": None,
                "supersedes_id": supersedes_id,
            },
        }
    )


@pytest.fixture
def t0() -> datetime:
    return T0
