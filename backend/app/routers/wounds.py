import base64

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from .. import models as m
from .. import requests_service, wounds
from ..db import Repo, get_repo

router = APIRouter(tags=["wounds"])


@router.post("/patients/{patient_id}/wound-photos")
async def upload_wound_photo(patient_id: str, file: UploadFile = File(...), actor: str = "sarah",
                             repo: Repo = Depends(get_repo)):
    """A wound photo from the app camera. Measured by code and compared with the reference (first) photo.
    If the care-team agent is waiting for a photo, this answers its request (the investigation resumes)."""
    if repo.patient(patient_id) is None:
        raise HTTPException(404, "unknown patient")
    data = await file.read(wounds.MAX_BYTES + 1)
    pending = next((r for r in repo.pending_requests(patient_id) if r.kind == "photo"), None)
    try:
        if pending:
            body = m.RequestAnswer(photo_base64=base64.b64encode(data).decode())
            out = requests_service.answer(repo, pending.id, body, actor)
            obs = repo.get(m.Observation, out["request"].answer_observation_id)
        else:
            obs = wounds.save_photo(repo, patient_id, data, "caregiver_on_behalf" if actor != patient_id else "patient")
    except requests_service.RequestError as e:
        raise HTTPException(e.status, str(e)) from e
    except ValueError as e:
        raise HTTPException(413, str(e)) from e
    return {**wounds.public(obs), "answered_request_id": pending.id if pending else None}


@router.get("/patients/{patient_id}/wound-photos")
def list_wound_photos(patient_id: str, repo: Repo = Depends(get_repo)):
    photos = repo.observations(patient_id, "photo", newest_first=True, limit=20)
    ref = wounds.reference(repo, patient_id)
    return {"reference": wounds.public(ref) if ref else None, "photos": [wounds.public(o) for o in photos]}
