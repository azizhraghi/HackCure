# SurgiGuard AI — Developer 1

| Part | Folder | What it does |
|---|---|---|
| **Trajectory prediction** | `src/surgiguard_d1/trajectory_prediction/` | Takes the patient's surgery, age and medications (Developer 2's JSON) and says what a normal recovery looks like for someone like him. Made once, before any readings from home, covering the whole recovery, split into days. This is what the app's home screen shows. |
| **Patient Twin** | `src/surgiguard_d1/patient_twin/` | Takes the numbers actually coming from the patient's wearable and continues the curve a few hours ahead. It knows nothing about the surgery; it only follows his data. Built, not yet connected to live readings. |
| **Guided movement tests** | `src/surgiguard_d1/neuro/` | Six short phone-camera tests for signs of neurological distress: arm hold, smile, finger to nose, hand open and close, eyebrows and eyes, head and gaze. Each measures the movement and compares left with right, and with the patient's earlier sessions. Reports what was seen; does not diagnose. |
| Physiology pipeline | `src/surgiguard_d1/physiology/` | Validates and cleans vital-sign readings and describes their trends. Feeds the Patient Twin. |
| Earlier experiments | `src/surgiguard_d1/legacy/` | Kept for reference; not used by the parts above. |

## Use it

```python
from surgiguard_d1.trajectory_prediction import predict_normal_trajectory

plan = predict_normal_trajectory(d2_json)             # once per patient
card = plan.home_screen(surgery_date, date.today())   # each day, for the home screen
```

`card` is `{"day", "surgery", "message", "normal_today", "normal_pain", "today"}`,
or `None` before surgery or after the plan ends.

From the command line, run inside this `d1/` folder:

```
python scripts/home_screen.py examples/d2_sample.json --surgery-date 2026-10-07 --today 2026-10-21
python scripts/predict_trajectory.py examples/d2_sample.json     # the whole plan
```

## Setup

```
pip install -e ".[dev]" groq
echo "GROQ_API_KEY=your-key" > .env      # never committed
python -m pytest -q
```

The plan is written by an LLM (Groq, model `openai/gpt-oss-120b`; override with
`GROQ_MODEL`). A new patient takes a few minutes on Groq's free tier; the result
is saved under `.cache/recovery/` and read from there afterwards.

## Guided movement tests

```
sh scripts/fetch_neuro_models.sh                      # once: pretrained MediaPipe models
pip install mediapipe opencv-python-headless
python scripts/neuro_test.py arm_hold my_video.mp4    # add --mirrored for a mirrored selfie video
```

In code: `analyze(read_video(path, "arm_hold"))`, or build `Frame`s yourself if the phone
computes the joint positions. The cut-offs that decide when a difference is "worth a
clinician's look" (`Limits` in `neuro/tests.py`) are engineering defaults, not validated
on patients.

## What to know

- Input is Developer 2's extraction JSON (`examples/d2_sample.json`). Names,
  prescriber and dates are removed before anything is sent to the LLM.
- The surgery date is not in that JSON yet; `home_screen` needs it.
- The plan is a guide for the patient, not a clinical reference. Its medical
  content has not been reviewed by a clinician.
- The pretrained weights in `models/chronos-bolt-tiny/` are not committed
  (only used by the Patient Twin's pretrained forecaster); download `amazon/chronos-bolt-tiny` from Hugging Face.
