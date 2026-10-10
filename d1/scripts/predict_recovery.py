"""Predict the normal recovery trajectory from Developer 2's JSON.

    .venv/bin/python scripts/predict_recovery.py examples/d2_sample.json --days 42

Needs GROQ_API_KEY, either exported in the terminal or in a `.env` file at the
project root (one line: GROQ_API_KEY=...). GROQ_MODEL picks a different Groq model.

Prints a readable day-by-day view; --json prints the full structured result.
"""

import argparse
import json
import sys
from pathlib import Path

import os

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
if (ROOT / ".env").exists():
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"\''))

from surgiguard_d1.recovery import predict_normal_trajectory  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("d2_json")
parser.add_argument("--days", type=int, default=42)
parser.add_argument("--language", default="French")
parser.add_argument("--json", action="store_true")
args = parser.parse_args()

t = predict_normal_trajectory(
    json.loads(Path(args.d2_json).read_text()), args.days, args.language,
    progress=lambda step: print(f"  estimating {step} ...", file=sys.stderr, flush=True))
if args.json:
    print(t.model_dump_json(indent=2))
    sys.exit()

print(f"{t.surgery}\n{t.summary}\n")
c = t.typical_course
print(f"Usual course: full recovery in about {c.full_recovery_typically_weeks:g} weeks")
for ph in c.phases:
    print(f"  days {ph.from_day}-{ph.to_day}: {ph.description}")
for ls in c.lasting_symptoms:
    print(f"  lasts about {ls.typically_lasts_days:g} days: {ls.symptom}")
print("\nCheckpoints set by the model (days in between are straight lines):")
for k in t.checkpoints:
    print(f"  day {k.day:>3}: HR {k.heart_rate.low:g}-{k.heart_rate.high:g}  SpO2 {k.spo2.low:g}-{k.spo2.high:g}  "
          f"BP {k.systolic_bp.low:g}-{k.systolic_bp.high:g}/{k.diastolic_bp.low:g}-{k.diastolic_bp.high:g}  "
          f"temp {k.temperature.low:g}-{k.temperature.high:g}  pain {k.pain.low:g}-{k.pain.high:g}")
for e in t.events:
    print(f"  event on day {e.day}: {e.description}")
for note in t.adjustments:
    print(f"  corrected by our code: {note}")
print("\nPersonalised for this patient:")
for f in t.personal_factors:
    print(f"  {f.factor}: {f.effect}")
print()
for a in t.assumptions:
    print(f"  assumed: {a}")
for d in t.days:
    print(f"\nDay {d.day}")
    print(f"  heart rate {d.heart_rate.low:g}-{d.heart_rate.high:g}   SpO2 {d.spo2.low:g}-{d.spo2.high:g}   "
          f"BP {d.systolic_bp.low:g}-{d.systolic_bp.high:g}/{d.diastolic_bp.low:g}-{d.diastolic_bp.high:g}   "
          f"temp {d.temperature.low:g}-{d.temperature.high:g}   pain {d.pain.low:g}-{d.pain.high:g}/10")
    print(f"  normal: {'; '.join(d.expected_signs)}")
    print(f"  > {d.patient_message}")
print(f"\n[{t.generated_by}, {t.prompt_version}]")
