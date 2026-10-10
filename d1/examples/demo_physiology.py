"""Run the physiology pipeline on a small synthetic episode and print the result.

    .venv/bin/python examples/demo_physiology.py

All numbers are fixtures. The "expected interval" and reference below stand in
for what D2's approved protocol will supply; they are not clinical values.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from surgiguard_d1.physiology import (  # noqa: E402
    ApprovedReference,
    CodeConfig,
    PhysiologyConfig,
    RecordedObservation,
    analyze_physiology,
    validate_physiology,
)

T0 = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
UNITS = {"spo2": "%", "hr": "beats/min", "sbp": "mmHg", "dbp": "mmHg", "temperature": "Cel"}


def obs(n, minutes, metrics, method="iot", device="wearable_demo_001", supersedes=None, late_s=30):
    at = T0 + timedelta(minutes=minutes)
    return RecordedObservation.model_validate({
        "event_id": f"ev_{n:03d}", "patient_id": "pt_demo_001", "episode_id": "ep_demo_001",
        "occurred_at": at, "received_at": at + timedelta(seconds=late_s),
        "payload": {
            "observation_id": f"obs_{n:03d}", "kind": "physiology",
            "source": {"method": method, "device_id": device,
                       "reporter_id": "pt_demo_001" if method == "manual" else None},
            "quality": {"status": "usable", "reasons": [], "usable_for": []},
            "metrics": [{"code": c, "value": v, "unit": UNITS[c]} for c, v in metrics.items()],
            "artifact_id": None, "assessment_id": None, "supersedes_id": supersedes,
        },
    })


records = []
# Wearable SpO2/HR every 15 min for 2 h, then nothing for 3 h, then 1 more hour.
n = 0
for m in list(range(0, 121, 15)) + list(range(300, 361, 15)):
    n += 1
    records.append(obs(n, m, {"spo2": 97 - (m > 250), "hr": 72 + m / 30}))
# The sensor sends a zero while being re-attached.
records.append(obs(40, 295, {"spo2": 0, "hr": 0}))
# Two manual BP entries; the second was mistyped and then corrected.
records.append(obs(50, 10, {"sbp": 122, "dbp": 78}, method="manual", device="cuff_demo_001"))
records.append(obs(51, 240, {"sbp": 218, "dbp": 80}, method="manual", device="cuff_demo_001"))
records.append(obs(52, 240, {"sbp": 128, "dbp": 80}, method="manual", device="cuff_demo_001",
                   supersedes="obs_051", late_s=600))
# One temperature reading only.
records.append(obs(60, 20, {"temperature": 36.9}, device="thermo_demo_001"))

config = PhysiologyConfig(
    protocol_version="protocol_demo_v1",
    codes={
        "spo2": CodeConfig(max_gap=timedelta(minutes=30)),
        "hr": CodeConfig(
            max_gap=timedelta(minutes=30),
            reference=ApprovedReference("ref_demo_hr", "1", lower=50, upper=100, baseline=72),
        ),
        "sbp": CodeConfig(),
        "dbp": CodeConfig(),
        "temperature": CodeConfig(),
    },
)

for r in records:
    assert validate_physiology(r.payload, config) == []

run = analyze_physiology(records, config, as_of=T0 + timedelta(hours=6, minutes=10), window=timedelta(hours=24))
p = run.payload

print(f"analysis {p.analysis_id}  status={p.status}  quality={p.quality.status}")
print(f"reasons: {p.quality.reasons}\n")
for f in p.observations:
    print(f"[{f.code}] {f.state}  samples={f.sample_count} usable={f.usable_count} excluded={f.excluded}")
    if f.latest:
        print(f"    latest {f.latest.value:g} {f.unit} at {f.latest.observed_at:%H:%M}")
    if f.median is not None:
        slope = f"{f.slope.value:+.2f} {f.slope.unit}" if f.slope else "n/a"
        print(f"    median {f.median:g}  MAD {f.mad:g}  slope {slope}")
    if f.coverage is not None:
        print(f"    coverage of window {f.coverage:.0%}")
    for g in f.gaps:
        print(f"    gap {g.start:%H:%M} -> {g.end:%H:%M} ({g.seconds / 60:.0f} min)")
    if f.reference:
        r = f.reference
        print(f"    vs {r.reference_id}: latest {r.latest}, median {r.window_median}, "
              f"change from baseline {r.change_from_baseline:+.1f}")
    for lim in f.limitations:
        print(f"    ! {lim}")
print(f"\ncorrections kept: {[(c.superseded_id, '->', c.superseding_id) for c in run.series.corrections]}")
print(f"evidence items: {len(p.evidence)}   input watermark: {run.input_watermark:%Y-%m-%d %H:%M:%S}Z")
