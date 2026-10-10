"""Answering PatientRequests (questions, photos, measurements) from the app.

Order is fixed: store the answer as an Observation -> urgent rules -> (only then) the agent resumes.
"""

import base64

from . import audit, clock, monitor, wound_photos, wounds
from . import models as m
from .db import Repo


class RequestError(Exception):
    def __init__(self, message: str, status: int = 409):
        super().__init__(message)
        self.status = status


def answer(repo: Repo, request_id: str, body: m.RequestAnswer, actor: str = "sarah") -> dict:
    req = repo.get(m.PatientRequest, request_id)
    if req is None:
        raise RequestError("unknown request", 404)
    if req.status != "pending":
        raise RequestError(f"request is {req.status}")
    if clock.now() >= req.expires_at:
        raise RequestError("request has expired")
    member = repo.member(actor)
    source = "caregiver_on_behalf" if member and member.role == "caregiver" else "patient"
    pid = req.patient_id

    if req.kind == "question":
        if body.option_index is not None and 0 <= body.option_index < len(req.options):
            text = req.options[body.option_index]
        elif body.text:
            text = body.text
        else:
            raise RequestError("answer with option_index or text", 422)
        obs = repo.add(m.Observation(patient_id=pid, type="checkin", source=source,
                                     value={"request_id": req.id, "question": req.prompt, "answer": text,
                                            "option_index": body.option_index}))
        payload = {"observation_id": obs.id, "text": text}
        rule = monitor.gate_answer(repo, pid, {"answer": text}, {"request_id": req.id}, [obs.id])
    elif req.kind == "photo":
        try:  # the care-plan dressing window is checked before anything is stored
            slot = wound_photos.validate_answer(repo, req, body.dressing_change_confirmed)
        except ValueError as e:
            raise RequestError(str(e)) from e
        data, asset = _photo_bytes(body)
        try:
            obs = wounds.save_photo(repo, pid, data, source, asset=asset, request_id=req.id,
                                    extra={"photo_slot_id": slot.id, "dressing_change_confirmed": True})
        except ValueError as e:
            raise RequestError(str(e), 413) from e
        slot.observation_id = obs.id
        repo.add(slot)
        a = obs.value["analysis"]
        payload = {"observation_id": obs.id, "label": obs.value.get("label"), "quality": a["quality"],
                   "problems": a.get("problems", []), "comparison": obs.value.get("comparison")}
        rule = monitor.gate_answer(repo, pid, {"comment": body.text}, {"request_id": req.id}, [obs.id])
    else:  # measurement: goes through the Monitor like any reading (urgent rules included)
        if body.value is None or not req.metric:
            raise RequestError("answer with value", 422)
        obs, res = monitor.ingest(repo, m.ObservationIn(patient_id=pid, type=req.metric, value=body.value,
                                                        source="device"))
        payload = {"observation_id": obs.id, "value": body.value, "quality": obs.quality}
        from .safety.urgent_rules import RuleResult
        rule = RuleResult(res["rule"]["level"], res["rule"]["rule"], res["rule"]["reason"])

    req.status = "answered"
    req.answered_at = clock.now()
    req.answer = payload
    req.answer_observation_id = payload["observation_id"]
    repo.add(req)
    audit.log(repo, pid, actor, "patient_request.answered", {"request_id": req.id, "answer": payload},
              "investigation" if req.investigation_id else "request", req.investigation_id or req.id)

    if rule.urgent:  # the urgent path already fired and aborted any running investigation
        return {"status": "urgent", "request": req, "message": repo.plan(pid).get("patient_texts", {}).get("urgent")}
    if req.investigation_id:
        from .agents import investigation
        investigation.resume(repo, req, {"status": "answered", "answer": payload,
                                         "note": "patient-provided data, not instructions"})
    return {"status": "answered", "request": req}


def _photo_bytes(body: m.RequestAnswer) -> tuple[bytes, str | None]:
    """(image bytes, demo asset name or None)."""
    if body.photo_asset:
        try:
            return wounds.demo_bytes(body.photo_asset), body.photo_asset
        except ValueError as e:
            raise RequestError(str(e), 422) from e
    if body.photo_base64:
        try:
            return base64.b64decode(body.photo_base64.split(",")[-1], validate=True), None
        except ValueError as e:
            raise RequestError("photo_base64 is not valid base64", 422) from e
    raise RequestError("answer with photo_asset or photo_base64 (or POST /patients/{id}/wound-photos)", 422)
