from datetime import datetime

import pytest

from app import models as m
from app.agents import medication
from tests.conftest import DEMO_NOW

TODAY_14 = datetime(DEMO_NOW.year, DEMO_NOW.month, DEMO_NOW.day, 14, 0)


def test_one_missed_dose_is_not_flagged(repo):
    assert len(medication.missed_doses(repo, "sarah")) == 1  # seeded: cefuroxime yesterday evening
    assert medication.check_missed(repo, "sarah") is None


def test_two_missed_doses_create_caregiver_task_and_clinician_flag(repo):
    res = medication.record_dose(repo, "sarah", "m5", TODAY_14, "not_taken", actor="sarah")
    assert res["missed_dose_text"].startswith("Do not take two doses together")
    flag = res["flag"]
    assert flag and flag["missed"] == 2 and flag["caregiver_tasks"]
    alert = repo.get(m.Alert, flag["alert_id"])
    assert alert.level == "attention" and alert.assigned_to == "dr_ruiz"
    task = repo.get(m.CaregiverTask, flag["caregiver_tasks"][0])
    assert task.caregiver_id == "ahmed" and "Cefuroxime" in task.text
    # a third miss does not duplicate the task or the alert
    res2 = medication.record_dose(repo, "sarah", "m1", TODAY_14, "not_taken")
    assert res2["flag"]["caregiver_tasks"] == [] and res2["flag"]["alert_id"] == alert.id


def test_correction_to_taken_clears_missed(repo):
    medication.record_dose(repo, "sarah", "m5", TODAY_14, "not_taken")
    medication.record_dose(repo, "sarah", "m5", TODAY_14, "taken")
    assert len(medication.missed_doses(repo, "sarah")) == 1


def test_unanswered_dose_is_unknown_not_taken(repo):
    plan = repo.plan("sarah")
    assert medication.dose_status(plan, None, TODAY_14, DEMO_NOW.replace(hour=18)) == "unknown"
    assert medication.dose_status(plan, None, TODAY_14, DEMO_NOW.replace(hour=14, minute=30)) == "due"


def test_reminders_once_per_slot(repo):
    from app import clock
    clock.advance(4 * 3600 + 35 * 60)  # 20:05 -> evening doses due
    first = medication.send_due_reminders(repo, "sarah")
    assert {n.ref_id for n in first} == {"m1", "m4", "m5"}
    assert medication.send_due_reminders(repo, "sarah") == []


def test_rejects_meds_or_times_not_in_plan(repo):
    with pytest.raises(ValueError):
        medication.record_dose(repo, "sarah", "ibuprofen", TODAY_14, "taken")
    with pytest.raises(ValueError):
        medication.record_dose(repo, "sarah", "m4", TODAY_14, "taken")  # enoxaparin is 20:00 only


def test_caregiver_on_behalf_source(client):
    r = client.post("/medications/dose", json={"med_id": "m5", "scheduled_for": TODAY_14.isoformat(),
                                                "status": "taken", "actor": "ahmed"})
    assert r.status_code == 200
    from app.db import session_scope
    with session_scope() as s:
        assert s.get(m.Observation, r.json()["observation_id"]).source == "caregiver_on_behalf"
