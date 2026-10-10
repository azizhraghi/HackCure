from fastapi import APIRouter, Depends, HTTPException

from .. import models as m
from .. import monitor
from ..db import Repo, get_repo

router = APIRouter(tags=["observations"])


@router.post("/observations")
def post_observation(body: m.ObservationIn, repo: Repo = Depends(get_repo)):
    """Device (ESP32 / simulator) or app readings. Runs the Monitor synchronously (no LLM on this path)."""
    if repo.patient(body.patient_id) is None:
        raise HTTPException(404, "unknown patient")
    obs, result = monitor.ingest(repo, body)
    return {"observation": obs, "monitor": result}


@router.get("/patients/{patient_id}/observations")
def list_observations(patient_id: str, type: str | None = None, limit: int = 200, repo: Repo = Depends(get_repo)):
    return repo.observations(patient_id, type, newest_first=True, limit=limit)
