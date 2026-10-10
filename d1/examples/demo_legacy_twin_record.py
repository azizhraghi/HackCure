"""Build Recovery Twin snapshots for a synthetic episode and print them.

    .venv/bin/python examples/demo_legacy_twin_record.py

All values are fixtures; milestones stand in for D2's approved protocol.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from surgiguard_d1.physiology import CodeConfig, PhysiologyConfig, RecordedObservation, analyze_physiology  # noqa: E402
from surgiguard_d1.legacy.twin_record import (  # noqa: E402
    AnalysisInput, ApprovedMilestone, ContextItem, Episode, MedicationReport, MetricReference,
    ProtocolView, SymptomReport, TwinInputs, TwinStore, caregiver_view, patient_view,
    physiology_config, predict_expected,
)
from surgiguard_d1.legacy.trajectory_model import TrajectoryModel  # noqa: E402
from surgiguard_d1.patient_twin import ChronosForecaster, TrendForecaster, forecast_metric  # noqa: E402
from surgiguard_d1.physiology import build_series  # noqa: E402

MODEL_DIR = Path(__file__).resolve().parents[1] / "models" / "trajectory"
if not MODEL_DIR.exists():
    sys.exit("No trained model. Run: .venv/bin/python scripts/train_legacy_model.py --simulate 1500 --out models/trajectory")
model = TrajectoryModel.load(MODEL_DIR)

# Pretrained forecaster if it has been downloaded, otherwise the simple trend method.
CHRONOS_DIR = MODEL_DIR.parent / "chronos-bolt-tiny"
forecaster = ChronosForecaster(CHRONOS_DIR) if (CHRONOS_DIR / "model.safetensors").exists() else TrendForecaster()

T0 = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
UNITS = {"spo2": "%", "hr": "beats/min", "temperature": "Cel"}


def reading(n, minutes, metrics):
    at = T0 + timedelta(minutes=minutes)
    return RecordedObservation.model_validate({
        "event_id": f"ev_{n:03d}", "patient_id": "pt_demo_001", "episode_id": "ep_demo_001",
        "occurred_at": at, "received_at": at + timedelta(seconds=30),
        "payload": {
            "observation_id": f"obs_{n:03d}", "kind": "physiology",
            "source": {"method": "iot", "device_id": "wearable_demo_001", "reporter_id": None},
            "quality": {"status": "usable", "reasons": [], "usable_for": []},
            "metrics": [{"code": c, "value": v, "unit": UNITS[c]} for c, v in metrics.items()],
            "artifact_id": None, "assessment_id": None, "supersedes_id": None,
        },
    })


def wearable(until_minutes):
    """Readings every 15 minutes since discharge, 24 hours before the demo starts."""
    import math
    return [reading(i, m, {"spo2": 96, "hr": 96 + m / 60 + 3 * math.sin(m / 230)})
            for i, m in enumerate(range(-1440, until_minutes + 1, 15))]


def forecasts(until_minutes):
    points = list(build_series(wearable(until_minutes), physiology_config(protocol)).by_code["hr"].points)
    return forecast_metric("hr", "beats/min", points, T0 + timedelta(minutes=until_minutes + 5), forecaster)


def physiology(until_minutes):
    records = wearable(until_minutes)
    # Ranges, baselines and intervals come from the approved protocol.
    config = physiology_config(protocol)
    run = analyze_physiology(records, config, T0 + timedelta(minutes=until_minutes + 5), timedelta(hours=24))
    return AnalysisInput.from_payload(run.payload, run.input_watermark)


def symptom(n, minutes, pain, mood, **kw):
    at = T0 + timedelta(minutes=minutes)
    return SymptomReport(
        event_id=f"ev_sym_{n}", occurred_at=at, received_at=at + timedelta(seconds=5),
        report_id=f"sym_{n}", original_report_ref=f"raw_sym_{n}", mood_label=mood, pain_score=pain,
        items=kw.get("items", []), warning_answers=kw.get("answers", []),
        extraction_status=kw.get("status", "structured"), confirmed_by_patient=kw.get("confirmed", True))


def dose(n, minutes, status):
    at = T0 + timedelta(minutes=minutes)
    return MedicationReport(
        event_id=f"ev_med_{n}", occurred_at=at, received_at=at + timedelta(seconds=5),
        report_id=f"med_{n}", prescription_id="rx_demo_001", scheduled_dose_id=f"dose_{n}",
        reported_status=status, reported_taken_at=at if status == "taken" else None,
        reporter_id="pt_demo_001", symptom_report_ids=[])


episode = Episode(patient_id="pt_demo_001", episode_id="ep_demo_001",
                  surgery_at=T0 - timedelta(days=3), discharge_at=T0 - timedelta(days=1),
                  timezone="Africa/Algiers")
# What Developer 2 publishes after a clinician approves the personalised plan.
protocol = ProtocolView(
    protocol_id="protocol_demo", version="protocol_demo_v1", procedure="colectomy",
    patient_context=[
        ContextItem(code="age", label="Age", value=68, unit="a"),
        ContextItem(code="condition.diabetes", label="Diabetes", value="present"),
    ],
    metric_references={
        "hr": MetricReference(reference_id="ref_demo_hr", version="1", lower=50, upper=100,
                              baseline=70, expected_interval_minutes=30),
        "spo2": MetricReference(reference_id="ref_demo_spo2", version="1", lower=94,
                                baseline=97, expected_interval_minutes=30),
        "temperature": MetricReference(reference_id="ref_demo_temp", version="1"),
    },
    milestones=[
    ApprovedMilestone(milestone_id="ms_a", version="1", label="Fixture milestone A", expected_from_day=2, expected_to_day=4),
    ApprovedMilestone(milestone_id="ms_b", version="1", label="Fixture milestone B", expected_from_day=7, expected_to_day=14),
])


def show(s):
    print(f"\n=== version {s.snapshot_version}  reason={s.recompute_reason}  changed={s.changed_dimensions}")
    print(f"  dossier: " + ", ".join(
        i.code if i.value == "yes" else f"{i.code}={i.value:g}" if isinstance(i.value, float)
        else f"{i.code}={i.value}" for i in s.context.items))
    for d in s.dimensions:
        print(f"  {d.name:<22} {d.status:<9} latest={d.latest_observed_at:%H:%M}" if d.latest_observed_at
              else f"  {d.name:<22} {d.status:<9} latest=-")
        for m in d.metric_summaries:
            value = "" if m.value is None else f"{m.value:g}" if isinstance(m.value, float) else m.value
            extra = ""
            if m.code.endswith(".approved_reference"):
                ref = m.detail
                extra = f"range {ref['lower']}..{ref['upper']}, baseline {ref['baseline']}"
            elif m.code.endswith(".expected"):
                extra = (f"normal band {m.detail['lower']}..{m.detail['upper']} on day {m.detail['day']} "
                         f"({m.detail['data_origin']} data)")
            elif m.code.endswith(".vs_expected"):
                extra = f"({m.detail['difference_from_expected']:+g} from expected)"
            elif m.code.endswith(".vs_reference") and m.detail["change_from_baseline"] is not None:
                extra = f"(change from baseline {m.detail['change_from_baseline']:+g})"
            print(f"      [{m.basis:<20}] {m.code} = {value} {m.unit or ''} {extra}")
        for x in d.missing:
            print(f"      missing: {x}")
    for f in s.forecasts:
        if f.status == "available":
            band = f"({f.interval.lower} .. {f.interval.upper})" if f.interval else "(no band)"
            print(f"  forecast {f.target_code} in {f.horizon_hours:g} h: {f.point} {band}  [{f.method_version}]")
        else:
            print(f"  forecast {f.target_code} in {f.horizon_hours:g} h: abstained - {f.limitations[0]}")


store = TwinStore()
# The patient's medical dossier, as Developer 2 will send it (placeholder shape for now).
dossier = json.loads((Path(__file__).parent / "dossier_demo.json").read_text(encoding="utf-8"))
# The model predicts this patient's normal recovery curve from the whole dossier.
expected = predict_expected(model, dossier, ["hr", "spo2", "sbp", "dbp", "temperature"],
                            [d / 2 for d in range(0, 61)])
hr_curve = next(t for t in expected if t.metric == "hr")
print(f"model used:     {', '.join(hr_curve.used_inputs)}")
print(f"model ignored:  {', '.join(hr_curve.unused_inputs)}  (never seen in training)\n")
print("predicted normal heart rate for this patient (typical, band):")
for p in hr_curve.points[::10]:
    print(f"  day {p.day:>4.1f}: {p.median:5.1f}  ({p.lower:.1f} .. {p.upper:.1f})")

# 1. Wearable data up to two hours into the demo, nothing else yet.
show(store.update(TwinInputs(episode=episode, protocol=protocol, dossier=dossier, expected=expected,
                             forecasts=forecasts(120), analyses=[physiology(120)]),
                  T0 + timedelta(hours=2, minutes=5)))

# 2. The patient checks in and reports a dose; more wearable data arrives.
syms = [symptom(1, 30, 3, "okay", answers=[{"question_id": "q_demo_1", "answer": "no"}]),
        symptom(2, 200, 6, "unwell", items=[{"code": "dizziness", "assertion": "present"}],
                status="needs_clarification", confirmed=False)]
show(store.update(
    TwinInputs(episode=episode, protocol=protocol, dossier=dossier, expected=expected, forecasts=forecasts(240),
               analyses=[physiology(120), physiology(240)],
               symptom_reports=syms, medication_reports=[dose(1, 10, "taken"), dose(2, 190, "unsure")]),
    T0 + timedelta(hours=4, minutes=5)))

latest = store.latest("ep_demo_001")
print("\n--- patient view, 'How you feel' ---")
print(next(d for d in patient_view(latest)["dimensions"] if d["name"] == "pain_symptoms"))
print("\n--- caregiver granted only the timeline ---")
print([d["name"] for d in caregiver_view(latest, {"recovery_timeline"})["dimensions"]])
print(f"\nhistory kept: {[s.snapshot_id for s in store.history('ep_demo_001')]}")
