"""Link between the AI backend (this app) and the SurgiGuard API (.NET + MongoDB).

The SurgiGuard API is the source of truth for everything the hardware and the family apps touch:

    ESP32 --MQTT--> SurgiGuard API --(pull, every few s)--> telemetry_sync --> Monitor (urgent rules, signals, agents)
    care plan confirmed ------------------------------------> /api/agents/.../medications/sync  (Android alarms)
    doses taken in the Android/RN app ----(pull)------------> medication agent (med_dose observations)
    AI alert (alerts.create) -------------------------------> POST /api/alerts/trigger  (FCM / WhatsApp to the family)

Nothing here is required: with SURGIGUARD_LINK=off, or when the API is unreachable, the AI backend keeps running
on its own seed data. Failures are logged and counted, never raised into the calling request.
"""

import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any

import httpx

from .. import alerts as alerts_mod
from .. import audit, clock, monitor
from .. import models as m
from ..config import DEMO_PATIENT_ID, settings
from ..db import Repo, session_scope
from ..safety.urgent_rules import RuleResult

log = logging.getLogger("surgiguard.link")

_lock = threading.Lock()
_state: dict[str, Any] = {
    "patient_cache": (0.0, None),          # (fetched_at, api patient dict | None)
    "cursor": None,                         # last telemetry timestamp consumed (aware UTC)
    "buffer": [],                           # raw readings waiting for their window
    "last_ok": None, "last_error": None, "errors": 0,
    "readings_in": 0, "observations_out": 0, "last_reading_at": None,
    "alerts_pushed": [],                    # newest first, small ring
    "meds_synced_plan_version": None,
    "doses_imported": 0,
}


# --------------------------------------------------------------------------- HTTP

def enabled() -> bool:
    return settings.surgiguard_link != "off"


def _headers() -> dict:
    return {"X-Api-Key": settings.surgiguard_agents_key, "ngrok-skip-browser-warning": "true"}


def _request(method: str, path: str, **kw) -> Any | None:
    try:
        r = httpx.request(method, settings.surgiguard_api_url + path, headers=_headers(), timeout=4.0, **kw)
        if r.status_code >= 400:
            raise RuntimeError(f"{r.status_code} {r.text[:200]}")
        _state["last_ok"] = datetime.now(timezone.utc).isoformat()
        _state["last_error"] = None
        return r.json() if r.content else {}
    except Exception as e:  # network down, API restarting, 4xx/5xx: the AI side must keep running
        _state["errors"] += 1
        _state["last_error"] = f"{type(e).__name__}: {e}"[:300]
        log.debug("SurgiGuard API %s %s failed: %s", method, path, e)
        return None


def get(path: str, **params) -> Any | None:
    return _request("GET", path, params={k: v for k, v in params.items() if v is not None})


def post(path: str, body: Any) -> Any | None:
    return _request("POST", path, json=body)


# --------------------------------------------------------------------------- patient mapping

def api_patient(force: bool = False) -> dict | None:
    """The SurgiGuard API patient that plays the demo patient (DEMO_PATIENT_ID): configured id, else the owner of the ESP32."""
    if not enabled():
        return None
    fetched, cached = _state["patient_cache"]
    if not force and time.time() - fetched < 20:
        return cached
    rows = get("/api/agents/patients")
    found = None
    if rows:
        wanted = settings.surgiguard_patient_id
        if wanted and wanted != "auto":
            found = next((p for p in rows if p["id"] == wanted), None)
        else:
            found = (next((p for p in rows if p.get("device_id") == settings.esp32_device_id), None)
                     or (rows[0] if len(rows) == 1 else None))
    _state["patient_cache"] = (time.time(), found)
    return found


def api_patient_id() -> str | None:
    p = api_patient()
    return p["id"] if p else None


def _parse_ts(s: str) -> datetime:
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _to_local_naive(d: datetime) -> datetime:
    """The AI backend stores naive local datetimes (clock.now())."""
    return d.astimezone().replace(tzinfo=None)


