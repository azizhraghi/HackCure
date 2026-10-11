from datetime import datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException

from .. import clock, monitor, wound_photos
from .. import models as m
from ..agents import medication
from ..db import Repo, get_repo
from ..notifications import caregiver_allowed
from ..safety import quality

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
    latest_inv = repo.first(m.Investigation, m.Investigation.patient_id == patient_id,
                            order=m.Investigation.started_at.desc())
    from ..agents.investigation_workflow import patient_progress
    return {
        "patient": {"id": p.id, "name": p.name, "first_name": p.first_name, "age": p.age, "surgery": p.surgery,
                    "day": day_number(p, now) if p.surgery != "Not yet supplied" else None, "allergies": p.allergies},
        "now": now.isoformat(),
        "tasks": tasks,
        "appointments": appointments,
        "pending_requests": [r.model_dump() for r in repo.pending_requests(patient_id)],
        "open_alerts": len(repo.open_alerts(patient_id)),
        "next_step": next_step.model_dump() if next_step else None,
        "wound_photo": wound_photos.eligibility(repo, patient_id),
        "investigation_progress": patient_progress(repo, latest_inv) if latest_inv else None,
    }


@router.get("/patients/{patient_id}/twin")
def twin(patient_id: str, role: str = "patient", member_id: str | None = None, hours: int = 24,
         repo: Repo = Depends(get_repo)):
    """Recovery twin: expected (baseline/plan) vs observed. Missing data is "unknown", unusable is "unreliable".

    role=caregiver&member_id=ahmed returns only the categories the patient shared.
    """
    p = get_patient(repo, patient_id)
    plan = repo.plan(patient_id)
    now = clock.now()
    th = plan.get("thresholds", {})
    since = now - timedelta(hours=hours)

    def allowed(cat: str) -> bool:
        return role != "caregiver" or (member_id is not None and caregiver_allowed(plan, member_id, cat))

    out: dict = {"patient_id": p.id, "day": day_number(p, now), "now": now.isoformat(), "role": role}
    if allowed("vitals"):
        tol = {"hr": th.get("hr_deviation_bpm", 15), "temp": th.get("temp_deviation_c", 1.0), "spo2": None}
        stale = {"bp": 24 * 60}
        vitals = {}
        for metric in ("hr", "spo2", "temp", "bp"):
            rows = repo.observations(patient_id, metric, since=since)
            st = quality.metric_status(rows, now, stale.get(metric, th.get("stale_after_min", 240)))
            base = (p.baselines or {}).get(metric)
            expected = None
            if metric == "spo2":
                expected = {"min": th.get("spo2_urgent_below", 90), "max": 100}
            elif tol.get(metric) is not None and base is not None:
                expected = {"min": round(base - tol[metric], 1), "max": round(base + tol[metric], 1)}
            vitals[metric] = {
                **st, "baseline": base, "expected_range": expected,
                "gaps": quality.find_gaps(rows, since, now,
                                          plan.get("vitals_schedule", {}).get(metric, {}).get("expected_every_min", 60)),
                "series": [{"at": o.measured_at.isoformat(), "value": o.value, "quality": o.quality,
                            "simulated": o.simulated, "observation_id": o.id} for o in rows],
            }
        out["vitals"] = vitals
        out["deviation_signals"] = monitor.compute_signals(repo, patient_id)
    if allowed("symptoms"):
        cis = [o for o in repo.observations(patient_id, "checkin", newest_first=True, limit=12) if "items" in o.value]
        out["checkins"] = {
            "latest": ({"at": cis[0].measured_at.isoformat(), "scores_1_to_5":
                        {k: v["scale5"] for k, v in cis[0].value["items"].items()}} if cis else None),
            "status": "ok" if cis and (now - cis[0].measured_at) < timedelta(hours=14) else "unknown",
            "history": [{"at": o.measured_at.isoformat(), "scores_1_to_5": {k: v["scale5"] for k, v in o.value["items"].items()}}
                        for o in reversed(cis[:6])],
            "worsening": monitor.checkin_worsening(repo, patient_id),
        }
    if allowed("medications"):
        doses = medication.dose_answers(repo, patient_id, now - timedelta(hours=48))
        slots = medication.slots(plan, now - timedelta(hours=48), now)
        counts = {"taken": 0, "not_taken": 0, "postponed": 0, "unknown": 0, "due": 0}
        for med, ts in slots:
            st = medication.dose_status(plan, doses.get((med["id"], ts.isoformat())), ts, now)
            counts[st] = counts.get(st, 0) + 1
        out["medications"] = {"last_48h": counts, "today": medication.day_schedule(repo, patient_id, now)}
    if allowed("wound"):
        photos = repo.observations(patient_id, "photo", newest_first=True, limit=3)
        out["wound"] = {"photos": [{"observation_id": o.id, "at": o.measured_at.isoformat(), "url": o.value.get("url"),
                                    "label": o.value.get("label")} for o in photos],
                        "status": "ok" if photos else "unknown"}
    if allowed("alerts"):
        alerts_ = repo.open_alerts(patient_id)
        out["alerts"] = [{"id": a.id, "level": a.level, "state": a.state, "title": a.title} for a in alerts_]
        inv = repo.first(m.Investigation, m.Investigation.patient_id == patient_id,
                         order=m.Investigation.started_at.desc())
        out["investigation"] = ({"id": inv.id, "status": inv.status} if inv and role == "clinician" else None)
    out["hidden_categories"] = [c for c in ("vitals", "symptoms", "medications", "wound", "alerts") if not allowed(c)]
    return out
