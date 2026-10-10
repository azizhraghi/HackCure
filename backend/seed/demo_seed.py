"""Fictional demo data: Sarah Miller, total knee replacement (right), day 3 after discharge.

Everything generated here is simulated (`simulated=True`). History is built relative to the
demo clock so the story works whenever the demo is run.
"""

import json
import random
from datetime import datetime, time, timedelta
from pathlib import Path

from app import clock
from app import models as m
from app.agents.checkin import to_scale5
from app.db import Repo, drop_all

SEED_DIR = Path(__file__).parent
PLAN = json.loads((SEED_DIR / "plan_sarah.json").read_text(encoding="utf-8"))
PHOTO_COMPARISONS = json.loads((SEED_DIR / "photo_comparisons.json").read_text(encoding="utf-8"))

BASELINES = {"hr": 72, "spo2": 97, "temp": 36.8, "bp": {"systolic": 120, "diastolic": 78}}
UNITS = {"hr": "bpm", "spo2": "%", "temp": "C", "bp": "mmHg"}


def at(day: datetime, hhmm: str) -> datetime:
    h, mnt = map(int, hhmm.split(":"))
    return datetime.combine(day.date(), time(h, mnt))


def load(repo: Repo, now: datetime | None = None) -> dict:
    """Wipe the database and load the demo patient. Returns a few useful ids."""
    drop_all()
    now = now or clock.now()
    rng = random.Random(42)

    today = datetime.combine(now.date(), time(0, 0))
    discharge = at(today - timedelta(days=2), "11:00")  # discharge day = day 1, today = day 3
    surgery = discharge - timedelta(days=2)

    repo.add(m.Patient(id="sarah", name="Sarah Miller", first_name="Sarah", age=64,
                       surgery="Total knee replacement (right)", surgery_date=surgery,
                       discharge_date=discharge, allergies=["penicillin"], baselines=BASELINES))
    for mem in [
        m.CareTeamMember(id="sarah", patient_id="sarah", name="Sarah Miller", role="patient"),
        m.CareTeamMember(id="ahmed", patient_id="sarah", name="Ahmed Khan", role="caregiver", relation="partner"),
        m.CareTeamMember(id="dr_ruiz", patient_id="sarah", name="Dr. Elena Ruiz", role="clinician", relation="surgeon"),
        m.CareTeamMember(id="dr_oncall", patient_id="sarah", name="On-call surgical team", role="clinician",
                         relation="backup", is_backup=True),
    ]:
        repo.add(mem)
    repo.add(m.SurveillancePlan(patient_id="sarah", approved_by="dr_ruiz", approved_at=discharge - timedelta(hours=2),
                                plan=PLAN))

    # -- vitals: normal days 1-2, slow drift over the last 24 h (HR -> ~84, temp -> ~37.5)
    objs: list[m.Observation] = []
    drift_start = now - timedelta(hours=24)
    t = discharge + timedelta(hours=1)
    end = now - timedelta(minutes=45)
    while t <= end:
        p = max(0.0, (t - drift_start) / timedelta(hours=24))
        hr = round(72 + 12 * p + rng.uniform(-2, 2))
        spo2 = round(97 + rng.uniform(-1, 1))
        objs.append(_dev("hr", {"value": hr}, t))
        objs.append(_dev("spo2", {"value": spo2}, t))
        if t.hour % 2 == 0:
            temp = round(36.8 + 0.7 * p + rng.uniform(-0.1, 0.1), 1)
            objs.append(_dev("temp", {"value": temp}, t))
        if t.hour in (8, 20):
            objs.append(_dev("bp", {"systolic": 120 + rng.randint(-4, 4), "diastolic": 78 + rng.randint(-3, 3)}, t))
        t += timedelta(hours=1)

    # -- check-ins (0-10 form mapped to 1-5), days 1-2 only: today's is done live in the demo
    for day in (today - timedelta(days=2), today - timedelta(days=1)):
        for hhmm in ("08:00", "20:00"):
            ts = at(day, hhmm)
            if ts < discharge:
                continue
            objs.append(m.Observation(patient_id="sarah", type="checkin", source="patient", measured_at=ts,
                                      received_at=ts, value=checkin_value(pain=4, fatigue=3, mobility=4)))

    # -- medication doses: all taken, except the antibiotic yesterday evening
    missed = at(today - timedelta(days=1), "20:00")
    for med in PLAN["medications"]:
        day = datetime.combine(discharge.date(), time(0, 0))
        while day <= today:
            for hhmm in med["times"]:
                ts = at(day, hhmm)
                if ts <= discharge or ts > now - timedelta(minutes=60):
                    continue
                status = "not_taken" if (med["id"] == "m5" and ts == missed) else "taken"
                objs.append(m.Observation(patient_id="sarah", type="med_dose", source="patient",
                                          measured_at=ts + timedelta(minutes=5), received_at=ts + timedelta(minutes=5),
                                          value={"med_id": med["id"], "scheduled_for": ts.isoformat(), "status": status}))
            day += timedelta(days=1)

    # -- wound photos (day 1, day 2); the day-3 photo is taken live when the agent asks for it
    for asset, ts in (("day1", discharge + timedelta(hours=2)), ("day2", at(today - timedelta(days=1), "10:00"))):
        objs.append(m.Observation(id=f"obs_photo_{asset}", patient_id="sarah", type="photo", source="patient",
                                  measured_at=ts, received_at=ts,
                                  value={"asset": asset, "url": f"/static/photos/{asset}.svg", "label": asset}))

    for o in objs:
        repo.s.add(o)
    repo.s.commit()
    return {"patient_id": "sarah", "observations": len(objs), "discharge": discharge.isoformat()}


def _dev(type_: str, value: dict, ts: datetime) -> m.Observation:
    return m.Observation(patient_id="sarah", type=type_, value=value, unit=UNITS[type_], measured_at=ts,
                         received_at=ts, source="device", quality="good", simulated=True)


def checkin_value(pain: int, fatigue: int, mobility: int, chips=None, comment=None) -> dict:
    items = {k: {"raw": v, "scale5": to_scale5(v)} for k, v in
             (("pain", pain), ("fatigue", fatigue), ("mobility", mobility))}
    return {"items": items, "chips": list(chips or []), "comment": comment}
