"""Simulated device data + demo scenarios. Everything here is tagged source=device, simulated=true
(symptom reports are tagged source=patient, simulated=true).

In-process:  inject(repo, "infection_pattern")   (used by POST /demo/scenario/{name})
Stand-alone: python -m seed.simulator --url http://localhost:8000 --scenario normal --every 5
             streams readings to POST /observations, like an ESP32 would.
"""

import argparse
import random
import time
from datetime import timedelta

from app import clock
from app import models as m
from app import monitor
from app.db import Repo

SCENARIOS = ("normal", "infection_pattern", "urgent_breathless", "bad_signal", "no_data")


def _vital(type_: str, value: dict, minutes_ago: float = 0) -> m.ObservationIn:
    unit = {"hr": "bpm", "spo2": "%", "temp": "C", "bp": "mmHg"}[type_]
    return m.ObservationIn(type=type_, value=value, unit=unit, source="device", simulated=True,
                           measured_at=clock.now() - timedelta(minutes=minutes_ago))


def readings(scenario: str) -> list[m.ObservationIn]:
    if scenario == "normal":
        return [_vital("hr", {"value": 72}), _vital("spo2", {"value": 97}), _vital("temp", {"value": 36.8})]
    if scenario == "infection_pattern":
        return [_vital("hr", {"value": 88}, 20), _vital("spo2", {"value": 96}, 20), _vital("hr", {"value": 90}, 10),
                _vital("temp", {"value": 37.9}, 5), _vital("hr", {"value": 91}, 0)]
    if scenario == "urgent_breathless":
        return [_vital("hr", {"value": 104}), _vital("spo2", {"value": 88, "signal_quality": 0.95})]
    if scenario == "bad_signal":
        return [_vital("spo2", {"value": 71, "signal_quality": 0.1}), _vital("spo2", {"value": 64, "signal_quality": 0.15})]
    if scenario == "no_data":
        return []
    raise ValueError(f"unknown scenario {scenario}; choose one of {SCENARIOS}")


# Sarah's day-3 check-in in the demo story: fatigue 7/10 (= 4/5; it was 2/5 yesterday)
DEMO_CHECKIN = {"pain": 4, "fatigue": 7, "mobility": 4, "chips": [], "comment": "Very tired today"}


def inject(repo: Repo, scenario: str, patient_id: str = "sarah", with_checkin: bool = False) -> dict:
    """Apply a scenario in-process. Every reading goes through the Monitor exactly like POST /observations.

    with_checkin (infection_pattern): submit Sarah's check-in first, as in the demo story.
    """
    results = []
    checkin_result = None
    if scenario == "infection_pattern" and with_checkin:
        from app.agents import checkin
        checkin_result = checkin.submit(repo, m.CheckinIn(patient_id=patient_id, **DEMO_CHECKIN))
    if scenario == "no_data":
        cutoff = clock.now() - timedelta(hours=6)
        repo.delete_where(m.Observation, m.Observation.patient_id == patient_id, m.Observation.source == "device",
                          m.Observation.simulated == True, m.Observation.measured_at >= cutoff)  # noqa: E712
        return {"scenario": scenario, "removed_device_readings_since": cutoff.isoformat(), "results": []}
    for r in readings(scenario):
        r.patient_id = patient_id
        obs, res = monitor.ingest(repo, r)
        results.append(res)
    if scenario == "urgent_breathless":
        report = m.ObservationIn(patient_id=patient_id, type="checkin", source="patient", simulated=True,
                                 value={"chips": ["shortness_of_breath"], "comment": "severe breathlessness"})
        obs, res = monitor.ingest(repo, report)
        results.append(res)
    return {"scenario": scenario, "checkin": checkin_result, "results": results}


def stream(url: str, scenario: str, every: float, count: int) -> None:  # pragma: no cover - manual tool
    import httpx
    rng = random.Random()
    for i in range(count):
        for r in readings(scenario if scenario != "no_data" else "normal"):
            body = r.model_dump(mode="json")
            body["measured_at"] = None
            if isinstance(body["value"], dict) and "value" in body["value"] and r.type == "hr":
                body["value"]["value"] += rng.randint(-1, 1)
            res = httpx.post(f"{url.rstrip('/')}/observations", json=body, timeout=10)
            print(r.type, body["value"], "->", res.status_code, res.json().get("monitor", {}).get("rule"))
        time.sleep(every)


if __name__ == "__main__":  # pragma: no cover
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--scenario", default="normal", choices=SCENARIOS)
    ap.add_argument("--every", type=float, default=5)
    ap.add_argument("--count", type=int, default=1000)
    a = ap.parse_args()
    stream(a.url, a.scenario, a.every, a.count)