# --------------------------------------------------------------------------- ESP32 telemetry -> Monitor

def _quality(valid: int, total: int) -> float:
    return round(valid / total, 2) if total else 0.0


def sync_telemetry(repo: Repo) -> dict:
    """Pull new ESP32 readings from the API, aggregate them per window, feed the Monitor.

    bpm/spo2 -> hr/spo2 (median of the window, signal_quality = share of valid samples: 0 means 'no finger').
    activity -> movement. A fall flag fires an urgent alert immediately (no window).
    The DHT11 room temperature is NOT body temperature and is never sent as `temp`.
    """
    pid = api_patient_id()
    if pid is None:
        return {"linked": False}
    if _state["cursor"] is None:
        _state["cursor"] = datetime.now(timezone.utc) - timedelta(minutes=2)
    rows = get(f"/api/agents/patients/{pid}/telemetry/since", after=_state["cursor"].isoformat(), limit=500)
    if rows is None:
        return {"linked": True, "error": _state["last_error"]}
    out = {"linked": True, "new_readings": len(rows), "observations": 0}
    for r in rows:
        ts = _parse_ts(r["timestamp"])
        r["_ts"] = ts
        _state["cursor"] = max(_state["cursor"], ts)
        _state["readings_in"] += 1
        _state["last_reading_at"] = ts.isoformat()
        if r.get("fall_detected"):
            out["observations"] += _handle_fall(repo, r)
        else:
            _state["buffer"].append(r)

    buf = _state["buffer"]
    if buf and (datetime.now(timezone.utc) - buf[0]["_ts"]).total_seconds() >= settings.esp32_window_s:
        _state["buffer"] = []
        out["observations"] += _flush_window(repo, buf)
    return out


def _handle_fall(repo: Repo, r: dict) -> int:
    when = _to_local_naive(r["_ts"])
    obs, _ = monitor.ingest(repo, m.ObservationIn(
        patient_id=DEMO_PATIENT_ID, type="movement", value={"state": r.get("motion_state"), "fall": True},
        measured_at=when, source="device", simulated=False))
    monitor.fire_urgent(repo, DEMO_PATIENT_ID,
                        RuleResult("urgent", "fall_detected", "Fall detected by the ESP32 motion sensor (MPU6050)"), [obs.id])
    return 1


