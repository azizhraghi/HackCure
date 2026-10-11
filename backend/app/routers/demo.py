"""Demo controls: reset, scenarios, run any scheduled job now, move the demo clock."""

import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from .. import alerts, audit, clock, requests_service, sweep, wound_photos
from .. import models as m
from ..agents import checkin, digest, medication
from ..config import settings
from ..db import Repo, get_repo

router = APIRouter(prefix="/demo", tags=["demo"])
DEMO_MEASUREMENTS = {"hr": 90, "spo2": 96, "temp": 37.9, "bp": {"systolic": 126, "diastolic": 80}}


@router.post("/clock/next_dressing_change")
def next_dressing_change(repo: Repo = Depends(get_repo)):
    status = wound_photos.eligibility(repo, "sarah")
    if not status["permitted"]:
        window = status.get("next_window")
        if not window:
            raise HTTPException(409, "No upcoming dressing window in the demo plan. Reset the demo to load its schedule.")
        clock.advance((datetime.fromisoformat(window["starts_at"]) - clock.now()).total_seconds())
    audit.log(repo, "sarah", "demo", "clock.dressing_window", {"now": clock.now()}, "patient", "sarah")
    return {"now": clock.now(), "sweep": sweep.run(repo), "wound_photo": wound_photos.eligibility(repo, "sarah")}


@router.post("/alerts/{alert_id}/followup-evidence")
def followup_evidence(alert_id: str, body: m.ActorBody, repo: Repo = Depends(get_repo)):
    """Explicitly synthetic follow-up for exercising the verification UI offline."""
    try:
        alert = alerts.get(repo, alert_id)
        alerts._clinician(repo, alert, body.actor)
        if alert.state != "action_taken":
            raise alerts.AlertError("record the clinician action before adding follow-up evidence")
    except alerts.AlertError as e:
        raise HTTPException(e.status, str(e)) from e
    obs = repo.add(m.Observation(patient_id=alert.patient_id, type="checkin", source="patient", simulated=True,
                   value={"comment": "Synthetic follow-up for workflow demonstration; no clinical assessment implied.",
                          "demo_alert_id": alert.id}))
    audit.log(repo, alert.patient_id, body.actor, "demo.followup_evidence", {"observation_id": obs.id}, "alert", alert.id)
    return obs


@router.post("/reset")
def reset(repo: Repo = Depends(get_repo)):
    from seed.demo_seed import load
    from ..integrations import d2_bridge
    clock.clear_offset()
    d2_bridge._indexed.clear()  # the RAG index is rebuilt from the reseeded plan on the next question
    return {"ok": True, **load(repo)}


@router.post("/scenario/{name}")
def scenario(name: str, with_checkin: bool = True, patient_id: str = "sarah", repo: Repo = Depends(get_repo)):
    """normal | infection_pattern | urgent_breathless | bad_signal | no_data.
    infection_pattern submits Sarah's check-in first (fatigue 7/10) unless with_checkin=false."""
    from seed import simulator
    if name not in simulator.SCENARIOS:
        raise HTTPException(404, f"unknown scenario; choose one of {simulator.SCENARIOS}")
    out = simulator.inject(repo, name, patient_id, with_checkin=with_checkin)
    repo.s.expire_all()
    return {**out, "open_alerts": [a.model_dump() for a in repo.open_alerts(patient_id)],
            "pending_requests": repo.pending_requests(patient_id)}


@router.post("/run/{job}")
def run_job(job: str, patient_id: str = "sarah", repo: Repo = Depends(get_repo)):
    """Trigger a scheduled job immediately: checkin | medication | digest | sweep."""
    if job == "checkin":
        n = checkin.send_reminder(repo, patient_id)
        return {"reminder": n}
    if job == "medication":
        sent = medication.send_due_reminders(repo, patient_id)
        return {"reminders": sent, "missed_flag": medication.check_missed(repo, patient_id)}
    if job == "digest":
        return {"digests": [digest.generate(repo, patient_id, cg.id) for cg in repo.members(patient_id, "caregiver")]}
    if job == "sweep":
        return sweep.run(repo)
    raise HTTPException(404, "unknown job; choose checkin | medication | digest | sweep")


@router.post("/answer_pending")
def answer_pending(patient_id: str = "sarah", option_index: int = 1, repo: Repo = Depends(get_repo)):
    """Presenter shortcut (no phone): answer every pending request like Sarah would
    (day-3 wound photo, multiple-choice option `option_index`)."""
    answered = []
    for _ in range(6):
        active = repo.active_investigation(patient_id)
        if active:  # live agents are slower: let it post its next request (or finish) first
            _wait_for_agent(repo, active.id)
        repo.s.expire_all()
        reqs = repo.pending_requests(patient_id)
        if not reqs:
            break
        r = reqs[0]
        if r.kind == "photo":
            body = m.RequestAnswer(photo_asset="day3", dressing_change_confirmed=True)
        elif r.kind == "measurement":
            body = m.RequestAnswer(value=DEMO_MEASUREMENTS.get(r.metric))
        else:
            body = m.RequestAnswer(option_index=min(option_index, len(r.options) - 1))
        res = requests_service.answer(repo, r.id, body)
        answered.append({"request_id": r.id, "kind": r.kind, "prompt": r.prompt, "status": res["status"]})
        if r.investigation_id:
            _wait_for_agent(repo, r.investigation_id)
    return {"answered": answered}


def _wait_for_agent(repo: Repo, inv_id: str, max_s: float = 60) -> None:
    """Agents run in a worker thread: give the investigation time to ask its next question or finish."""
    deadline = time.monotonic() + max_s
    while time.monotonic() < deadline:
        repo.s.expire_all()
        inv = repo.get(m.Investigation, inv_id)
        if inv is None or inv.status != "running":
            return
        time.sleep(0.25)


@router.post("/clock/advance")
def advance(seconds: float, repo: Repo = Depends(get_repo)):
    now = clock.advance(seconds)
    audit.log(repo, "sarah", "demo", "clock.advanced", {"seconds": seconds, "now": now})
    return {"now": now.isoformat(), "sweep": sweep.run(repo)}


@router.get("/status")
def status(patient_id: str = "sarah", repo: Repo = Depends(get_repo)):
    inv = repo.first(m.Investigation, m.Investigation.patient_id == patient_id, order=m.Investigation.started_at.desc())
    return {"now": clock.now().isoformat(), "llm_mode": settings.llm_mode,
            "open_alerts": [a.model_dump() for a in repo.open_alerts(patient_id)],
            "pending_requests": repo.pending_requests(patient_id),
            "latest_investigation": inv.model_dump(exclude={"state"}) if inv else None}


@router.post("/llm_mode/{mode}")
def set_llm_mode(mode: str):
    """Switch live | stub | off at runtime (e.g. show the urgent path with the LLM 'down')."""
    if mode not in ("live", "stub", "off"):
        raise HTTPException(422, "live | stub | off")
    settings.llm_mode = mode
    return {"llm_mode": mode}
