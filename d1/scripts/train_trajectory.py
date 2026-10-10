"""Train the normal-recovery-trajectory model and report how it does on unseen patients.

From the built-in simulated cohort:
    .venv/bin/python scripts/train_trajectory.py --simulate 1500 --out models/trajectory

From a file of past patients (real, or real mixed with simulated):
    .venv/bin/python scripts/train_trajectory.py --jsonl patients.jsonl --origin real --out models/trajectory

File format: one patient per line,
    {"patient_id": "...", "dossier": { the full medical dossier },
     "measurements": [{"metric": "hr", "day": 3.2, "value": 81}, ...]}
Metrics use the platform codes (spo2, hr, sbp, dbp, temperature); day is days since surgery.
Every dossier field that enough patients have is used automatically.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from surgiguard_d1.trajectory import FeatureSpec, TrajectoryModel, evaluate, load_jsonl, split_by_patient  # noqa: E402
from surgiguard_d1.trajectory.simulate import simulate_cohort  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
source = parser.add_mutually_exclusive_group(required=True)
source.add_argument("--jsonl")
source.add_argument("--simulate", type=int, metavar="N_PATIENTS")
parser.add_argument("--origin", choices=["real", "simulated", "mixed"])
parser.add_argument("--out", required=True)
parser.add_argument("--min-patients", type=int, default=30)
args = parser.parse_args()

if args.simulate:
    rows, origin = simulate_cohort(args.simulate, seed=0), "simulated"
else:
    if not args.origin:
        parser.error("--origin is required with --jsonl")
    rows, origin = load_jsonl(args.jsonl), args.origin

spec = FeatureSpec.infer(rows)
train, test = split_by_patient(rows, test_fraction=0.2, seed=0)
print(f"{len(rows)} rows, {len({r.patient_id for r in rows})} patients "
      f"({len({r.patient_id for r in test})} held out), origin={origin}")
print("dossier fields used:")
for group in ("numeric", "optional_numeric", "categorical", "optional_categorical", "flags"):
    print(f"  {group:<21}{', '.join(getattr(spec, group)) or '-'}")

check = TrajectoryModel(spec, origin).fit(train, args.min_patients)
print(f"\n{'metric':<13}{'n':>7}{'refused':>9}{'error':>8}{'baseline':>10}{'in band':>9}{'band width':>12}")
for metric, r in evaluate(check, train, test).items():
    if r["n"]:
        print(f"{metric:<13}{r['n']:>7}{r['abstained']:>9}{r['mae']:>8.2f}{r['baseline_mae']:>10.2f}"
              f"{r['band_coverage']:>9.0%}{r['band_width']:>12.2f}")
    else:
        print(f"{metric:<13}{0:>7}{r['abstained']:>9}   (no model: too few patients)")
print("\nerror    = average miss of the predicted typical value, on held-out patients"
      "\nbaseline = same for a prediction that ignores the patient's dossier"
      "\nin band  = share of real values inside the predicted band (target about 80%)")

TrajectoryModel(spec, origin).fit(rows, args.min_patients).save(args.out)
print(f"\nsaved model trained on all patients to {args.out}/")
