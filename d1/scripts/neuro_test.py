"""Measure a guided movement test from a video.

    python scripts/neuro_test.py arm_hold my_video.mp4
    python scripts/neuro_test.py smile selfie.mp4 --mirrored

Tests: arm_hold, smile, finger_to_nose, hand_open_close, eyebrows_and_eyes, head_and_gaze.
Use --mirrored for a front-camera video that was saved mirrored (text in it reads backwards).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from surgiguard_d1.neuro import TESTS, analyze  # noqa: E402
from surgiguard_d1.neuro.video import read_video  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("test", choices=list(TESTS))
parser.add_argument("video")
parser.add_argument("--mirrored", action="store_true")
parser.add_argument("--json", action="store_true")
args = parser.parse_args()

recording = read_video(args.video, args.test, mirrored=args.mirrored)
result = analyze(recording)
if args.json:
    print(result.model_dump_json(indent=2))
    sys.exit()

print(f"{result.test}: {result.status}   ({len(recording.frames)} frames, {recording.seconds:.1f} s)")
for o in result.observations:
    print(f"  - {o}")
if result.review_suggested:
    print("  => worth a clinician's look")
for m in result.measurements:
    if m.value is not None:
        print(f"      {m.code}{' (' + m.side + ')' if m.side else ''}: {m.value:g} {m.unit}")
for note in result.limitations:
    print(f"  ! {note}")
