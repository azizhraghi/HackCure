import base64

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from .. import models as m
from .. import clock, requests_service, wound_photos, wounds
from ..db import Repo, get_repo

router = APIRouter(tags=["wounds"])


@router.post("/patients/{patient_id}/wound-photos")
async def upload_wound_photo(patient_id: str, file: UploadFile = File(...), actor: str = "sarah",
                             dressing_change_confirmed: bool = Form(False), repo: Repo = Depends(get_repo)):
    """A wound photo from the app camera, only inside a dressing-change window permitted by the care plan
    (app/wound_photos.py). Measured by code and compared with the reference (first) photo.
    It answers the window's photo request, so a waiting investigation resumes."""
    if repo.patient(patient_id) is None:
        raise HTTPException(404, "unknown patient")
    data = await file.read(wounds.MAX_BYTES + 1)
    pending = next((r for r in repo.pending_requests(patient_id) if r.kind == "photo" and r.expires_at > clock.now()),
                   None)
    if pending is None:  # no request yet: open the current window's request (refused outside a window)
        opened = wound_photos.request(repo, patient_id)
        if opened["status"] != "requested":
            raise HTTPException(409, opened["reason"])
        pending = repo.get(m.PatientRequest, opened["request_id"])
    try:
        body = m.RequestAnswer(photo_base64=base64.b64encode(data).decode(),
                               dressing_change_confirmed=dressing_change_confirmed)
        out = requests_service.answer(repo, pending.id, body, actor)
        obs = repo.get(m.Observation, out["request"].answer_observation_id)
    except requests_service.RequestError as e:
        raise HTTPException(e.status, str(e)) from e
    return {**wounds.public(obs), "answered_request_id": pending.id}


@router.get("/patients/{patient_id}/wound-photos")
def list_wound_photos(patient_id: str, repo: Repo = Depends(get_repo)):
    photos = repo.observations(patient_id, "photo", newest_first=True, limit=20)
    ref = wounds.reference(repo, patient_id)
    return {"reference": wounds.public(ref) if ref else None, "photos": [wounds.public(o) for o in photos]}
