# SurgiGuard AI — Developer 1

The normal recovery plan for a patient, built once from Developer 2's JSON
and split into days. Each day the patient app shows that day's part: how it is
normal to feel, what is normal to notice, and anything scheduled.

## Use it

```python
from surgiguard_d1.recovery import predict_normal_trajectory

plan = predict_normal_trajectory(d2_json)             # once per patient
card = plan.home_screen(surgery_date, date.today())   # each day, for the home screen
```

`card` is `{"day", "surgery", "message", "normal_today", "normal_pain", "today"}`,
or `None` before surgery or after the plan ends.

From the command line, run inside this `d1/` folder:

```
python scripts/home_screen.py examples/d2_sample.json --surgery-date 2026-10-07 --today 2026-10-21
python scripts/predict_recovery.py examples/d2_sample.json     # the whole plan
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

## What to know

- Input is Developer 2's extraction JSON (`examples/d2_sample.json`). Names,
  prescriber and dates are removed before anything is sent to the LLM.
- The surgery date is not in that JSON yet; `home_screen` needs it.
- The plan is a guide for the patient, not a clinical reference. Its medical
  content has not been reviewed by a clinician.
- `physiology/`, `twin/`, `trajectory/` and `forecast/` under `src/` are earlier
  work kept for reference; the recovery plan does not use them.
- The pretrained weights in `models/chronos-bolt-tiny/` are not committed
  (only used by `forecast/`); download `amazon/chronos-bolt-tiny` from Hugging Face.
