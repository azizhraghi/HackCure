"""Behavioral checks for graph orchestration and the human follow-up boundary."""

import json
from datetime import timedelta

from app import clock, llm, monitor
from app import models as m
from app.agents import investigation
from app.agents.investigation_graph import build_graph
from app.config import settings
from tests.test_step7_investigation import start_infection, drive


def test_graph_collects_context_and_records_pause_then_clinician_handover(client, repo):
    inv = start_infection(repo)
    body = client.get(f"/investigations/{inv.id}").json()
    assert body["workflow"]["engine"] == "langgraph"
    assert body["workflow"]["stage"] == "waiting_patient"
    assert body["workflow"]["context_sources"][0]["kind"] == "care_plan"
    assert body["workflow"]["followup"] is None
    assert client.get("/patients/sarah/today").json()["investigation_progress"]["phase"] == "evidence"
    inv = drive(repo, inv.id)
    body = client.get(f"/investigations/{inv.id}").json()
    assert inv.status == "finished" and inv.summary["orchestrator"] == "langgraph"
    assert body["workflow"]["stage"] == "await_clinician"
    assert body["workflow"]["followup"]["closed"] is False
    stages = [e["stage"] for e in body["workflow"]["events"]]
    assert {"collect_context", "read_evidence", "request_evidence", "waiting_patient", "validate_report", "await_clinician"} <= set(stages)
    # A completed report is not a completed clinical case.
    today = client.get("/patients/sarah/today").json()["investigation_progress"]
    assert today["report_ready"] and today["phase"] == "followup" and not today["closed"]


def test_recorded_d1_results_are_supplementary_with_source_ids(client, repo):
    result = client.post("/patients/sarah/rehab/demo", json={"kind": "occluded", "pain_eva": 3}).json()
    inv = drive(repo, start_infection(repo).id)
    context = inv.state["context"]
    assert context["d1_status"] == "available"
    finding = inv.summary["supplementary_findings"][0]
    assert finding["observation_id"] == result["observation_id"]
    assert finding["assessment"]["status"] == "abstained"
    assert finding["simulated"] is True
    assert "not a diagnosis" in finding["note"]
    assert any(s["id"] == result["observation_id"] for s in inv.summary["context_sources"])
    assert not any("no recorded results" in x for x in inv.summary["missing_or_conflicting"])


def test_followup_state_changes_without_calling_the_model(client, repo, monkeypatch):
    inv = drive(repo, start_infection(repo).id)
    monkeypatch.setattr(llm, "chat_tools", lambda *a, **k: (_ for _ in ()).throw(AssertionError("LLM used for follow-up")))
    aid = inv.alert_id
    actor = {"actor": "dr_ruiz"}
    assert client.post(f"/alerts/{aid}/ack", json=actor).status_code == 200
    assert client.get(f"/investigations/{inv.id}").json()["workflow"]["followup"]["state"] == "acknowledged"
    client.post(f"/alerts/{aid}/contacted", json=actor)
    client.post(f"/alerts/{aid}/action", json={**actor, "note": "Fictional clinician action recorded"})
    assert client.post(f"/alerts/{aid}/resolve", json={**actor, "reason": "Reviewed", "verification_id": "missing"}).status_code != 200
    obs = client.post(f"/demo/alerts/{aid}/followup-evidence", json=actor).json()
    body = {**actor, "summary": "Synthetic follow-up reviewed in the demo", "observation_ids": [obs["id"]]}
    client.post(f"/alerts/{aid}/verify", json={**body, "outcome": "needs_review"})
    assert client.get(f"/investigations/{inv.id}").json()["workflow"]["followup"]["state"] == "action_taken"
    verification = client.post(f"/alerts/{aid}/verify", json={**body, "outcome": "resolved"}).json()
    assert not client.get(f"/investigations/{inv.id}").json()["workflow"]["followup"]["closed"]
    assert client.post(f"/alerts/{aid}/resolve", json={**actor, "reason": "Fictional follow-up completed", "verification_id": verification["id"]}).status_code == 200
    workflow = client.get(f"/investigations/{inv.id}").json()["workflow"]
    assert workflow["followup"]["closed"]
    assert client.get("/patients/sarah/today").json()["investigation_progress"]["phase"] == "closed"


def test_unavailable_d1_is_unknown_not_normal(repo):
    inv = drive(repo, start_infection(repo).id)
    assert inv.state["context"]["d1_status"] == "unknown"
    assert inv.summary["supplementary_findings"] == []
    assert any("D1" in x and "no recorded results" in x for x in inv.summary["missing_or_conflicting"])


def test_failed_core_tool_cannot_satisfy_report_requirements():
    messages = [{"role": "tool", "name": "get_medication_context", "content": json.dumps({"error": "unavailable"})}]
    assert "get_medication_context" in investigation._missing_required(messages)


def test_unavailable_wound_comparison_is_explicit_in_demo_report():
    from app.llm_stubs import _findings
    report = _findings([("compare_wound_photos", {"available": False, "reason": "image cannot be measured"})], {}, None)
    assert any("Wound comparison unavailable" in x and "image cannot be measured" in x
               for x in report["missing_or_conflicting"])
    assert "redness area" not in report["what_changed"]


def test_budget_cannot_turn_missing_required_evidence_into_complete_report(repo, monkeypatch):
    monkeypatch.setattr(settings, "max_tool_calls", 0)
    inv = monitor.request_investigation(repo, "sarah", {"signals": []})
    repo.refresh(inv)
    assert inv.status == "incomplete" and inv.alert_id
    assert "Required evidence" in inv.summary["ai_interpretation"]


def test_repeated_non_tool_replies_terminate_and_nudge_count_is_persisted(repo, monkeypatch):
    monkeypatch.setattr(llm, "chat_tools", lambda *a, **k: llm.Reply(content="Just text"))
    inv = monitor.request_investigation(repo, "sarah", {"signals": []})
    repo.refresh(inv)
    assert inv.status == "incomplete" and inv.state["nudges"] == 3


def test_graph_has_explicit_request_validation_and_human_handover_nodes(repo):
    inv = repo.add(m.Investigation(patient_id="sarah", deadline=clock.now() + timedelta(seconds=120)))
    graph = build_graph(repo, inv).get_graph()
    assert {"collect_context", "safety_gate", "assess_evidence", "read_evidence", "request_evidence",
            "validate_report", "await_clinician"} <= set(graph.nodes)


def test_patient_progress_does_not_expose_clinician_report_or_tool_trace(client, repo):
    inv = drive(repo, start_infection(repo).id)
    progress = client.get("/patients/sarah/today").json()["investigation_progress"]
    assert progress["id"] == inv.id
    assert not {"summary", "messages", "context_sources", "events", "steps"} & set(progress)
