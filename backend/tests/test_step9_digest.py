from app import llm, monitor
from app import models as m
from app.agents import checkin, digest
from app.config import settings
from seed import simulator


def restrict(repo, **cats):
    row = repo.first(m.SurveillancePlan)
    plan = dict(row.plan)
    perms = dict(plan["caregiver_permissions"]["ahmed"]["categories"])
    perms.update(cats)
    plan["caregiver_permissions"] = {"ahmed": {"categories": perms}}
    row.plan = plan
    repo.add(row)


def busy_day(repo):
    checkin.submit(repo, m.CheckinIn(pain=4, fatigue=7, mobility=4))
    simulator.inject(repo, "infection_pattern")
    monitor.ingest(repo, m.ObservationIn(type="spo2", value=88, source="device"))  # urgent alert


def words(text):
    return len(text.split())


def test_digest_short_and_plain(repo):
    busy_day(repo)
    d = digest.generate(repo, "sarah", "ahmed")
    assert 0 < words(d.text) <= 80
    assert not digest.check_text(d.text, hidden=[])
    assert len(d.task_ids) <= 3


def test_hidden_categories_never_appear(repo):
    restrict(repo, vitals=False, medications=False, wound=False, alerts=False)
    busy_day(repo)
    events = digest.collect_events(repo, "sarah", "ahmed", since=repo.patient("sarah").discharge_date)
    assert {e["category"] for e in events} <= {"symptoms", "rehab", "appointments"}
    d = digest.generate(repo, "sarah", "ahmed")
    low = d.text.lower()
    for cat in ("vitals", "medications", "wound", "alerts"):
        assert not any(w in low for w in digest.HIDDEN_WORDS[cat]), (cat, d.text)
    for tid in d.task_ids:
        assert repo.get(m.CaregiverTask, tid).category in {"symptoms", "rehab", "appointments"}


def test_leaky_or_long_llm_output_falls_back_to_template(repo, monkeypatch):
    restrict(repo, medications=False)
    busy_day(repo)

    def leaky(messages, ctx):
        return {"summary": "Sarah missed her antibiotic dose and may have an infection. " + "word " * 90,
                "tasks": [{"text": "Give her the missed tablet", "category": "medications"}]}
    monkeypatch.setitem(llm._stubs, "digest", leaky)
    d = digest.generate(repo, "sarah", "ahmed")
    assert d.mode == "template" and words(d.text) <= 80
    assert "antibiotic" not in d.text.lower() and "infection" not in d.text.lower()
    assert all(repo.get(m.CaregiverTask, t).category != "medications" for t in d.task_ids)


def test_llm_down_uses_template(repo, monkeypatch):
    monkeypatch.setattr(settings, "llm_mode", "off")
    busy_day(repo)
    d = digest.generate(repo, "sarah", "ahmed")
    assert d.mode == "template" and d.text


def test_finished_investigation_triggers_digest(repo):
    from tests.test_step7_investigation import drive, start_infection
    inv = start_infection(repo)
    drive(repo, inv.id)
    repo.s.expire_all()
    d = repo.first(m.Digest, m.Digest.caregiver_id == "ahmed")
    assert d and words(d.text) <= 80
    assert repo.first(m.Notification, m.Notification.member_id == "ahmed", m.Notification.kind == "digest")


def test_digest_api(client):
    body = client.get("/caregiver/ahmed/digest", params={"refresh": True}).json()
    assert body["digest"]["text"] and "vitals" in body["shared_categories"]
    assert client.get("/caregiver/sarah/digest").status_code == 404


def test_reassurance_rejected(repo, monkeypatch):
    busy_day(repo)
    monkeypatch.setitem(llm._stubs, "digest", lambda msgs, ctx: {
        "summary": "Sarah's evening is smooth and she is resting well. The care team is handling a minor update.",
        "tasks": []})
    d = digest.generate(repo, "sarah", "ahmed")
    assert d.mode == "template" and "minor" not in d.text


def test_investigation_caregiver_message_respects_permissions(repo):
    from tests.test_step7_investigation import drive, start_infection
    restrict(repo, medications=False, wound=False)
    inv = start_infection(repo)
    drive(repo, inv.id)
    repo.s.expire_all()
    task = repo.first(m.CaregiverTask, m.CaregiverTask.dedupe_key == f"inv:{inv.id}")
    assert task and not digest.check_text(task.text, ["medications", "wound"])
