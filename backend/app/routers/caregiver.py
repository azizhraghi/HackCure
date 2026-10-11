from fastapi import APIRouter, Depends, HTTPException

from .. import audit, clock
from .. import models as m
from ..agents import digest
from ..db import Repo, get_repo
from ..notifications import caregiver_allowed

router = APIRouter(tags=["caregiver"])


def _caregiver(repo: Repo, caregiver_id: str) -> m.CareTeamMember:
    cg = repo.member(caregiver_id)
    if cg is None or cg.role != "caregiver":
        raise HTTPException(404, "unknown caregiver")
    return cg


@router.get("/caregiver/{caregiver_id}/digest")
def get_digest(caregiver_id: str, refresh: bool = False, repo: Repo = Depends(get_repo)):
    """Latest evening digest (refresh=true generates a new one now)."""
    cg = _caregiver(repo, caregiver_id)
    d = None if refresh else repo.first(m.Digest, m.Digest.caregiver_id == caregiver_id, order=m.Digest.created_at.desc())
    plan_row = repo.first(m.SurveillancePlan, m.SurveillancePlan.patient_id == cg.patient_id, order=m.SurveillancePlan.created_at.desc())
    if d and plan_row and plan_row.created_at > d.created_at:
        d = None
    if d is None:
        d = digest.generate(repo, cg.patient_id, caregiver_id)
    tasks = [repo.get(m.CaregiverTask, t) for t in d.task_ids]
    return {"digest": d, "tasks": [t for t in tasks if t and caregiver_allowed(repo.plan(cg.patient_id), caregiver_id, t.category)],
            "shared_categories": digest.allowed_categories(repo.plan(cg.patient_id), caregiver_id)}


@router.get("/caregiver/{caregiver_id}/tasks")
def list_tasks(caregiver_id: str, open_only: bool = True, repo: Repo = Depends(get_repo)):
    cg = _caregiver(repo, caregiver_id)
    where = [m.CaregiverTask.caregiver_id == caregiver_id]
    if open_only:
        where.append(m.CaregiverTask.status == "open")
    return [t for t in repo.all(m.CaregiverTask, *where, order=m.CaregiverTask.created_at.desc())
            if caregiver_allowed(repo.plan(cg.patient_id), caregiver_id, t.category)]


@router.post("/caregiver/tasks/{task_id}/done")
def task_done(task_id: str, body: m.ActorBody, repo: Repo = Depends(get_repo)):
    t = repo.get(m.CaregiverTask, task_id)
    if t is None or t.caregiver_id != body.actor:
        raise HTTPException(404, "unknown task for this caregiver")
    if not caregiver_allowed(repo.plan(t.patient_id), body.actor, t.category):
        raise HTTPException(403, "this task category is not shared")
    t.status, t.done_at = "done", clock.now()
    repo.add(t)
    audit.log(repo, t.patient_id, body.actor, "caregiver_task.done", {"text": t.text, "note": body.note}, "task", t.id)
    return t
