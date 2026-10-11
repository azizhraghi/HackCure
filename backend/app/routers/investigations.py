from fastapi import APIRouter, Depends, HTTPException, Query

from .. import audit, requests_service
from .. import models as m
from ..db import Repo, get_repo
from ..agents.investigation_workflow import public as workflow_progress

router = APIRouter(tags=["investigations"])


@router.get("/patients/{patient_id}/agent-metrics")
def agent_metrics(patient_id: str, repo: Repo = Depends(get_repo)):
    """Operational evaluation, separated by execution mode; not medical accuracy."""
    rows = repo.all(m.Investigation, m.Investigation.patient_id == patient_id,
                    order=m.Investigation.started_at.desc(), limit=100)
    modes = {}
    for inv in rows:
        mode = (inv.summary or {}).get("generated_by", "pending")
        group = modes.setdefault(mode, {"cases": 0, "finished": 0, "incomplete": 0,
                                       "tool_calls": 0, "patient_requests": 0, "validation_retries": 0,
                                       "review_issues": 0, "elapsed_seconds": []})
        group["cases"] += 1
        group["finished"] += inv.status == "finished"
        group["incomplete"] += inv.status == "incomplete"
        group["tool_calls"] += inv.tool_calls
        group["patient_requests"] += inv.patient_requests
        group["validation_retries"] += inv.evidence_retries
        group["review_issues"] += len((inv.summary or {}).get("evidence_review", {}).get("issues", []))
        if inv.finished_at:
            group["elapsed_seconds"].append(max(0, (inv.finished_at - inv.started_at).total_seconds()))
    return {"sample_size": len(rows), "by_mode": modes,
            "note": "Elapsed time includes patient waits and the demo clock. Source-review issues are not an accuracy score."}


@router.get("/patients/{patient_id}/requests")
def list_requests(patient_id: str, include_closed: bool = False, repo: Repo = Depends(get_repo)):
    if include_closed:
        return repo.all(m.PatientRequest, m.PatientRequest.patient_id == patient_id,
                        order=m.PatientRequest.created_at.desc(), limit=50)
    return repo.pending_requests(patient_id)


@router.post("/requests/{request_id}/answer")
def answer_request(request_id: str, body: m.RequestAnswer, actor: str = Query("sarah"),
                   repo: Repo = Depends(get_repo)):
    try:
        return requests_service.answer(repo, request_id, body, actor)
    except requests_service.RequestError as e:
        raise HTTPException(e.status, str(e)) from e


@router.get("/investigations/{inv_id}")
def get_investigation(inv_id: str, include_messages: bool = False, repo: Repo = Depends(get_repo)):
    """Investigation evidence, public workflow actions and clinician follow-up."""
    inv = repo.get(m.Investigation, inv_id)
    if inv is None:
        raise HTTPException(404, "unknown investigation")
    out = inv.model_dump(exclude={"state"})
    out["workflow"] = workflow_progress(repo, inv)
    if include_messages:
        out["messages"] = (inv.state or {}).get("messages", [])
    out["requests"] = repo.all(m.PatientRequest, m.PatientRequest.investigation_id == inv_id,
                               order=m.PatientRequest.created_at)
    out["steps"] = [{"at": e.at, "actor": e.actor, "kind": e.kind, "data": e.data}
                    for e in audit.trail(repo, "investigation", inv_id)]
    return out


@router.get("/patients/{patient_id}/investigations")
def list_investigations(patient_id: str, repo: Repo = Depends(get_repo)):
    return [{**i.model_dump(exclude={"state"}), "workflow": workflow_progress(repo, i)} for i in
            repo.all(m.Investigation, m.Investigation.patient_id == patient_id,
                     order=m.Investigation.started_at.desc(), limit=20)]


@router.get("/audit")
def get_audit(patient_id: str = "sarah", ref_type: str | None = None, ref_id: str | None = None, limit: int = 500,
              repo: Repo = Depends(get_repo)):
    return audit.trail(repo, ref_type, ref_id, patient_id, limit)
