from fastapi import APIRouter, Depends, HTTPException

from .. import medication_guide
from .. import models as m
from ..agents import medication
from ..db import Repo, get_repo

router = APIRouter(tags=["medications"])


@router.get("/patients/{patient_id}/medications")
def medications(patient_id: str, repo: Repo = Depends(get_repo)):
    return {"plan": repo.plan(patient_id).get("medications", []),
            "today": medication.day_schedule(repo, patient_id)}


@router.post("/medications/dose")
def record_dose(body: m.DoseIn, repo: Repo = Depends(get_repo)):
    try:
        return medication.record_dose(repo, body.patient_id, body.med_id, body.scheduled_for, body.status, body.actor)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e


@router.get("/patients/{patient_id}/medication-guide")
def guide(patient_id: str, lang: str = "en", repo: Repo = Depends(get_repo)):
    """Possible side effects of today's medicines, with reassurance and when to call the care team."""
    if repo.patient(patient_id) is None:
        raise HTTPException(404, "unknown patient")
    return medication_guide.for_plan(repo.plan(patient_id), lang)
