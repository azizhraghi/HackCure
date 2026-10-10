"""Recovery Protocol Compiler: documents -> grounded draft plan -> patient confirms -> active plan."""

from app import models as m
from app.agents import protocol
from app.config import settings
from app.routers.chat import plan_context
from app.routers.documents import SAMPLE


def sample(repo):
    return protocol.save_document(repo, "sarah", SAMPLE.name, "application/pdf", SAMPLE.read_bytes())


def fresh_draft(repo, draft):
    repo.s.expire_all()
    return repo.get(m.PlanDraft, draft.id)


def test_pdf_text_extracted(repo):
    doc = sample(repo)
    assert doc.status == "ready" and "Cefuroxime 500 mg" in doc.text


def test_photo_and_unknown_files_are_rejected_clearly(repo):
    photo = protocol.save_document(repo, "sarah", "scan.jpg", "image/jpeg", b"\xff\xd8fake")
    assert photo.status == "unreadable" and "OCR" in photo.error
    weird = protocol.save_document(repo, "sarah", "x.docx", "application/octet-stream", b"PK")
    assert weird.status == "unreadable"


def test_draft_from_sample_is_grounded_and_keeps_safety_settings(repo):
    sample(repo)
    base = repo.plan("sarah")
    draft = fresh_draft(repo, protocol.start_draft(repo, "sarah", []))
    assert draft.status == "ready"
    plan = draft.plan
    assert [x["name"] for x in plan["medications"]] == ["Paracetamol", "Celecoxib", "Pantoprazole", "Enoxaparin", "Cefuroxime"]
    assert not [w for w in draft.warnings if w["level"] == "high"]
    assert [a["day_offset"] for a in plan["appointments"]] == [6, 8, 12]
    for key in protocol.SAFETY_KEYS:  # never taken from the AI
        assert plan[key] == base[key]


def test_hallucinated_medication_or_dose_is_flagged():
    text = "Paracetamol 1 g at 08:00. Allergy: penicillin."
    ex = m.ProtocolExtraction(medications=[
        m.ExtractedMedication(name="Paracetamol", dose="2 g", times=["08:00"]),
        m.ExtractedMedication(name="Tramadol", dose="50 mg", times=["08:00"]),
        m.ExtractedMedication(name="Amoxicillin", dose="500 mg", times=["08:00"]),
        m.ExtractedMedication(name="Paracetamol", dose="1 g", times=["08:00", "14:00", "20:00"], times_inferred=True,
                              frequency_text="three times daily"),
    ], allergies=["Penicillin (rash)"])
    msgs = [(w["item"], w["message"]) for w in protocol.ground(ex, text, None)]
    assert any("Paracetamol 2 g" == i and "not found word-for-word" in t for i, t in msgs)
    assert any("Tramadol" in i and "name not found" in t for i, t in msgs)
    assert any("Amoxicillin" in i and "allergy" in t for i, t in msgs)
    assert any("proposed by the AI" in t for _, t in msgs)


def test_confirm_makes_the_draft_the_active_plan(repo):
    sample(repo)
    before = repo.plan("sarah")
    draft = fresh_draft(repo, protocol.start_draft(repo, "sarah", []))
    protocol.confirm(repo, draft.id, "sarah")
    repo.s.expire_all()
    plan = repo.plan("sarah")
    assert plan["wound_photo_schedule"] == before["wound_photo_schedule"]  # care-team schedule carries over
    assert plan["version"] == before["version"] + 1 and plan["document_info"]["surgeon"] == "Dr. Elena Ruiz"
    assert repo.get(m.PlanDraft, draft.id).status == "confirmed"
    assert "penicillin" in repo.patient("sarah").allergies
    assert "from the patient's documents" in plan_context(repo, "sarah")


def test_llm_down_fails_cleanly(repo, monkeypatch):
    monkeypatch.setattr(settings, "llm_mode", "off")
    sample(repo)
    draft = fresh_draft(repo, protocol.start_draft(repo, "sarah", []))
    assert draft.status == "failed" and draft.error


def test_api_upload_analyze_confirm(client):
    r = client.post("/patients/sarah/documents",
                    files=[("files", (SAMPLE.name, SAMPLE.read_bytes(), "application/pdf")),
                           ("files", ("photo.png", b"\x89PNG", "image/png"))])
    docs = r.json()
    assert r.status_code == 200 and [d["status"] for d in docs] == ["ready", "unreadable"]
    draft = client.post("/patients/sarah/plan-drafts", json={"document_ids": [docs[0]["id"]]}).json()
    assert draft["status"] == "ready"  # inline in tests; poll GET /plan-drafts/{id} in the app
    assert client.get(f"/plan-drafts/{draft['id']}").json()["plan"]["medications"]
    ok = client.post(f"/plan-drafts/{draft['id']}/confirm", json={"actor": "sarah"}).json()
    assert ok["ok"] and len(ok["medications"]) == 5
    assert client.post(f"/plan-drafts/{draft['id']}/confirm", json={"actor": "sarah"}).status_code == 409


def test_no_documents_is_422(client):
    assert client.post("/patients/sarah/plan-drafts", json={}).status_code == 422


def test_day_month_swap_is_corrected_from_the_document():
    text = "Date of surgery: 06/10/2026    Date of discharge: 08/10/2026  Physiotherapy: 14/10/2026 at 15:00."
    ex = m.ProtocolExtraction(surgery_date="2026-06-10", discharge_date="2026-08-10",
                              appointments=[m.ExtractedAppointment(title="Physiotherapy", date="2026-10-14", time="15:00"),
                                            m.ExtractedAppointment(title="Ghost visit", date="2026-11-30")])
    notes = protocol.fix_dates(ex, text)
    assert ex.surgery_date == "2026-10-06" and ex.discharge_date == "2026-10-08"
    assert ex.appointments[0].date == "2026-10-14"
    assert any(n["item"] == "Discharge date" and "corrected" in n["message"] for n in notes)
    assert any(n["item"] == "Ghost visit" and "not found" in n["message"] for n in notes)
    plan = protocol.build_plan({}, ex, [])
    assert plan["appointments"][0]["day_offset"] == 6
