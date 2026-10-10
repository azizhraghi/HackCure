"""The full demo story from the brief, end to end through the HTTP API, in stub mode."""

import time
from datetime import datetime

from app import clock
from app.config import settings


def test_full_demo_story(client):
    c = client
    assert c.post("/demo/reset").json()["ok"]
    today = c.get("/patients/sarah/today").json()
    assert today["patient"]["day"] == 3

    # 1. Daily check-in: fatigue 7/10 (= 4/5, yesterday 2/5) -> exactly one clarification
    ci = c.post("/checkin", json={"pain": 4, "fatigue": 7, "mobility": 4, "chips": [], "comment": "Very tired"}).json()
    assert ci["status"] == "ok" and ci["worsened"][0]["item"] == "fatigue"
    clar = ci["clarification"]
    assert c.post(f"/requests/{clar['id']}/answer", json={"option_index": 1}).json()["status"] == "answered"

    # 2. Simulated HR ~90 + temp 37.9 -> Monitor opens an investigation (not urgent)
    sc = c.post("/demo/scenario/infection_pattern", params={"with_checkin": False}).json()
    inv_id = next(r["investigation_id"] for r in sc["results"] if r["investigation_id"])
    assert not any(a["level"] == "urgent" for a in sc["open_alerts"])

    # 3. Investigation asks for a wound photo, then one follow-up question (max 2 requests)
    reqs = c.get("/patients/sarah/requests").json()
    assert [r["kind"] for r in reqs] == ["photo"]
    c.post(f"/requests/{reqs[0]['id']}/answer", json={"photo_asset": "day3"})
    reqs = c.get("/patients/sarah/requests").json()
    assert [r["kind"] for r in reqs] == ["question"]
    c.post(f"/requests/{reqs[0]['id']}/answer", json={"option_index": 0})
    inv = c.get(f"/investigations/{inv_id}").json()
    assert inv["status"] == "finished" and inv["patient_requests"] == 2
    assert len(inv["requests"]) == 2 and any(s["kind"] == "tool.call" for s in inv["steps"])

    # 4. Evidence summary (3 separated sources, missing evidence), clinician alert, Ahmed task, Sarah next step
    s = inv["summary"]
    assert s["patient_reported"] and s["device_measured"] and "not a diagnosis" in s["ai_interpretation"]
    assert isinstance(s["missing_or_conflicting"], list)
    alerts = c.get("/alerts", params={"role": "clinician", "open_only": True}).json()
    inv_alert = next(a for a in alerts if a["investigation_id"] == inv_id)
    assert inv_alert["level"] == "attention" and inv_alert["assigned_to"] == "dr_ruiz"
    assert c.get(f"/alerts/{inv_alert['id']}").json()["evidence_summary"]["what_changed"]
    assert any(t["category"] == "alerts" for t in c.get("/caregiver/ahmed/tasks").json())
    today = c.get("/patients/sarah/today").json()
    assert today["next_step"]["kind"] == "next_step"

    # 5. Lifecycle: acknowledged (clinician) -> resolved with reason
    assert c.post(f"/alerts/{inv_alert['id']}/ack", json={"actor": "ahmed"}).status_code == 403
    assert c.post(f"/alerts/{inv_alert['id']}/ack", json={"actor": "dr_ruiz"}).json()["state"] == "acknowledged"
    c.post(f"/alerts/{inv_alert['id']}/contacted", json={"actor": "dr_ruiz", "note": "Called Sarah"})
    done = c.post(f"/alerts/{inv_alert['id']}/resolve",
                  json={"actor": "dr_ruiz", "reason": "Seen in clinic, wound swab taken"}).json()
    assert done["state"] == "resolved"

    # 6. Urgent contrast with the LLM switched OFF: breathlessness + SpO2 88 -> urgent alert < 5 s
    c.post("/demo/llm_mode/off")
    try:
        t0 = time.perf_counter()
        sc = c.post("/demo/scenario/urgent_breathless").json()
        assert time.perf_counter() - t0 < 5
        urgent = [a for a in sc["open_alerts"] if a["level"] == "urgent"]
        assert urgent
    finally:
        c.post("/demo/llm_mode/stub")

    # 5b. ... and if nobody acknowledges it within 60 s it escalates to the backup contact
    esc = c.post("/demo/clock/advance", params={"seconds": settings.ack_timeout_s + 1}).json()
    assert urgent[0]["id"] in esc["sweep"]["escalated_alerts"]
    assert c.get(f"/alerts/{urgent[0]['id']}").json()["assigned_to"] == "dr_oncall"

    # 7. Caregiver digest for Ahmed
    d = c.get("/caregiver/ahmed/digest", params={"refresh": True}).json()["digest"]
    assert 0 < len(d["text"].split()) <= 80

    # 8. Medication Agent (rules): a second missed antibiotic dose -> Ahmed task + clinician flag
    two_pm = datetime.combine(clock.now().date(), datetime.min.time()).replace(hour=14).isoformat()
    med = c.post("/medications/dose", json={"med_id": "m5", "scheduled_for": two_pm, "status": "not_taken"}).json()
    assert med["flag"]["caregiver_tasks"] and med["missed_dose_text"]

    # Every agent step and tool call is in the audit log
    kinds = {e["kind"] for e in c.get("/audit", params={"limit": 2000}).json()}
    assert {"agent.step", "tool.call", "evidence.validated", "urgent.fired", "alert.escalated", "digest.created",
            "medication.dose_recorded", "checkin.clarification", "gate.answer"} <= kinds


def test_twin_marks_unknown_and_unreliable(client):
    c = client
    c.post("/demo/scenario/bad_signal")
    t = c.get("/patients/sarah/twin").json()
    assert t["vitals"]["spo2"]["status"] == "unreliable" and t["vitals"]["spo2"]["value"] is None
    c.post("/demo/scenario/no_data")
    t = c.get("/patients/sarah/twin").json()
    assert t["vitals"]["hr"]["status"] == "unknown" and t["vitals"]["hr"]["value"] is None


def test_twin_caregiver_view_hides_categories(client, repo):
    from app import models as m
    row = repo.first(m.SurveillancePlan)
    plan = dict(row.plan)
    plan["caregiver_permissions"] = {"ahmed": {"categories": {"symptoms": True, "alerts": True}}}
    row.plan = plan
    repo.add(row)
    t = client.get("/patients/sarah/twin", params={"role": "caregiver", "member_id": "ahmed"}).json()
    assert "vitals" not in t and "medications" not in t and "wound" not in t
    assert set(t["hidden_categories"]) == {"vitals", "medications", "wound"}


def test_demo_answer_pending_shortcut(client):
    c = client
    sc = c.post("/demo/scenario/infection_pattern").json()  # includes Sarah's check-in
    assert sc["checkin"]["clarification"]
    out = c.post("/demo/answer_pending").json()["answered"]
    assert [a["kind"] for a in out] == ["question", "photo", "question"]
    assert c.get("/demo/status").json()["latest_investigation"]["status"] == "finished"
