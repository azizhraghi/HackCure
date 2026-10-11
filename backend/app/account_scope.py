"""Ownership gate for account-linked AI records; the fictional demo stays separate."""
import json
from fastapi import HTTPException
from starlette.responses import JSONResponse
from . import db, models as m
from .routers.account_context import verified


async def guard(request, call_next):
    path = request.url.path
    if path == "/account/ai-context" or path.startswith(("/app", "/static", "/uploads", "/agent-demo")):
        return await call_next(request)
    parts = path.strip("/").split("/")
    patient_ids, members = set(), set()
    payload = {}
    if "application/json" in request.headers.get("content-type", ""):
        try:
            payload = json.loads(await request.body())
        except (ValueError, UnicodeDecodeError):
            pass
        if not isinstance(payload, dict):
            payload = {}
    if payload.get("patient_id"):
        patient_ids.add(payload["patient_id"])
    if payload.get("actor"):
        members.add(payload["actor"])
    if len(parts) > 1 and parts[0] == "patients":
        patient_ids.add(parts[1])
    if request.query_params.get("patient_id"):
        patient_ids.add(request.query_params["patient_id"])
    if request.query_params.get("member_id"):
        members.add(request.query_params["member_id"])
    if request.query_params.get("actor"):
        members.add(request.query_params["actor"])
    if len(parts) > 1 and parts[0] == "caregiver" and parts[1] != "tasks":
        members.add(parts[1])
    with db.session_scope() as repo:
        resources = {"plan-drafts": m.PlanDraft, "alerts": m.Alert, "investigations": m.Investigation,
                     "requests": m.PatientRequest, "notifications": m.Notification}
        resource = repo.get(resources[parts[0]], parts[1]) if len(parts) > 1 and parts[0] in resources else None
        if len(parts) > 2 and parts[:2] == ["caregiver", "tasks"]:
            resource = repo.get(m.CaregiverTask, parts[2])
        if resource:
            patient_ids.add(resource.patient_id)
        for member_id in members:
            member = repo.member(member_id)
            if member:
                patient_ids.add(member.patient_id)
    account = any(str(p).startswith("acct_") for p in [*patient_ids, *members])
    authenticated = bool(request.headers.get("authorization"))
    if not account and not authenticated:
        return await call_next(request)
    try:
        identity = await verified(request.headers.get("authorization"))
        profile = identity.get("profile_id")
        is_patient = identity["user"]["role"] == "PATIENT"
        allowed = {"acct_" + profile} if is_patient and profile else {"acct_" + p["patient_id"] for p in identity.get("linked", [])}
        if not patient_ids or not patient_ids <= allowed:
            raise HTTPException(403, "This account cannot access the requested AI patient record")
        allowed_members = {"acct_" + profile} if is_patient else {"acct_" + profile + "_" + p[5:] for p in allowed}
        if not members <= allowed_members:
            raise HTTPException(403, "Actor does not match the signed-in account")
        if not is_patient:
            allowed_path = parts[0] in ("caregiver", "alerts", "notifications") or (parts[0] == "patients" and parts[-1] == "twin")
            if not allowed_path:
                raise HTTPException(403, "Family access uses the shared family views")
            if parts[0] == "alerts" and (request.method != "GET" or len(parts) > 1 or request.query_params.get("role") != "caregiver"):
                raise HTTPException(403, "Family members cannot access clinician alert details or actions")
            if parts[0] == "patients" and request.query_params.get("role") != "caregiver":
                raise HTTPException(403, "Use the permission-filtered family twin")
    except HTTPException as exc:
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    return await call_next(request)
