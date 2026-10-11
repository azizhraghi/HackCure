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


@router.get("/patients/{patient_id}/wound-photos/{observation_id}")
def wound_photo_detail(patient_id: str, observation_id: str, repo: Repo = Depends(get_repo)):
    o = repo.get(m.Observation, observation_id)
    if o is None or o.patient_id != patient_id or o.type != "photo":
        raise HTTPException(404, "unknown wound photo")
    return wounds.public(o)


@router.post("/patients/{patient_id}/wound-photos/{observation_id}/review")
def rerun_wound_review(patient_id: str, observation_id: str, repo: Repo = Depends(get_repo)):
    """Run the code analysis and the vision reading again (e.g. after adding an LLM key)."""
    from ..integrations import d1_wound
    o = repo.get(m.Observation, observation_id)
    data = d1_wound.photo_bytes(o.value.get("url")) if o and o.patient_id == patient_id else None
    if data is None:
        raise HTTPException(404, "unknown wound photo")
    d1_wound.analyze(repo, o, data)
    d1_wound.vision_review(repo, o, data)
    d1_wound.decide(repo, o)
    return wounds.public(repo.get(m.Observation, observation_id))


@router.get("/patients/{patient_id}/wound-status")
def wound_status(patient_id: str, repo: Repo = Depends(get_repo)):
    """Is a dressing-change photo due now? (the care plan's windows; never a prompt to uncover the wound)."""
    if repo.patient(patient_id) is None:
        raise HTTPException(404, "unknown patient")
    return wound_photos.eligibility(repo, patient_id)
