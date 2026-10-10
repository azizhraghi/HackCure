from datetime import datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException

from .. import clock
from .. import models as m
from ..agents import medication
from ..db import Repo, get_repo

router = APIRouter(tags=["patient"])


def get_patient(repo: Repo, patient_id: str) -> m.Patient:
    p = repo.patient(patient_id)
    if not p:
        raise HTTPException(404, f"unknown patient {patient_id}")
    return p


def day_number(p: m.Patient, now: datetime) -> int:
    """Day 1 = discharge day."""
    return (now.date() - p.discharge_date.date()).days + 1


@router.get("/patients/{patient_id}/today")
def today(patient_id: str, repo: Repo = Depends(get_repo)):
    p = get_patient(repo, patient_id)
    plan = repo.plan(patient_id)
    now = clock.now()
    start = datetime.combine(now.date(), time(0, 0))

    checkins_today = repo.observations(patient_id, "checkin", since=start)
    tasks = []
    for hhmm in plan.get("checkin", {}).get("times", []):
        ts = medication.slot_time(now, hhmm)
        done = any(abs((c.measured_at - ts).total_seconds()) < 6 * 3600 for c in checkins_today
                   if "items" in c.value)
        tasks.append({"kind": "checkin", "time": hhmm, "title": "Daily check-in",
                      "status": "done" if done else ("due" if ts <= now else "upcoming")})
    for dose in medication.day_schedule(repo, patient_id, now):
        tasks.append({"kind": "medication", "time": dose["scheduled_for"][11:16],
                      "title": f'{dose["name"]} {dose["dose"]}', **dose})
    for ex in plan.get("rehab", []):
        for hhmm in ex["times"]:
            tasks.append({"kind": "rehab", "time": hhmm, "title": f'{ex["name"]} ({ex["detail"]})',
                          "status": "upcoming" if medication.slot_time(now, hhmm) > now else "due"})
    tasks.sort(key=lambda t: t["time"])

    appointments = []
    for a in plan.get("appointments", []):
        when = medication.slot_time(p.discharge_date + timedelta(days=a["day_offset"]), a["time"])
        if when >= now:
            appointments.append({"title": a["title"], "at": when.isoformat()})

    next_step = repo.first(m.Notification, m.Notification.member_id == patient_id,
                           m.Notification.kind.in_(["next_step", "alert"]), order=m.Notification.created_at.desc())
    return {
        "patient": {"id": p.id, "name": p.name, "first_name": p.first_name, "age": p.age, "surgery": p.surgery,
                    "day": day_number(p, now), "allergies": p.allergies},
        "now": now.isoformat(),
        "plan_approved_by": "dr_ruiz",
        "tasks": tasks,
        "appointments": appointments,
        "pending_requests": [r.model_dump() for r in repo.pending_requests(patient_id)],
        "open_alerts": len(repo.open_alerts(patient_id)),
        "next_step": next_step.model_dump() if next_step else None,
    }
