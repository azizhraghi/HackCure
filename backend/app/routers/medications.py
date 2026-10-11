import base64
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from PIL import Image, UnidentifiedImageError

from .. import medication_guide, clock
from .. import models as m
from ..agents import medication
from ..db import Repo, get_repo

router = APIRouter(tags=["medications"])


@router.get("/patients/{patient_id}/medications")
def medications(patient_id: str, repo: Repo = Depends(get_repo)):
    if repo.patient(patient_id) is None:
        raise HTTPException(404, "unknown patient")
    return {"plan": repo.plan(patient_id).get("medications", []),
            "today": medication.day_schedule(repo, patient_id),
            "now": clock.now().isoformat()}


@router.post("/patients/{patient_id}/medications/{med_id}/photo")
async def package_photo(patient_id: str, med_id: str, file: UploadFile = File(...), repo: Repo = Depends(get_repo)):
    med = medication.plan_med(repo.plan(patient_id), med_id)
    if not med:
        raise HTTPException(404, "medicine is not in the confirmed plan")
    data = await file.read(2 * 1024 * 1024 + 1)
    if len(data) > 2 * 1024 * 1024:
        raise HTTPException(413, "Use a package photo smaller than 2 MB")
    try:
        with Image.open(io.BytesIO(data)) as im:
            if im.width * im.height > 16_000_000:
                raise HTTPException(413, "Photo dimensions are too large")
            im.thumbnail((1000, 1000))
            output = io.BytesIO()
            im.convert("RGB").save(output, format="JPEG", quality=85)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise HTTPException(422, "Use a readable JPEG, PNG or WebP photo") from exc
    repo.add(m.Observation(patient_id=patient_id, type="medication_photo", source="patient",
                          value={"medication_key": medication.medication_key(med),
                                 "data_url": "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode()}))
    return medication.photo(repo, patient_id, med)


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
