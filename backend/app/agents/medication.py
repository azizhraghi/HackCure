"""B2 Medication Agent: rules only, no LLM.

- Reminders come from the approved plan schedule.
- Dose answers: taken | not_taken | postponed | unknown.
- No answer after the grace period means "unknown", never "taken".
- 2+ missed (not_taken) doses in 48 h -> CaregiverTask + attention flag for the clinician.
- Missed-dose text comes only from the plan; the agent never invents catch-up doses.
"""

from datetime import datetime, time, timedelta

from .. import audit, clock
from .. import models as m
from ..db import Repo

AGENT = "agent:medication"


def slot_time(day: datetime, hhmm: str) -> datetime:
    h, mnt = map(int, hhmm.split(":"))
    return datetime.combine(day.date(), time(h, mnt))


def plan_med(plan: dict, med_id: str) -> dict | None:
    return next((x for x in plan.get("medications", []) if x["id"] == med_id), None)


def dose_answers(repo: Repo, patient_id: str, since: datetime) -> dict[tuple[str, str], m.Observation]:
    """Latest answer per (med_id, scheduled_for iso)."""
    out: dict[tuple[str, str], m.Observation] = {}
    for o in repo.observations(patient_id, "med_dose", since=since - timedelta(hours=12)):
        out[(o.value.get("med_id"), o.value.get("scheduled_for"))] = o
    return out


def slots(plan: dict, start: datetime, end: datetime) -> list[tuple[dict, datetime]]:
    res = []
    day = datetime.combine(start.date(), time(0, 0))
    while day <= end:
        for med in plan.get("medications", []):
            for hhmm in med.get("times", []):
                ts = slot_time(day, hhmm)
                if start <= ts <= end:
                    res.append((med, ts))
        day += timedelta(days=1)
    return sorted(res, key=lambda x: x[1])


def dose_status(plan: dict, answer: m.Observation | None, ts: datetime, now: datetime) -> str:
    if answer is not None:
        return answer.value.get("status", "unknown")
    grace = plan.get("medication_rules", {}).get("answer_grace_min", 120)
    if ts > now:
        return "upcoming"
    if now - ts <= timedelta(minutes=grace):
        return "due"
    return "unknown"  # no answer: unknown, never assumed taken


def day_schedule(repo: Repo, patient_id: str, now: datetime | None = None) -> list[dict]:
    now = now or clock.now()
    plan = repo.plan(patient_id)
    start = datetime.combine(now.date(), time(0, 0))
    end = start + timedelta(days=1) - timedelta(seconds=1)
    answers = dose_answers(repo, patient_id, start)
    out = []
    for med, ts in slots(plan, start, end):
        ans = answers.get((med["id"], ts.isoformat()))
        out.append({"med_id": med["id"], "name": med["name"], "dose": med["dose"], "purpose": med["purpose"],
                    "scheduled_for": ts.isoformat(), "status": dose_status(plan, ans, ts, now)})
    return out


def missed_doses(repo: Repo, patient_id: str, hours: int = 48, now: datetime | None = None) -> list[m.Observation]:
    now = now or clock.now()
    since = now - timedelta(hours=hours)
    return [o for o in repo.observations(patient_id, "med_dose", since=since) if o.value.get("status") == "not_taken"]
