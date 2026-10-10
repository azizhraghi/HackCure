"""Care-plan dressing windows govern photo requests and uploads, independently of the LLM."""

from datetime import datetime, time, timedelta
from hashlib import sha256
from threading import RLock

from . import audit, clock
from . import models as m
from .db import Repo
from .notifications import notify

_lock = RLock()
PROMPT = ("Add a wound photo during this dressing change permitted by your care plan. "
          "Do not remove the dressing just to take a photo.")


def eligibility(repo: Repo, pid: str) -> dict:
    plan = repo.plan(pid)
    policy = plan.get("wound_photo_schedule") or {}
    patient = repo.patient(pid)
    if "wound_photo" not in plan.get("allowed_tests", []):
        return {"status": "blocked", "permitted": False, "reason": "Wound photos are not permitted by the care plan."}
    if not patient or not isinstance(policy, dict) or policy.get("mode") != "permitted_dressing_changes" or not policy.get("windows"):
        return {"status": "unconfigured", "permitted": False,
                "reason": "No dressing-change schedule is recorded. Ask the care team to confirm it."}
    windows = []
    try:
        for item in policy["windows"]:
            day = patient.discharge_date.date() + timedelta(days=int(item["day_offset"]))
            start = datetime.combine(day, time.fromisoformat(item["start"]))
            end = datetime.combine(day, time.fromisoformat(item["end"]))
            if start.tzinfo or end.tzinfo or end <= start:
                raise ValueError("invalid window")
            key = sha256(f'{pid}:{plan.get("version")}:{item["id"]}:{start}:{end}'.encode()).hexdigest()[:24]
            windows.append({"slot_id": key, "starts_at": start.isoformat(), "ends_at": end.isoformat()})
    except (ValueError, TypeError, KeyError):
        return {"status": "unconfigured", "permitted": False, "reason": "The dressing-change schedule needs care-team review."}
    now = clock.now().isoformat()
    for window in sorted(windows, key=lambda w: w["starts_at"]):
        if window["starts_at"] <= now < window["ends_at"]:
            slot = repo.get(m.PhotoCollectionSlot, window["slot_id"])
            done = bool(slot and slot.observation_id)
            return {"status": "completed" if done else "due", "permitted": not done, "window": window,
                    "next_window": next((w for w in sorted(windows, key=lambda w: w["starts_at"])
                                         if w["starts_at"] >= window["ends_at"]), None),
                    "reason": "Photo recorded for this dressing change." if done else PROMPT}
    upcoming = next((w for w in sorted(windows, key=lambda w: w["starts_at"]) if w["starts_at"] > now), None)
    return {"status": "not_due", "permitted": False, "next_window": upcoming,
            "reason": "Wait for the next dressing change permitted by your care plan."}


def request(repo: Repo, pid: str, investigation_id: str | None = None, reason: str = "") -> dict:
    with _lock:
        if any(a.level == "urgent" for a in repo.open_alerts(pid)):
            return {"status": "deferred", "reason": "Urgent care takes precedence over wound-photo requests."}
        status = eligibility(repo, pid)
        if not status["permitted"]:
            return {"status": "deferred", "reason": status["reason"], "eligibility": status}
        window = status["window"]
        slot = repo.get(m.PhotoCollectionSlot, window["slot_id"])
        if slot and slot.request_id:
            req = repo.get(m.PatientRequest, slot.request_id)
            if req and req.status == "pending":
                if investigation_id and req.investigation_id not in (None, investigation_id):
                    return {"status": "deferred", "reason": "Another investigation is awaiting this photo."}
                if investigation_id and not req.investigation_id:
                    req.investigation_id = investigation_id
                    repo.add(req)
                return {"status": "requested", "request_id": req.id, "window": window}
            return {"status": "deferred", "reason": "This window's photo request has already been processed."}
        if not slot:
            slot = repo.add(m.PhotoCollectionSlot(id=window["slot_id"], patient_id=pid,
                           starts_at=datetime.fromisoformat(window["starts_at"]),
                           ends_at=datetime.fromisoformat(window["ends_at"])))
        req = repo.add(m.PatientRequest(patient_id=pid, investigation_id=investigation_id, kind="photo",
                       prompt=PROMPT, reason=reason or "Scheduled dressing-change photo (care plan)", expires_at=slot.ends_at))
        slot.request_id = req.id
        repo.add(slot)
        notify(repo, pid, pid, "request", "Dressing-change photo", PROMPT, "request", req.id)
        audit.log(repo, pid, "rule:dressing_schedule", "photo.requested", window, "request", req.id)
        return {"status": "requested", "request_id": req.id, "window": window}


def validate_answer(repo: Repo, req: m.PatientRequest, confirmed: bool) -> m.PhotoCollectionSlot:
    status = eligibility(repo, req.patient_id)
    if not confirmed:
        raise ValueError("Confirm that this photo is being added during a permitted dressing change.")
    if not status["permitted"]:
        raise ValueError(status["reason"])
    slot = repo.get(m.PhotoCollectionSlot, status["window"]["slot_id"])
    if not slot or slot.request_id != req.id:
        raise ValueError("This request is not linked to the current dressing-change window.")
    return slot


def sweep(repo: Repo) -> list[str]:
    requests = []
    for patient in repo.all(m.Patient):
        # Active urgent alerts take precedence over optional photo collection.
        if any(a.level == "urgent" for a in repo.open_alerts(patient.id)):
            continue
        result = request(repo, patient.id)
        if result.get("request_id"):
            requests.append(result["request_id"])
    return requests
