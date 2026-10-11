"""S1 Monitor: quality -> urgent rules -> deviation -> investigation_request.

Runs synchronously inside the request that delivered the data. It never calls an LLM, so
urgent alerts fire even when the LLM is down. Investigations are handed to the runner.
"""

from datetime import timedelta
from statistics import median
from typing import Any

from . import alerts, audit, clock, runner
from . import models as m
from .db import Repo
from .notifications import notify
from .safety import quality, urgent_rules
from .safety.urgent_rules import RuleResult

ACTOR = "monitor"
VITALS = ("hr", "spo2", "temp", "bp")
URGENT_TITLES = {
    "spo2_low": "Low oxygen saturation",
    "temp_very_high": "Very high temperature",
    "red_flag_text": "Red-flag symptom reported",
    "red_flag_symptom": "Red-flag symptom reported",
    "fall_detected": "Fall detected",
}


def ingest(repo: Repo, data: m.ObservationIn) -> tuple[m.Observation, dict]:
    value: Any = data.value if isinstance(data.value, dict) else {"value": data.value}
    q = quality.assess(data.type, value, data.quality) if data.type in VITALS else (data.quality or "good")
    now = clock.now()
    obs = repo.add(m.Observation(patient_id=data.patient_id, type=data.type, value=value, unit=data.unit,
                                 measured_at=data.measured_at or now, received_at=now, source=data.source,
                                 quality=q, simulated=data.simulated))
    return obs, process(repo, obs)


def process(repo: Repo, obs: m.Observation) -> dict:
    pid = obs.patient_id
    plan = repo.plan(pid)
    out: dict = {"observation_id": obs.id, "quality": obs.quality, "alert_id": None, "investigation_id": None}

    rule = urgent_rules.evaluate_observation(obs.type, obs.value, obs.quality, plan)
    out["rule"] = {"level": rule.level, "rule": rule.rule, "reason": rule.reason}
    audit.log(repo, pid, ACTOR, "monitor.rules", {"observation_id": obs.id, "type": obs.type, "quality": obs.quality,
                                                  **out["rule"]}, "observation", obs.id)

    if rule.urgent:
        out["alert_id"] = fire_urgent(repo, pid, rule, [obs.id]).id
        return out
    if obs.quality == "unusable":
        out["flag"] = "unusable_reading"  # shown as "unreliable" in the twin, never as normal
        return out
    if rule.level == "attention":
        a = alerts.create(repo, pid, "attention", URGENT_TITLES.get(rule.rule, "Reading needs review"), rule.reason,
                          "rule", rule=rule.rule, evidence={"observation_ids": [obs.id]}, actor="rule:" + rule.rule)
        out["alert_id"] = a.id
    signals = compute_signals(repo, pid)
    out["signals"] = signals
    needed = plan.get("thresholds", {}).get("deviation_signals_to_investigate", 2)
    if rule.investigate or len(signals) >= needed:
        trigger = {"observation_id": obs.id, "rule": rule.rule, "signals": signals}
        inv = request_investigation(repo, pid, trigger)
        out["investigation_id"] = inv.id if inv else None
    return out


def gate_answer(repo: Repo, patient_id: str, answer: Any, context: dict, observation_ids: list[str]) -> RuleResult:
    """Every patient/caregiver answer goes through here before any agent sees it."""
    rule = urgent_rules.evaluate_answer(answer, repo.plan(patient_id))
    audit.log(repo, patient_id, "rule:urgent", "gate.answer", {"level": rule.level, "rule": rule.rule,
                                                               "matched": list(rule.matched), **context})
    if rule.urgent:
        fire_urgent(repo, patient_id, rule, observation_ids)
    return rule


def fire_urgent(repo: Repo, patient_id: str, rule: RuleResult, observation_ids: list[str]) -> m.Alert:
    started = clock.now()
    alert = alerts.create(repo, patient_id, "urgent", URGENT_TITLES.get(rule.rule or "", "Urgent"), rule.reason,
                          "rule", rule=rule.rule, evidence={"observation_ids": observation_ids,
                                                            "matched": list(rule.matched)},
                          actor="rule:" + (rule.rule or "urgent"))
    inv = repo.active_investigation(patient_id)
    if inv:
        abort_investigation(repo, inv, f"Urgent rule fired: {rule.reason}", alert.id)
    audit.log(repo, patient_id, "rule:urgent", "urgent.fired",
              {"alert_id": alert.id, "reason": rule.reason, "llm_involved": False,
               "ms": int((clock.now() - started).total_seconds() * 1000)}, "alert", alert.id)
    return alert


