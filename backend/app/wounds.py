"""Wound photos: store the image, measure it (app/wound_image.py), compare with the reference photo."""

from pathlib import Path

from . import audit
from . import models as m
from .db import Repo
from .wound_image import analyze, compare

BACKEND_DIR = Path(__file__).resolve().parent.parent
UPLOADS = BACKEND_DIR / "uploads"
DEMO_DIR = BACKEND_DIR / "seed" / "photos"
DEMO_PHOTOS = {"day1", "day2", "day3"}
MAX_BYTES = 12 * 1024 * 1024


def reference(repo: Repo, patient_id: str) -> m.Observation | None:
    """The first wound photo after surgery is the baseline every new photo is compared with."""
    return repo.first(m.Observation, m.Observation.patient_id == patient_id, m.Observation.type == "photo",
                      order=m.Observation.measured_at)


def save_photo(repo: Repo, patient_id: str, data: bytes, source: str = "patient", asset: str | None = None,
               request_id: str | None = None, extra: dict | None = None) -> m.Observation:
    if len(data) > MAX_BYTES:
        raise ValueError("photo larger than 12 MB")
    analysis = analyze(data)
    if asset:
        url, label, simulated = f"/static/photos/{asset}.jpg", asset, True
    else:
        UPLOADS.mkdir(exist_ok=True)
        name = f"{m.new_id('img')}.jpg"
        (UPLOADS / name).write_bytes(data)
        url, label, simulated = f"/uploads/{name}", "photo", False
    ref = reference(repo, patient_id)
    comparison = compare(ref.value.get("analysis") if ref else None, analysis) if ref else \
        {"available": False, "reason": "first photo: it becomes the reference"}
    value = {"url": url, "label": label, "asset": asset, "analysis": analysis, "comparison": comparison,
             "reference_id": ref.id if ref else None, "reference_url": ref.value.get("url") if ref else None}
    if request_id:
        value["request_id"] = request_id
    value.update(extra or {})
    quality = "good" if analysis["quality"] == "good" else analysis["quality"]
    obs = repo.add(m.Observation(patient_id=patient_id, type="photo", source=source, value=value, quality=quality,
                                 simulated=simulated))
    audit.log(repo, patient_id, "code:wound_image", "wound_photo.measured",
              {"quality": analysis["quality"], "problems": analysis.get("problems"), "comparison": comparison},
              "observation", obs.id)
    from .integrations import d1_wound  # D1-F: OpenCV analysis + overlay now, vision-LLM reading in the runner
    d1_wound.process(repo, obs, data)
    return repo.get(m.Observation, obs.id) or obs


def demo_bytes(asset: str) -> bytes:
    if asset not in DEMO_PHOTOS:
        raise ValueError("unknown demo photo")
    return (DEMO_DIR / f"{asset}.jpg").read_bytes()


def public(o: m.Observation) -> dict:
    v = o.value
    return {"observation_id": o.id, "at": o.measured_at.isoformat(), "url": v.get("url"), "label": v.get("label"),
            "simulated": o.simulated, "quality": o.quality, "analysis": v.get("analysis"),
            "comparison": v.get("comparison"), "reference_url": v.get("reference_url"),
            "d1": v.get("d1"), "vision_review": v.get("vision_review"), "review_alert_id": v.get("review_alert_id"),
            "request_id": v.get("request_id"), "dressing_change_confirmed": v.get("dressing_change_confirmed"),
            "initiated_by": v.get("initiated_by", "care_plan_window"), "outside_planned_window": v.get("outside_planned_window", False)}