def _flush_window(repo: Repo, rows: list[dict]) -> int:
    n = 0
    when = _to_local_naive(rows[len(rows) // 2]["_ts"])
    total = len(rows)
    for kind, field, unit, lo in (("hr", "bpm", "bpm", 25), ("spo2", "spo2", "%", 50)):
        vals = [float(r[field]) for r in rows if r.get(field) is not None and float(r[field]) >= lo]
        if not vals:  # 0 = sensor not worn: unknown, never "normal" and never a reading
            continue
        v = round(median(vals))
        obs, res = monitor.ingest(repo, m.ObservationIn(
            patient_id=DEMO_PATIENT_ID, type=kind, unit=unit, measured_at=when, source="device", simulated=False,
            value={"value": v, "signal_quality": _quality(len(vals), total), "samples": total,
                   "device": settings.esp32_device_id}))
        n += 1
        _check_patient_thresholds(repo, kind, v, obs, res)
    states = [r["motion_state"] for r in rows if r.get("motion_state")]
    if states:
        monitor.ingest(repo, m.ObservationIn(
            patient_id=DEMO_PATIENT_ID, type="movement", value={"state": states[-1], "fall": False},
            measured_at=when, source="device", simulated=False))
        n += 1
    _state["observations_out"] += n
    return n


def _check_patient_thresholds(repo: Repo, kind: str, v: float, obs: m.Observation, res: dict) -> None:
    """The patient's own thresholds live in the SurgiGuard API (MinBpm / MaxBpm / MinSpo2): respect them.
    The AI urgent rules keep their stricter clinical lines (SpO2 < 90 urgent); this adds an 'attention' level."""
    p = api_patient() or {}
    th = p.get("thresholds") or {}
    if res.get("alert_id") or obs.quality != "good":
        return
    msg = rule = None
    if kind == "hr" and th.get("max_bpm") and v > th["max_bpm"]:
        rule, msg = "hr_above_patient_max", f"Heart rate {v:g} bpm above this patient's limit ({th['max_bpm']} bpm)"
    elif kind == "hr" and th.get("min_bpm") and v < th["min_bpm"]:
        rule, msg = "hr_below_patient_min", f"Heart rate {v:g} bpm below this patient's limit ({th['min_bpm']} bpm)"
    elif kind == "spo2" and th.get("min_spo2") and v < th["min_spo2"]:
        rule, msg = "spo2_below_patient_min", f"SpO2 {v:g}% below this patient's limit ({th['min_spo2']:g}%)"
    if rule:
        alerts_mod.create(repo, DEMO_PATIENT_ID, "attention", "Reading outside the patient's limits", msg, "rule",
                          rule=rule, evidence={"observation_ids": [obs.id], "limits_from": "SurgiGuard API"},
                          actor="rule:" + rule)


# --------------------------------------------------------------------------- medications

def _plan_meds(repo: Repo) -> list[dict]:
    return repo.plan(DEMO_PATIENT_ID).get("medications", [])


def sync_plan_to_api(repo: Repo, force: bool = False) -> dict | None:
    """Care plan -> API medications (idempotent: matched by name; never deletes anything)."""
    pid = api_patient_id()
    if pid is None:
        return None
    version = repo.plan(DEMO_PATIENT_ID).get("version")
    if not force and _state["meds_synced_plan_version"] == version:
        return None
    body = [{"name": x["name"], "dosage": x.get("dose"), "instructions": x.get("purpose"), "times": x["times"]}
            for x in _plan_meds(repo)]
    res = post(f"/api/agents/patients/{pid}/medications/sync", body)
    if res is not None:
        _state["meds_synced_plan_version"] = version
        audit.log(repo, DEMO_PATIENT_ID, "integration:surgiguard-api", "medications.synced_to_api", res)
    return res


def sync_doses_from_api(repo: Repo, now: datetime | None = None) -> int:
    """TAKEN/SKIPPED answers given in the Android/RN app -> med_dose observations for the medication agent."""
    pid = api_patient_id()
    if pid is None:
        return 0
    now = now or clock.now()
    doses = get(f"/api/agents/patients/{pid}/medications/schedule", date=now.strftime("%Y-%m-%d"), days=1,
                as_of=now.strftime("%Y-%m-%dT%H:%M"))
    if not doses:
        return 0
    from ..agents import medication
    plan_meds = _plan_meds(repo)
    start = datetime.combine(now.date(), datetime.min.time())
    known = medication.dose_answers(repo, DEMO_PATIENT_ID, start)
    imported = 0
    for d in doses:
        status = {"TAKEN": "taken", "SKIPPED": "not_taken"}.get(d["status"])
        med = next((x for x in plan_meds if x["name"].lower() == d["name"].lower()), None)
        if not status or med is None or d["time"] not in med["times"]:
            continue
        ts = datetime.strptime(f'{d["date"]} {d["time"]}', "%Y-%m-%d %H:%M")
        prev = known.get((med["id"], ts.isoformat()))
        if prev is not None and prev.value.get("status") == status:
            continue
        try:
            medication.record_dose(repo, DEMO_PATIENT_ID, med["id"], ts, status, actor="surgiguard-api", trusted_import=True)
            imported += 1
        except ValueError:
            continue
    _state["doses_imported"] += imported
    return imported


# --------------------------------------------------------------------------- AI alerts -> API (family notifications)

def _api_type(alert: m.Alert) -> str:
    rule = (alert.rule or "").lower()
    text = f"{alert.title} {alert.reason}".lower()
    if "fall" in rule:
        return "FALL"
    if "spo2" in rule or "oxygen" in text or "spo2" in text:
        return "HYPOXIA"
    if rule.startswith("hr_below") or "bradycardia" in text:
        return "BRADYCARDIA"
    if rule.startswith("hr_") or "heart rate" in text:
        return "TACHYCARDIA"
    if "temp" in rule or "temperature" in text or "fever" in text:
        return "FEVER"
    if "wound" in rule or "wound" in text or "photo" in text:
        return "WOUND"
    if "red_flag" in rule or "symptom" in text:
        return "SYMPTOM"
    return "OTHER"


CLINICIAN_ONLY = ("motor_review_", "rehab_")
_SEVERITY = {"info": 1, "attention": 2, "urgent": 3}


def push_alert(alert: m.Alert) -> None:
    """Fire-and-forget: send an AI alert to the API so the family gets push/WhatsApp. Never blocks, never raises."""
    if not enabled() or alert.level not in ("attention", "urgent"):
        return
    if (alert.rule or "").startswith(CLINICIAN_ONLY):  # movement-test / rehab findings are for the care team, not the family
        return
    snap = {"id": alert.id, "patient_id": alert.patient_id, "level": alert.level, "rule": alert.rule,
            "title": alert.title, "reason": alert.reason, "source": alert.source}
    threading.Thread(target=_push_alert_now, args=(snap,), daemon=True, name="alert-push").start()


def _push_alert_now(a: dict) -> None:
    try:
        if a["patient_id"] != DEMO_PATIENT_ID:
            return
        pid = api_patient_id()
        record = {"alert_id": a["id"], "at": datetime.now(timezone.utc).isoformat(), "ok": False}
        if pid is not None:
            latest = get(f"/api/agents/patients/{pid}/telemetry/latest")
            vitals = ({"timestamp": latest["timestamp"], "bpm": latest.get("bpm"), "spo2": latest.get("spo2"),
                       "room_temp": latest.get("room_temp"), "room_humidity": latest.get("room_humidity"),
                       "fall_detected": latest.get("fall_detected")} if latest else None)
            api_type = _api_type(m.Alert(patient_id=a["patient_id"], level=a["level"], title=a["title"],
                                         reason=a["reason"], source=a["source"], rule=a["rule"]))
            res = post("/api/alerts/trigger", {
                "patient_id": pid, "type": api_type, "severity": _SEVERITY[a["level"]],
                "message": f'{a["title"]}: {a["reason"]}'[:1000],
                "source": f"SurgiGuard AI - {a['rule'] or a['source']}", "vitals": vitals})
            record.update(ok=res is not None, api_alert_id=(res or {}).get("id"), type=api_type,
                          severity=_SEVERITY[a["level"]], notifications=(res or {}).get("notifications", []),
                          error=None if res is not None else _state["last_error"])
        else:
            record["error"] = "no SurgiGuard API patient linked"
        with _lock:
            _state["alerts_pushed"] = [record, *_state["alerts_pushed"]][:20]
        with session_scope() as repo:
            audit.log(repo, a["patient_id"], "integration:surgiguard-api", "alert.pushed_to_api", record, "alert", a["id"])
    except Exception:
        log.exception("alert push failed")


# --------------------------------------------------------------------------- status

def status(repo: Repo | None = None) -> dict:
    p = api_patient() if enabled() else None
    return {
        "link": settings.surgiguard_link, "api_url": settings.surgiguard_api_url,
        "reachable": bool(_state["last_ok"]) and not _state["last_error"], "last_error": _state["last_error"],
        "errors": _state["errors"], "api_patient": ({"id": p["id"], "name": p["full_name"], "device_id": p.get("device_id"),
                                                     "thresholds": p.get("thresholds"), "family": p.get("family")} if p else None),
        "ai_patient": DEMO_PATIENT_ID, "esp32_device_id": settings.esp32_device_id,
        "telemetry": {"readings_in": _state["readings_in"], "observations_out": _state["observations_out"],
                      "last_reading_at": _state["last_reading_at"], "window_s": settings.esp32_window_s},
        "doses_imported": _state["doses_imported"], "alerts_pushed": _state["alerts_pushed"][:5],
        "plan_synced_version": _state["meds_synced_plan_version"],
    }