def abort_investigation(repo: Repo, inv: m.Investigation, reason: str, alert_id: str | None = None) -> None:
    inv.status = "aborted_urgent"
    inv.finished_at = clock.now()
    inv.alert_id = inv.alert_id or alert_id
    repo.add(inv)
    for r in repo.all(m.PatientRequest, m.PatientRequest.investigation_id == inv.id,
                      m.PatientRequest.status == "pending"):
        r.status = "cancelled"
        repo.add(r)
    audit.log(repo, inv.patient_id, ACTOR, "investigation.aborted", {"reason": reason, "alert_id": alert_id},
              "investigation", inv.id)


def compute_signals(repo: Repo, patient_id: str) -> list[dict]:
    """Deviations from the patient's baseline / previous check-in. Only good-quality data counts."""
    now = clock.now()
    p = repo.patient(patient_id)
    th = repo.plan(patient_id).get("thresholds", {})
    base = p.baselines if p else {}
    signals = []

    hr = [o for o in repo.observations(patient_id, "hr", since=now - timedelta(minutes=60)) if o.quality == "good"]
    if hr and "hr" in base:
        med = median(o.value["value"] for o in hr)
        if med >= base["hr"] + th.get("hr_deviation_bpm", 15):
            signals.append({"signal": "hr_up", "text": f"Heart rate {med:g} bpm vs baseline {base['hr']}",
                            "observation_ids": [o.id for o in hr[-3:]]})

    temp = repo.first(m.Observation, m.Observation.patient_id == patient_id, m.Observation.type == "temp",
                      m.Observation.quality == "good", m.Observation.measured_at >= now - timedelta(hours=4),
                      order=m.Observation.measured_at.desc())
    if temp and "temp" in base and temp.value["value"] >= base["temp"] + th.get("temp_deviation_c", 1.0):
        signals.append({"signal": "temp_up", "text": f"Temperature {temp.value['value']:g}°C vs baseline {base['temp']}",
                        "observation_ids": [temp.id]})

    worse = checkin_worsening(repo, patient_id, since=now - timedelta(hours=24))
    if worse:
        signals.append({"signal": "checkin_worse",
                        "text": ", ".join(f"{w['item']} {w['before']}→{w['now']}/5" for w in worse["items"]),
                        "observation_ids": [worse["observation_id"], worse["previous_id"]]})
    return signals


def checkin_worsening(repo: Repo, patient_id: str, since=None) -> dict | None:
    """Compare the latest scored check-in with the previous one (1-5 scale, higher = worse)."""
    rows = [o for o in repo.observations(patient_id, "checkin", newest_first=True, limit=20) if "items" in o.value]
    if len(rows) < 2 or (since and rows[0].measured_at < since):
        return None
    delta = repo.plan(patient_id).get("checkin", {}).get("worsening_delta", 2)
    latest, prev = rows[0], rows[1]
    items = []
    for k, v in latest.value["items"].items():
        before = prev.value["items"].get(k, {}).get("scale5")
        if before is not None and v["scale5"] - before >= delta:
            items.append({"item": k, "before": before, "now": v["scale5"], "delta": v["scale5"] - before})
    if not items:
        return None
    items.sort(key=lambda x: -x["delta"])
    return {"observation_id": latest.id, "previous_id": prev.id, "items": items}


def request_investigation(repo: Repo, patient_id: str, trigger: dict) -> m.Investigation | None:
    from .config import settings
    active = repo.active_investigation(patient_id)
    if active:
        audit.log(repo, patient_id, ACTOR, "monitor.investigation_skipped", {"reason": "already running",
                                                                             "active": active.id})
        return None
    now = clock.now()
    recent = repo.first(m.Investigation, m.Investigation.patient_id == patient_id,
                        m.Investigation.started_at >= now - timedelta(minutes=20))
    if recent:
        audit.log(repo, patient_id, ACTOR, "monitor.investigation_skipped", {"reason": "recently investigated",
                                                                             "recent": recent.id})
        return None
    inv = repo.add(m.Investigation(patient_id=patient_id, trigger=trigger, started_at=now,
                                   deadline=now + timedelta(seconds=settings.investigation_timeout_s)))
    audit.log(repo, patient_id, ACTOR, "investigation_request", trigger, "investigation", inv.id)
    text = repo.plan(patient_id).get("patient_texts", {}).get("investigation_started")
    if text:
        notify(repo, patient_id, patient_id, "info", "A quick check", text, "investigation", inv.id)
    runner.submit("investigation", inv.id)
    return inv
