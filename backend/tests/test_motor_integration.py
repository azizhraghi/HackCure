"""D1 rehabilitation + guided movement tests wired into the shared backend."""

from app import clock
from app import models as m


def test_rehab_plan_is_personalised_from_the_patient_file(client):
    plan = client.get("/patients/sarah/rehab/plan").json()
    assert plan["patient_id"] == "sarah" and plan["affected_side"] == "right"
    cats = [e["category"] for e in plan["exercises"]]
    assert "knee_flexion" in cats and "ankle_pumps" in cats
    assert all(e["max_safety_angle_deg"] for e in plan["exercises"] if e["category"] == "knee_flexion")


def test_rehab_demo_good_session_counts_reps_and_is_stored(client, repo):
    r = client.post("/patients/sarah/rehab/demo", json={"kind": "good", "pain_eva": 3}).json()
    ex = r["session"]["exercise_results"][0]
    assert r["synthetic"] and r["session"]["status"] == "complete" and ex["completed_reps"] >= 1
    assert r["analysis"]["analysis_type"] == "rehabilitation" and "diagnosis" not in r["analysis"]
    assert r["heart_rate"]["status"] == "unknown"  # no ESP32 reading in the test database
    assert client.get("/patients/sarah/rehab/history").json()[0]["pain_eva"] == 3
    assert r["alerts"] == []


def test_rehab_high_pain_and_red_flag_words_reach_the_safety_lane(client, repo):
    r = client.post("/patients/sarah/rehab/demo", json={"kind": "good", "pain_eva": 8}).json()
    assert len(r["alerts"]) == 1
    alert = repo.get(m.Alert, r["alerts"][0])
    assert alert.level == "attention" and alert.rule == "rehab_pain_high"
    client.post("/patients/sarah/rehab/demo", json={"kind": "good", "difficulty": "I felt chest pain"})
    assert any(a.level == "urgent" for a in repo.open_alerts("sarah"))


def test_rehab_occluded_camera_abstains_instead_of_scoring(client):
    r = client.post("/patients/sarah/rehab/demo", json={"kind": "occluded"}).json()
    assert r["session"]["status"] == "abstained"


def test_motor_tests_need_opt_in_consent(client):
    assert client.post("/patients/sarah/motor/arm_hold", json={"demo": "normal"}).status_code == 403
    assert client.get("/patients/sarah/motor/tests").json()["consent"] is False


def test_motor_normal_vs_asymmetric_and_comparison_with_previous(client, repo):
    client.post("/patients/sarah/motor/consent", json={"granted": True})
    first = client.post("/patients/sarah/motor/arm_hold", json={"demo": "normal"}).json()
    assert first["result"]["review_suggested"] is False and first["alert_id"] is None and first["compared_with_previous"] is False
    clock.advance(60)
    second = client.post("/patients/sarah/motor/arm_hold", json={"demo": "left_arm_drifts"}).json()
    assert second["result"]["review_suggested"] is True and second["compared_with_previous"] is True
    alert = repo.get(m.Alert, second["alert_id"])
    assert alert.level == "attention" and "not a finding of illness" in alert.reason  # never an emergency, never a diagnosis
    assert client.get("/patients/sarah/motor/history").json()[0]["review_suggested"] is True


def test_motor_all_six_tests_run_on_demo_recordings(client):
    client.post("/patients/sarah/motor/consent", json={"granted": True})
    for t in client.get("/patients/sarah/motor/tests").json()["tests"]:
        for variant in t["demo_variants"]:
            r = client.post(f"/patients/sarah/motor/{t['id']}", json={"demo": variant})
            assert r.status_code == 200, (t["id"], variant, r.text)
            assert r.json()["result"]["status"] in ("complete", "limited", "not_interpretable")


def test_motor_test_not_offered_while_an_urgent_alert_is_open(client):
    client.post("/patients/sarah/motor/consent", json={"granted": True})
    client.post("/checkin", json={"pain": 5, "fatigue": 5, "mobility": 5, "comment": "I feel short of breath"})
    r = client.post("/patients/sarah/motor/smile", json={"demo": "normal"})
    assert r.status_code == 409


def test_motor_symptom_answers_go_through_the_urgent_gate(client, repo):
    client.post("/patients/sarah/motor/consent", json={"granted": True})
    r = client.post("/patients/sarah/motor/smile", json={"demo": "normal", "symptoms": {"dizziness": "I almost fainted"}}).json()
    assert r["urgent_gate"]["level"] == "urgent"
