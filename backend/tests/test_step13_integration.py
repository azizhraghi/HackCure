"""D1 + D2 + D3 on one backend: the bridges in app/integrations (offline; D2's LLM step is replaced by a fixed
extraction so the mapping, grounding, safety graph and activation are tested without a network)."""

import pytest

from app import models as m
from app.ai.graphs import protocol_graph as d2_protocol
from app.ai.rag import vectorstore
from app.ai.rag.retriever import Actor, ScopedRetriever
from app.integrations import d1_bridge, d2_bridge
from app.routers import documents as doc_router
from app.schemas.protocol import ExtractedProtocol


def sarah_d2(extra_meds=()) -> ExtractedProtocol:
    """What D2A returns for the sample discharge summary (fixed, instead of a live LLM)."""
    med = lambda dci, raw, freq, n, cls, days=None: {  # noqa: E731
        "dci": dci, "dosage_raw": raw, "frequency_raw": freq, "frequency_per_day": n, "drug_class": cls,
        "duration_days": days, "route": "oral", "confidence": 0.95}
    return ExtractedProtocol.model_validate({
        "document_type": "fiche_sortie", "patient_lastname": "Miller", "patient_firstname": "Sarah",
        "patient_age": 64, "patient_sex": "F", "surgery_type": "Total knee replacement, RIGHT knee",
        "surgery_date": "06/10/2026", "discharge_date": "08/10/2026", "prescriber": "Dr. Elena Ruiz",
        "known_allergies": ["penicillin"],
        "medications": [med("Paracetamol", "1 g", "at 08:00, 14:00 and 20:00", 3, "analgesic"),
                        med("Celecoxib", "200 mg", "once daily at 09:00 with food", 1, "AINS COX-2"),
                        med("Enoxaparin", "40 mg", "once daily at 20:00", 1, "HBPM", 14),
                        med("Cefuroxime", "500 mg", "three times daily", 3, "antibiotic", 7), *extra_meds],
        "physical_restrictions": ["No driving for at least 4 weeks."],
        "followup_appointments": [{"description": "Staple removal", "timing": "J+14", "type": "nurse"}],
        "global_confidence": 0.95,
    })


@pytest.fixture
def d2_offline(monkeypatch, tmp_path):
    state = {"extraction": sarah_d2()}

    class FakeGraph:
        def invoke(self, s):
            return {**s, "extracted_data": state["extraction"], "errors": []}
    monkeypatch.setattr(d2_protocol, "protocol_graph", FakeGraph())
    monkeypatch.setattr(vectorstore, "VECTORSTORE_PATH", str(tmp_path / "vs"))
    d2_bridge._indexed.clear()
    return state


def test_d2_engine_drafts_a_grounded_plan_that_the_patient_confirms(client, repo, d2_offline):
    d2_offline["extraction"] = sarah_d2([{"dci": "Amoxicillin", "dosage_raw": "1 g", "frequency_raw": "twice daily",
                                          "frequency_per_day": 2, "confidence": 0.9}])
    client.post("/patients/sarah/documents/sample")
    draft = client.post("/patients/sarah/plan-drafts", json={"engine": "d2"}).json()
    assert draft["status"] == "ready" and draft["mode"].startswith("d2/")
    meds = {x["name"]: x for x in draft["plan"]["medications"]}
    assert meds["Paracetamol"]["times"] == ["08:00", "14:00", "20:00"] and not meds["Paracetamol"]["times_inferred"]
    assert meds["Cefuroxime"]["times_inferred"]  # "three times daily": proposed times, flagged for review
    text = " ".join(w["message"] for w in draft["warnings"])
    assert "D2 safety check (allergy)" in text and "D2 safety check (drug_interaction)" in text  # English names
    assert "name not found" in text  # code grounding: Amoxicillin is not in the document
    assert draft["plan"]["clinical_profile"]["patient_age"] == 64
    before = repo.plan("sarah")
    assert client.post(f"/plan-drafts/{draft['id']}/confirm", json={"actor": "sarah"}).status_code == 200
    repo.s.expire_all()
    plan = repo.plan("sarah")
    assert plan["version"] == before["version"] + 1 and plan["wound_photo_schedule"] == before["wound_photo_schedule"]
    doc = client.get("/patients/sarah/d2-document").json()["extraction"]
    assert doc["patient_age"] == 64 and doc["surgery_date"] == repo.patient("sarah").surgery_date.strftime("%d/%m/%Y")


def test_d2_document_for_d1_without_a_d2_plan(client, repo):
    doc = client.get("/patients/sarah/d2-document").json()["extraction"]
    assert doc["medications"] and doc["surgery_date"] and doc["known_allergies"] == repo.patient("sarah").allergies


def test_v1_checkin_reaches_the_d3_safety_lane(client, repo):
    r = client.post("/v1/checkin", json={"patient_id": "sarah", "pain": 4, "fatigue": 3, "mobility": 5,
                                         "other_symptoms": ["calf_pain"]}).json()
    assert r["status"] == "EMERGENCY" and r["recorded"]["status"] == "urgent"
    assert any(a.level == "urgent" for a in repo.open_alerts("sarah"))
    unknown = client.post("/v1/checkin", json={"patient_id": "nobody", "pain": 1, "fatigue": 1, "mobility": 9}).json()
    assert unknown["recorded"] is None


def test_v1_chat_urgent_gate_and_patient_scoped_retrieval(client, repo, d2_offline):
    r = client.post("/v1/chat", json={"patient_id": "sarah", "messages": [{"role": "user", "content": "I fainted and I am short of breath"}]})
    assert r.json()["escalate"] and r.json()["citations"] == ["urgent_rules"]
    assert any(a.level == "urgent" for a in repo.open_alerts("sarah"))
    r = client.post("/v1/chat", json={"patient_id": "sarah", "messages": [{"role": "user", "content": "When do I take paracetamol?"}]})
    assert r.status_code == 200
    from langchain_core.documents import Document
    vectorstore.add_documents_to_store([Document(page_content="Paracetamol for another patient",
                                                 metadata={"access_scope": "medications", "patient_id": "other"})], False)
    docs = ScopedRetriever().retrieve("paracetamol", Actor(role="patient", patient_id="sarah"), k=20)
    assert docs and all(d.metadata.get("patient_id") in (None, "sarah") for d in docs)
    assert any("Paracetamol" in d.page_content for d in docs)


def test_d1_parts_are_honest_offline(client, repo):
    assert client.get("/patients/sarah/expected-recovery").json()["status"] == "unavailable"  # needs a live LLM
    fc = client.get("/patients/sarah/twin-forecast").json()
    assert fc["status"] == "ok" and set(fc["forecasts"]) == {"hr", "spo2"}
    for f in fc["forecasts"]["hr"]:
        assert f["status"] in ("available", "abstained") and (f["status"] == "available" or f["limitations"])
    st = client.get("/integration/status").json()
    assert st["d1"]["package"] and st["d2_langchain_provider"] == "offline"


def test_d1_card_from_a_ready_trajectory(repo, monkeypatch):
    class Traj:
        generated_by = "test"

        def home_screen(self, surgery_date, on):
            return {"day": (on - surgery_date).days, "message": "Normal day"}
    doc = d2_bridge.d2_document(repo, "sarah")
    key = repr(sorted(doc["extraction"].items(), key=str))
    monkeypatch.setitem(d1_bridge._jobs, "sarah", {"status": "ready", "key": key, "trajectory": Traj()})
    out = d1_bridge.expected_today(repo, "sarah")
    assert out["status"] == "ready" and out["card"]["message"] == "Normal day"
