"""Story hub: one place where the SurgiGuard API (ESP32 data, medications, family notifications) and the AI agents meet.

Everything under /hub is read-mostly glue for the /story page. The browser never holds the API keys: this router
calls the SurgiGuard API on its behalf.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import clock, monitor
from .. import models as m
from ..config import DEMO_PATIENT_ID, settings
from ..db import Repo, get_repo
from ..integrations import surgiguard_api as api
from ..safety.urgent_rules import RuleResult

router = APIRouter(prefix="/hub", tags=["hub"])


def _age_s(iso: str | None) -> float | None:
    if not iso:
        return None
    return round((datetime.now(timezone.utc) - api._parse_ts(iso)).total_seconds(), 1)


@router.get("/status")
def status(repo: Repo = Depends(get_repo)):
    """Link health + what the AI side currently knows (for the story page header)."""
    s = api.status(repo)
    pid = s["api_patient"]["id"] if s["api_patient"] else None
    s["device"] = None
    if pid:
        latest = api.get(f"/api/agents/patients/{pid}/telemetry/latest")
        age = _age_s(latest["timestamp"]) if latest else None
        s["device"] = {"id": s["api_patient"]["device_id"], "last_reading_age_s": age,
                       "online": age is not None and age < 20}
    s["ai"] = {"llm_mode": settings.llm_mode, "provider": settings.llm_provider,
               "open_alerts": len(repo.open_alerts(DEMO_PATIENT_ID))}
    return s


@router.get("/live")
def live(minutes: int = 3, repo: Repo = Depends(get_repo)):
    """Raw ESP32 stream as stored by the SurgiGuard API + the AI backend's reading of it."""
    pid = api.api_patient_id()
    now = datetime.now(timezone.utc)
    out: dict = {"linked": pid is not None, "now": now.isoformat()}
    if pid:
        latest = api.get(f"/api/agents/patients/{pid}/telemetry/latest")
        hist = api.get(f"/api/agents/patients/{pid}/telemetry/history",
                       **{"from": (now - timedelta(minutes=minutes)).isoformat(), "to": now.isoformat(), "interval_minutes": 0})
        out["latest"] = latest
        out["latest_age_s"] = _age_s(latest["timestamp"]) if latest else None
        out["points"] = (hist or {}).get("points", [])
        out["adherence"] = api.get(f"/api/agents/patients/{pid}/medications/adherence")
        out["schedule"] = api.get(f"/api/agents/patients/{pid}/medications/schedule", days=1,
                                  as_of=clock.now().strftime("%Y-%m-%dT%H:%M"), date=clock.now().strftime("%Y-%m-%d"))
    since = clock.now() - timedelta(hours=1)
    out["ai_observations"] = [
        {"type": o.type, "value": o.value, "quality": o.quality, "simulated": o.simulated, "source": o.source,
         "at": o.measured_at.isoformat()}
        for o in repo.observations(DEMO_PATIENT_ID, since=since, newest_first=True, limit=40) if o.type in ("hr", "spo2", "temp", "movement")]
    return out


@router.get("/family-alerts")
def family_alerts():
    """What the SurgiGuard API recorded and notified (FCM / WhatsApp, simulated unless enabled)."""
    pid = api.api_patient_id()
    return {"linked": pid is not None, "alerts": (api.get(f"/api/agents/patients/{pid}/alerts", limit=20) if pid else []) or []}


@router.post("/sync-now")
def sync_now(repo: Repo = Depends(get_repo)):
    return {"telemetry": api.sync_telemetry(repo), "plan_to_api": api.sync_plan_to_api(repo, force=True),
            "doses_from_api": api.sync_doses_from_api(repo)}


class SimulateIn(BaseModel):
    scenario: str  # fever | desaturation | tachycardia | fall | recover


SCENARIOS = {
    "fever": [("temp", {"value": 38.7}, "°C")],
    "high_fever": [("temp", {"value": 39.8}, "°C")],
    "desaturation": [("spo2", {"value": 88, "signal_quality": 0.95}, "%")],
    "tachycardia": [("hr", {"value": 112, "signal_quality": 0.95}, "bpm")],
    "recover": [("temp", {"value": 36.9}, "°C")],
}


@router.post("/simulate")
def simulate(body: SimulateIn, repo: Repo = Depends(get_repo)):
    """Readings the ESP32 cannot produce (it has no body-temperature probe) or that we do not want to provoke on a person.
    Always stored with simulated=True so every screen can tell them from the board's data."""
    if body.scenario == "fall":
        obs, _ = monitor.ingest(repo, m.ObservationIn(patient_id=DEMO_PATIENT_ID, type="movement", simulated=True,
                                                      value={"state": "SIMULATED", "fall": True}))
        alert = monitor.fire_urgent(repo, DEMO_PATIENT_ID,
                                    RuleResult("urgent", "fall_detected", "Fall detected (SIMULATED event)"), [obs.id])
        return {"scenario": "fall", "alert_id": alert.id}
    if body.scenario not in SCENARIOS:
        raise HTTPException(422, f"scenario must be one of {sorted([*SCENARIOS, 'fall'])}")
    results = []
    for typ, value, unit in SCENARIOS[body.scenario]:
        _, res = monitor.ingest(repo, m.ObservationIn(patient_id=DEMO_PATIENT_ID, type=typ, value=value, unit=unit,
                                                      source="device", simulated=True))
        results.append(res)
    return {"scenario": body.scenario, "monitor": results}


# ------------------------------------------------------------------ wound photos for the apps that talk to the SurgiGuard API
# The .NET API relays its patient's requests here (X-Api-Key Agents); only the API patient linked to the AI patient is served.

from fastapi import File, Form, Header, UploadFile  # noqa: E402

from .. import wound_photos, wounds  # noqa: E402


def _linked(api_patient_id: str, key: str | None) -> None:
    if key != settings.surgiguard_agents_key:
        raise HTTPException(401, "agents key required")
    if api.api_patient_id() != api_patient_id:
        raise HTTPException(404, "this SurgiGuard API patient is not followed by the AI backend")


@router.get("/wound/{api_patient_id}")
def wound_for_api_patient(api_patient_id: str, x_api_key: str | None = Header(default=None), repo: Repo = Depends(get_repo)):
    _linked(api_patient_id, x_api_key)
    photos = repo.observations(DEMO_PATIENT_ID, "photo", newest_first=True, limit=10)
    return {"status": wound_photos.eligibility(repo, DEMO_PATIENT_ID), "photos": [wounds.public(o) for o in photos]}


@router.post("/wound/{api_patient_id}")
async def wound_upload_for_api_patient(api_patient_id: str, file: UploadFile = File(...),
                                       dressing_change_confirmed: bool = Form(False),
                                       x_api_key: str | None = Header(default=None), repo: Repo = Depends(get_repo)):
    _linked(api_patient_id, x_api_key)
    from .wounds import upload_wound_photo
    return await upload_wound_photo(DEMO_PATIENT_ID, file, DEMO_PATIENT_ID, dressing_change_confirmed, repo)
