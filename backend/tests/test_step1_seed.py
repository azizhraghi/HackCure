from app import models as m
from app.routers.chat import router as chat_router


def test_seed_loads(repo):
    p = repo.patient("sarah")
    assert p.name == "Sarah Miller" and "penicillin" in p.allergies
    assert {x.role for x in repo.members("sarah")} == {"patient", "caregiver", "clinician"}
    assert repo.plan("sarah")["thresholds"]["spo2_urgent_below"] == 90
    assert repo.observations("sarah", "hr")
    # one missed antibiotic dose yesterday evening, everything simulated is tagged
    missed = [o for o in repo.observations("sarah", "med_dose") if o.value["status"] == "not_taken"]
    assert len(missed) == 1 and missed[0].value["med_id"] == "m5"
    assert all(o.simulated and o.source == "device" for o in repo.observations("sarah", source="device"))
    # history drifts but stays below the investigation thresholds at seed time
    last_hr = repo.latest("sarah", "hr")
    assert 78 <= last_hr.value["value"] <= 86


def test_today_returns_plan_tasks(client):
    r = client.get("/patients/sarah/today")
    assert r.status_code == 200
    body = r.json()
    assert body["patient"]["day"] == 3
    kinds = {t["kind"] for t in body["tasks"]}
    assert {"checkin", "medication", "rehab"} <= kinds
    cef = [t for t in body["tasks"] if t.get("med_id") == "m5"]
    assert [t["time"] for t in cef] == ["08:00", "14:00", "20:00"]
    assert cef[0]["status"] == "taken" and cef[2]["status"] == "upcoming"


def test_unknown_patient_404(client):
    assert client.get("/patients/nobody/today").status_code == 404


def test_chat_still_routed(client):
    assert any(getattr(r, "path", "") == "/chat" for r in chat_router.routes)
    # No key in tests -> explicit 503, same behaviour as before
    r = client.post("/chat", json={"messages": [{"role": "user", "content": "When is physio?"}]})
    assert r.status_code == 503


def test_health(client):
    assert client.get("/health").json()["llm_mode"] == "stub"
