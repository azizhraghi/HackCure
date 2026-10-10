from app import audit, monitor, requests_service
from app import models as m
from app.agents import checkin
from app.config import settings


def form(**kw):
    base = {"pain": 4, "fatigue": 3, "mobility": 4}
    return m.CheckinIn(**{**base, **kw})


def _hr(repo, value=90):
    monitor.ingest(repo, m.ObservationIn(type="hr", value=value, source="device", simulated=True))


def test_scale_mapping():
    assert [checkin.to_scale5(v) for v in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10)] == [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 5]


def test_stable_checkin_no_clarification(repo):
    res = checkin.submit(repo, form())
    assert res["status"] == "ok" and res["clarification"] is None and res["worsened"] == []


def test_worsened_fatigue_one_clarification_and_investigation(repo):
    _hr(repo, 90)  # one vital deviation (HR 90 vs baseline 72) ...
    res = checkin.submit(repo, form(fatigue=7))  # ... plus fatigue 2/5 -> 4/5
    assert res["worsened"] == [{"item": "fatigue", "before": 2, "now": 4, "delta": 2}]
    clar = res["clarification"]
    assert clar and clar.kind == "question" and len(clar.options) == 3 and clar.checkin_id == res["checkin_id"]
    # exactly one clarification even if several items worsen
    repo.s.expire_all()
    assert len(repo.all(m.PatientRequest, m.PatientRequest.checkin_id == res["checkin_id"])) == 1
    assert res["investigation_id"]
    inv = repo.get(m.Investigation, res["investigation_id"])
    assert {s["signal"] for s in inv.trigger["signals"]} == {"hr_up", "checkin_worse"}


def test_several_items_worse_still_one_clarification(repo):
    res = checkin.submit(repo, form(pain=9, fatigue=8, mobility=9))
    repo.s.expire_all()
    assert len(repo.all(m.PatientRequest, m.PatientRequest.checkin_id == res["checkin_id"])) == 1


def test_red_flag_chip_stops_checkin(repo):
    res = checkin.submit(repo, form(fatigue=8, chips=["shortness_of_breath"]))
    assert res["status"] == "urgent" and "clarification" not in res
    repo.s.expire_all()
    assert repo.first(m.Alert, m.Alert.level == "urgent")
    assert not repo.all(m.PatientRequest)  # no clarification, no investigation request
    assert not repo.all(m.Investigation)


def test_red_flag_comment_stops_checkin(repo):
    res = checkin.submit(repo, form(comment="I have chest pain since lunch"))
    assert res["status"] == "urgent"


def test_red_flag_in_clarification_answer(repo):
    res = checkin.submit(repo, form(fatigue=7))
    out = requests_service.answer(repo, res["clarification"].id, m.RequestAnswer(text="So tired, I fainted earlier"))
    assert out["status"] == "urgent"


def test_llm_down_uses_template_question(repo, monkeypatch):
    monkeypatch.setattr(settings, "llm_mode", "off")
    res = checkin.submit(repo, form(fatigue=7))
    assert "tiredness" in res["clarification"].prompt
    ev = [e for e in audit.trail(repo, patient_id="sarah") if e.kind == "checkin.clarification"][-1]
    assert ev.data["mode"].startswith("template")


def test_api(client):
    r = client.post("/checkin", json={"pain": 4, "fatigue": 7, "mobility": 4, "chips": [], "comment": None})
    assert r.status_code == 200 and r.json()["clarification"]["prompt"]
    assert client.post("/checkin", json={"pain": 11, "fatigue": 1, "mobility": 1}).status_code == 422
