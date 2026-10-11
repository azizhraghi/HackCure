"""Verify account identity against the configured .NET service before linking AI data."""
import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from .. import clock, models as m
from ..config import settings
from ..db import Repo, get_repo

router = APIRouter(tags=["account context"])


class Selection(BaseModel):
    patient_id: str | None = None


async def verified(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Sign in to connect your AI patient record")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(settings.surgiguard_api_url + "/api/auth/me", headers={"Authorization": authorization})
            if res.status_code != 200:
                raise HTTPException(401 if res.status_code == 401 else 503, "Account verification unavailable; demo data will not be used")
            identity = res.json()
            if identity["user"]["role"] == "FAMILY_MEMBER":
                linked = await client.get(settings.surgiguard_api_url + "/api/family/patients", headers={"Authorization": authorization})
                linked.raise_for_status()
                identity["linked"] = linked.json()
            return identity
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise HTTPException(503, "Cannot verify the account with the configured account service") from exc


@router.post("/account/ai-context")
async def connect(body: Selection, authorization: str | None = Header(default=None), repo: Repo = Depends(get_repo)):
    identity = await verified(authorization)
    user, profile = identity["user"], identity.get("profile_id")
    if not profile:
        raise HTTPException(409, "This account has no patient or family profile")
    if user["role"] == "PATIENT":
        patient_id, member_id = "acct_" + profile, "acct_" + profile
        if repo.patient(patient_id) is None:
            with repo.atomic():
                repo.add(m.Patient(id=patient_id, name=f"{user['first_name']} {user['last_name']}", first_name=user["first_name"],
                                   age=0, surgery="Not yet supplied", surgery_date=clock.now(), discharge_date=clock.now()))
                repo.add(m.CareTeamMember(id=patient_id, patient_id=patient_id, name=user["first_name"], role="patient"))
                repo.add(m.SurveillancePlan(patient_id=patient_id, plan={"version": 1, "medications": [], "rehab": [],
                           "appointments": [], "allowed_tests": [], "caregiver_permissions": {}, "approval": "not recorded"}))
    elif user["role"] == "FAMILY_MEMBER":
        choices = identity.get("linked", [])
        selected = next((p for p in choices if p["patient_id"] == body.patient_id), None)
        if selected is None and len(choices) == 1:
            selected = choices[0]
        if selected is None:
            raise HTTPException(409, "Link and select one patient before connecting the AI view")
        patient_id = "acct_" + selected["patient_id"]
        member_id = "acct_" + profile + "_" + selected["patient_id"]
        if not repo.patient(patient_id):
            raise HTTPException(409, "The patient must connect their AI record first")
        if not repo.member(member_id):
            repo.add(m.CareTeamMember(id=member_id, patient_id=patient_id, name=user["first_name"], role="caregiver"))
    else:
        raise HTTPException(403, "This app view supports patients and family members")
    return {"patient_id": patient_id, "member_id": member_id, "role": "patient" if user["role"] == "PATIENT" else "caregiver"}


class SharingIn(BaseModel):
    categories: dict[str, bool]


async def sharing_members(patient_id: str, authorization: str | None, repo: Repo):
    if patient_id == "sarah":
        return repo.members(patient_id, "caregiver")
    identity = await verified(authorization)
    if identity["user"]["role"] != "PATIENT" or "acct_" + identity["profile_id"] != patient_id:
        raise HTTPException(403, "only this patient can manage sharing")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(settings.surgiguard_api_url + "/api/patients/me", headers={"Authorization": authorization})
            response.raise_for_status()
            family = response.json().get("family_members", [])
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(503, "Cannot verify linked family members") from exc
    members = []
    for family_member in family:
        id_ = "acct_" + family_member["family_member_id"] + "_" + identity["profile_id"]
        member = repo.member(id_)
        if member is None:
            member = repo.add(m.CareTeamMember(id=id_, patient_id=patient_id, name=family_member["full_name"],
                                             role="caregiver", relation=family_member["relationship"]))
        members.append(member)
    return members


@router.get("/patients/{patient_id}/sharing")
async def sharing(patient_id: str, authorization: str | None = Header(default=None), repo: Repo = Depends(get_repo)):
    from ..agents.digest import CATEGORIES
    members = await sharing_members(patient_id, authorization, repo)
    permissions = repo.plan(patient_id).get("caregiver_permissions", {})
    return [{"id": member.id, "name": member.name, "relation": member.relation,
             "categories": {key: bool(permissions.get(member.id, {}).get("categories", {}).get(key)) for key in CATEGORIES}}
            for member in members]


@router.put("/patients/{patient_id}/sharing/{member_id}")
async def update_sharing(patient_id: str, member_id: str, body: SharingIn,
                         authorization: str | None = Header(default=None), repo: Repo = Depends(get_repo)):
    from ..agents.digest import CATEGORIES
    from .. import audit
    members = await sharing_members(patient_id, authorization, repo)
    if member_id not in {member.id for member in members} or set(body.categories) - set(CATEGORIES):
        raise HTTPException(422, "Use a linked family member and supported sharing categories")
    plan = repo.plan(patient_id)
    permissions = {**plan.get("caregiver_permissions", {})}
    permissions[member_id] = {"categories": {key: bool(body.categories.get(key)) for key in CATEGORIES}}
    repo.add(m.SurveillancePlan(patient_id=patient_id, plan={**plan, "caregiver_permissions": permissions}))
    audit.log(repo, patient_id, patient_id, "sharing.updated", {"member": member_id, **permissions[member_id]}, "caregiver", member_id)
    return permissions[member_id]
