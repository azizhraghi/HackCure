"""What the patient's home screen shows today.

    .venv/bin/python scripts/home_screen.py examples/d2_sample.json --surgery-date 2026-10-07
    .venv/bin/python scripts/home_screen.py examples/d2_sample.json --surgery-date 2026-10-07 --today 2026-10-21

Prints the JSON the app displays. The plan is made the first time a patient is
seen (this takes a few minutes) and read from its saved copy afterwards.
"""

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

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
parser.add_argument("--surgery-date", required=True, type=date.fromisoformat, help="YYYY-MM-DD")
parser.add_argument("--today", type=date.fromisoformat, default=date.today(), help="YYYY-MM-DD")
parser.add_argument("--days", type=int, default=42)
args = parser.parse_args()

plan = predict_normal_trajectory(
    json.loads(Path(args.d2_json).read_text()), args.days, cache_dir=ROOT / ".cache" / "recovery",
    progress=lambda step: print(f"  estimating {step} ...", file=sys.stderr, flush=True))
card = plan.home_screen(args.surgery_date, args.today)
print(json.dumps(card, ensure_ascii=False, indent=2) if card else "null  (today is outside the plan)")
