from fastapi import APIRouter, Depends, HTTPException

from .. import models as m
from ..agents import checkin
from ..db import Repo, get_repo

router = APIRouter(tags=["checkin"])


@router.post("/checkin")
def submit_checkin(body: m.CheckinIn, repo: Repo = Depends(get_repo)):
    """The app's check-in form. Returns an optional single clarification question (answer it via
    POST /requests/{id}/answer). status == "urgent" means a red flag stopped the check-in."""
    if repo.patient(body.patient_id) is None:
        raise HTTPException(404, "unknown patient")
    return checkin.submit(repo, body)
