import time

from app import audit, clock, runner
from app import models as m
from seed import simulator


def _alerts(repo, level):
    repo.s.expire_all()
    return repo.all(m.Alert, m.Alert.level == level)


def test_urgent_breathless_fires_fast_without_llm(repo, monkeypatch):
    # Any agent/LLM work blows up: the urgent path must not care.
    def boom(*a, **k):
        raise RuntimeError("LLM down")
    monkeypatch.setitem(runner._jobs, "investigation", boom)
    t0 = time.perf_counter()
    simulator.inject(repo, "urgent_breathless")
    elapsed = time.perf_counter() - t0
    urgent = _alerts(repo, "urgent")
    assert urgent and elapsed < 5
    assert {a.rule for a in urgent} >= {"spo2_low"}
    fired = [e for e in audit.trail(repo, patient_id="sarah") if e.kind == "urgent.fired"]
    assert fired and all(e.data["llm_involved"] is False for e in fired)


def test_urgent_via_api_under_5s(client):
    t0 = time.perf_counter()
    r = client.post("/observations", json={"type": "spo2", "value": {"value": 88}, "source": "device", "simulated": True})
    assert time.perf_counter() - t0 < 5
    body = r.json()
    assert body["monitor"]["rule"]["level"] == "urgent" and body["monitor"]["alert_id"]


def test_bad_signal_flags_but_does_not_alert(repo):
    res = simulator.inject(repo, "bad_signal")
    assert all(r["quality"] == "unusable" and r.get("flag") == "unusable_reading" for r in res["results"])
    assert not _alerts(repo, "urgent")


def test_infection_pattern_requests_investigation(repo):
    # Vitals alone (HR + temp) are 2 deviation signals -> investigation request, no urgent alert.
    res = simulator.inject(repo, "infection_pattern")
    inv_ids = [r["investigation_id"] for r in res["results"] if r["investigation_id"]]
    assert len(inv_ids) == 1
    assert not _alerts(repo, "urgent")
    signals = {s["signal"] for r in res["results"] for s in r.get("signals", [])}
    assert {"hr_up", "temp_up"} <= signals


def test_urgent_aborts_running_investigation(repo):
    simulator.inject(repo, "infection_pattern")
    repo.s.expire_all()
    inv = repo.first(m.Investigation)
    if inv.status in ("running", "waiting_patient"):
        simulator.inject(repo, "urgent_breathless")
        repo.s.expire_all()
        assert repo.get(m.Investigation, inv.id).status == "aborted_urgent"


def test_temp_attention_threshold_opens_attention_alert(repo):
    from app.monitor import ingest
    obs, res = ingest(repo, m.ObservationIn(type="temp", value=38.6, source="device"))
    assert res["rule"]["level"] == "attention" and res["alert_id"] and res["investigation_id"]


def test_no_data_shows_gap(repo):
    simulator.inject(repo, "no_data")
    assert not repo.observations("sarah", "hr", since=clock.now() - __import__("datetime").timedelta(hours=6))


def test_chat_red_flag_skips_llm(client):
    r = client.post("/chat", json={"messages": [{"role": "user", "content": "I suddenly have chest pain"}]})
    assert r.status_code == 200 and r.json()["escalate"] is True  # no Mistral key needed
    assert client.get("/alerts", params={"role": "clinician", "open_only": True}).json()[0]["level"] == "urgent"
