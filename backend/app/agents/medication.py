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
    latest: dict[tuple, m.Observation] = {}  # the last answer for a slot wins (corrections)
    for o in repo.observations(patient_id, "med_dose", since=since):
        latest[(o.value.get("med_id"), o.value.get("scheduled_for"))] = o
    return [o for o in latest.values() if o.value.get("status") == "not_taken"]


# ---------------------------------------------------------------- actions

def send_due_reminders(repo: Repo, patient_id: str, now: datetime | None = None) -> list[m.Notification]:
    """One reminder per scheduled dose that is due now (within the grace window) and not yet answered."""
    from ..notifications import notify
    now = now or clock.now()
    out = []
    for dose in day_schedule(repo, patient_id, now):
        if dose["status"] != "due":
            continue
        n = notify(repo, patient_id, patient_id, "reminder", f'Time for {dose["name"]} {dose["dose"]}',
                   dose["purpose"], "medication", dose["med_id"],
                   dedupe_key=f'dose:{dose["med_id"]}:{dose["scheduled_for"]}')
        if n:
            out.append(n)
            audit.log(repo, patient_id, AGENT, "medication.reminder", dose, "medication", dose["med_id"])
    return out


def record_dose(repo: Repo, patient_id: str, med_id: str, scheduled_for: datetime, status: str,
                actor: str = "patient") -> dict:
    plan = repo.plan(patient_id)
    med = plan_med(plan, med_id)
    if med is None:
        raise ValueError(f"{med_id} is not in the approved plan")
    if scheduled_for.strftime("%H:%M") not in med["times"]:
        raise ValueError(f"{med['name']} is not scheduled at {scheduled_for:%H:%M}")
    member = repo.member(actor)
    source = "caregiver_on_behalf" if member and member.role == "caregiver" else "patient"
    obs = repo.add(m.Observation(patient_id=patient_id, type="med_dose", source=source,
                                 value={"med_id": med_id, "scheduled_for": scheduled_for.isoformat(),
                                        "status": status, "recorded_by": actor}))
    audit.log(repo, patient_id, AGENT, "medication.dose_recorded",
              {"med_id": med_id, "scheduled_for": scheduled_for, "status": status, "by": actor}, "observation", obs.id)
    result = {"observation_id": obs.id, "status": status, "flag": None}
    if status == "not_taken":
        # Text from the approved plan only. Never a catch-up dose suggestion.
        result["missed_dose_text"] = med.get("missed_dose_text", "Please tell your care team that a dose was missed.")
        result["flag"] = check_missed(repo, patient_id)
    return result


def check_missed(repo: Repo, patient_id: str, now: datetime | None = None) -> dict | None:
    """2+ missed doses in the plan's window -> caregiver task + attention flag for the clinician."""
    from .. import alerts
    from ..notifications import caregiver_allowed
    now = now or clock.now()
    rules = repo.plan(patient_id).get("medication_rules", {})
    window, needed = rules.get("missed_window_h", 48), rules.get("missed_count_for_flag", 2)
    missed = missed_doses(repo, patient_id, window, now)
    if len(missed) < needed:
        return None
    plan = repo.plan(patient_id)
    names = sorted({(plan_med(plan, o.value["med_id"]) or {}).get("name", o.value["med_id"]) for o in missed})
    reason = f"{len(missed)} missed doses in {window} h ({', '.join(names)})"
    alert = alerts.create(repo, patient_id, "attention", "Missed medication doses", reason, "medication",
                          rule="missed_doses", evidence={"observation_ids": [o.id for o in missed]}, actor=AGENT)
    tasks = []
    for cg in repo.members(patient_id, "caregiver"):
        if not caregiver_allowed(plan, cg.id, "medications"):
            continue
        key = f"missed:{now.date()}"
        if repo.first(m.CaregiverTask, m.CaregiverTask.caregiver_id == cg.id, m.CaregiverTask.dedupe_key == key,
                      m.CaregiverTask.status == "open"):
            continue
        t = repo.add(m.CaregiverTask(patient_id=patient_id, caregiver_id=cg.id, category="medications",
                                     created_by=AGENT, dedupe_key=key,
                                     text=f"Help with medication reminders today: {', '.join(names)} doses were missed."))
        tasks.append(t.id)
        audit.log(repo, patient_id, AGENT, "caregiver_task.created", {"text": t.text}, "task", t.id)
    return {"alert_id": alert.id, "missed": len(missed), "caregiver_tasks": tasks}
