from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from .. import models as m
from ..agents import protocol
from ..db import Repo, get_repo

router = APIRouter(tags=["documents"])

MAX_BYTES = 20 * 1024 * 1024
SAMPLE = Path(__file__).resolve().parents[2] / "seed" / "documents" / "sarah_discharge_summary.pdf"


def _doc_out(d: m.Document) -> dict:
    return {**d.model_dump(exclude={"text"}), "chars": len(d.text)}


def _patient(repo: Repo, patient_id: str):
    if repo.patient(patient_id) is None:
        raise HTTPException(404, "unknown patient")


@router.post("/patients/{patient_id}/documents")
async def upload_documents(patient_id: str, files: list[UploadFile] = File(...), repo: Repo = Depends(get_repo)):
    """Upload discharge summaries / prescriptions (PDF or text). Text is extracted immediately."""
    _patient(repo, patient_id)
    out = []
    for f in files:
        data = await f.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise HTTPException(413, f"{f.filename} is larger than 20 MB")
        out.append(_doc_out(protocol.save_document(repo, patient_id, f.filename or "document", f.content_type or "", data)))
    return out


@router.post("/patients/{patient_id}/documents/sample")
def upload_sample(patient_id: str, repo: Repo = Depends(get_repo)):
    """Demo: add the FICTIONAL sample discharge summary as if the patient uploaded it."""
    _patient(repo, patient_id)
    return _doc_out(protocol.save_document(repo, patient_id, SAMPLE.name, "application/pdf", SAMPLE.read_bytes()))


@router.get("/patients/{patient_id}/documents")
def list_documents(patient_id: str, repo: Repo = Depends(get_repo)):
    return [_doc_out(d) for d in repo.all(m.Document, m.Document.patient_id == patient_id, order=m.Document.created_at)]


@router.post("/patients/{patient_id}/plan-drafts")
def create_draft(patient_id: str, body: m.PlanDraftIn, repo: Repo = Depends(get_repo)):
    """'Analyze with AI': drafts a care plan from the documents (poll GET /plan-drafts/{id}).
    engine "agent" = D3 protocol agent, "d2" = Developer 2 compiler; both are grounded by code and confirmed by the patient."""
    _patient(repo, patient_id)
    try:
        if body.engine == "d2":
            from ..integrations import d2_bridge
            draft = d2_bridge.start_draft(repo, patient_id, body.document_ids)
        else:
            draft = protocol.start_draft(repo, patient_id, body.document_ids)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    repo.s.expire_all()
    return protocol.summary(repo.get(m.PlanDraft, draft.id))


@router.get("/plan-drafts/{draft_id}")
def get_draft(draft_id: str, repo: Repo = Depends(get_repo)):
    draft = repo.get(m.PlanDraft, draft_id)
    if draft is None:
        raise HTTPException(404, "unknown draft")
    from ..agents.plan_clarification import prepare
    return {**protocol.summary(draft), "clarifications": prepare(repo, draft)}


@router.post("/plan-drafts/{draft_id}/clarification-request")
def request_clarification(draft_id: str, body: m.ActorBody, repo: Repo = Depends(get_repo)):
    from ..agents.plan_clarification import request_review
    draft = repo.get(m.PlanDraft, draft_id)
    if draft is None:
        raise HTTPException(404, "unknown draft")
    try:
        return request_review(repo, draft, body.actor)
    except ValueError as exc:
        raise HTTPException(403, str(exc)) from exc


@router.post("/plan-drafts/{draft_id}/confirm")
def confirm_draft(draft_id: str, body: m.ActorBody, repo: Repo = Depends(get_repo)):
    """The patient reviewed the draft (Review step): it becomes the active care plan."""
    try:
        row = protocol.confirm(repo, draft_id, body.actor)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(409, str(e)) from e
    return {"ok": True, "plan_id": row.id, "medications": row.plan.get("medications", [])}
