"""Developer 1 <-> the shared backend.

- Expected recovery (d1 trajectory_prediction): from the patient's "D2 JSON" (d2_bridge.d2_document), an LLM
  writes what a normal recovery looks like day by day. It takes minutes on Groq's free tier, so it runs once in a
  background thread and is cached on disk (backend/.cache/recovery); the home screen shows today's card.
- Patient Twin (d1 patient_twin): near-term HR / SpO2 forecast from this patient's own readings, or an abstention.
Both are supplementary: they never change alerts, schedules or the urgent path.
"""

import logging
import sys
import threading
from datetime import timezone
from pathlib import Path

from .. import clock
from ..config import settings
from ..db import Repo, session_scope

log = logging.getLogger("surgiguard.d1")
ROOT = Path(__file__).resolve().parents[3]
D1_SRC = ROOT / "d1" / "src"
CACHE = Path(__file__).resolve().parents[2] / ".cache" / "recovery"
UNITS = {"hr": "bpm", "spo2": "%"}

_lock = threading.Lock()
_jobs: dict[str, dict] = {}  # patient_id -> {"status": computing|ready|failed, "trajectory", "error", "key"}


def _import_d1():
    if str(D1_SRC) not in sys.path:
        sys.path.insert(0, str(D1_SRC))
    import surgiguard_d1.patient_twin as twin  # noqa: F401
    import surgiguard_d1.trajectory_prediction as tp  # noqa: F401
    return tp, twin


def available() -> tuple[bool, str]:
    if not D1_SRC.exists():
        return False, "Developer 1 package (d1/src) is not in this checkout."
    if settings.llm_mode != "live" or not settings.groq_api_key:
        return False, "Expected recovery needs a live LLM (GROQ_API_KEY and LLM_MODE=live)."
    return True, ""


# ------------------------------------------------------------------ expected recovery (home-screen card)

def expected_today(repo: Repo, patient_id: str, start: bool = True) -> dict:
    from .d2_bridge import d2_document
    patient = repo.patient(patient_id)
    if patient is None:
        return {"status": "unknown_patient"}
    document = d2_document(repo, patient_id)
    key = repr(sorted(document["extraction"].items(), key=str))
    with _lock:
        job = _jobs.get(patient_id)
        if job and job["key"] != key:  # the plan changed: the expectation must be rebuilt
            job = None
        if job and job["status"] == "ready":
            card = job["trajectory"].home_screen(patient.surgery_date.date(), clock.now().date())
            return {"status": "ready", "card": card, "generated_by": job["trajectory"].generated_by,
                    "note": "What a typical uncomplicated recovery looks like; not a clinical reference. "
                            "Not reviewed by a clinician."}
        if job and job["status"] == "computing":
            return {"status": "computing", "since": job["since"]}
        ok, reason = available()
        if not ok:
            return {"status": "unavailable", "reason": reason}
        if job and job["status"] == "failed" and not start:
            return {"status": "failed", "error": job["error"]}
        if not start:
            return {"status": "not_started"}
        _jobs[patient_id] = {"status": "computing", "key": key, "since": clock.now().isoformat()}
    threading.Thread(target=_compute, args=(patient_id, document, key), daemon=True, name=f"d1-{patient_id}").start()
    return {"status": "computing", "since": _jobs[patient_id]["since"]}


def _compute(patient_id: str, document: dict, key: str) -> None:
    try:
        tp, _ = _import_d1()
        trajectory = tp.predict_normal_trajectory(document, 42, language="English", cache_dir=CACHE,
                                                  progress=lambda step: log.info("D1 %s: %s", patient_id, step))
        result = {"status": "ready", "trajectory": trajectory}
    except Exception as e:  # never breaks the app: the card simply stays unavailable
        log.warning("D1 expected recovery failed for %s: %s", patient_id, e)
        result = {"status": "failed", "error": f"{type(e).__name__}: {str(e)[:300]}"}
    with _lock:
        if _jobs.get(patient_id, {}).get("key") == key:
            _jobs[patient_id] = {**_jobs[patient_id], **result}


# ------------------------------------------------------------------ Patient Twin (near-term forecast)

def twin_forecast(repo: Repo, patient_id: str) -> dict:
    if not D1_SRC.exists():
        return {"status": "unavailable", "reason": "Developer 1 package (d1/src) is not in this checkout."}
    _, twin = _import_d1()
    from surgiguard_d1.physiology.series import Point
    now = clock.now()
    as_of = now.replace(tzinfo=timezone.utc)
    out = {}
    for code, unit in UNITS.items():
        points = []
        for o in repo.observations(patient_id, code, since=now - _hours(72), until=now):
            value = o.value.get("value") if isinstance(o.value, dict) else None
            if not isinstance(value, (int, float)):
                continue
            flags = ("device_reported_unusable",) if o.quality == "unusable" else ()
            points.append(Point(code=code, value=float(value), unit=unit,
                                occurred_at=o.measured_at.replace(tzinfo=timezone.utc),
                                received_at=o.received_at.replace(tzinfo=timezone.utc), observation_id=o.id,
                                event_id=o.id, method=o.source, device_id=None, reporter_id=None, flags=flags))
        forecasts = twin.forecast_metric(code, unit, points, as_of, twin.TrendForecaster())
        out[code] = [f.model_dump(mode="json") for f in forecasts]
    return {"status": "ok", "as_of": now.isoformat(), "simulated_time": True, "forecasts": out,
            "note": "Supplementary estimate from this patient's own readings; never a 'safe until' time."}


def _hours(n: int):
    from datetime import timedelta
    return timedelta(hours=n)


def warm(patient_id: str) -> None:
    """Start the expected-recovery job early (called at startup) so the card is ready when someone looks."""
    with session_scope() as repo:
        expected_today(repo, patient_id)
