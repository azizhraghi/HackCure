"""Endpoints that connect the three developers' parts (see app/integrations)."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from .. import models as m
from ..config import get_active_provider, settings
from ..db import Repo, get_repo
from ..integrations import d1_bridge, d2_bridge

router = APIRouter(tags=["integration"])
ROOT = Path(__file__).resolve().parents[3]


def _patient(repo: Repo, patient_id: str) -> m.Patient:
    p = repo.patient(patient_id)
    if p is None:
        raise HTTPException(404, "unknown patient")
    return p


@router.get("/patients/{patient_id}/expected-recovery")
def expected_recovery(patient_id: str, start: bool = True, repo: Repo = Depends(get_repo)):
    """D1: today's 'normal recovery' card (built once from the patient's D2 JSON; status computing -> ready)."""
    _patient(repo, patient_id)
    return d1_bridge.expected_today(repo, patient_id, start)


@router.get("/patients/{patient_id}/twin-forecast")
def twin_forecast(patient_id: str, repo: Repo = Depends(get_repo)):
    """D1 Patient Twin: near-term HR/SpO2 forecast from this patient's own readings (or an abstention with reasons)."""
    _patient(repo, patient_id)
    return d1_bridge.twin_forecast(repo, patient_id)


@router.get("/patients/{patient_id}/d2-document")
def d2_document(patient_id: str, repo: Repo = Depends(get_repo)):
    """The 'Developer 2 JSON' handed to Developer 1 for this patient."""
    _patient(repo, patient_id)
    return d2_bridge.d2_document(repo, patient_id)


@router.get("/patients/{patient_id}/clinical-profile")
def clinical_profile(patient_id: str, repo: Repo = Depends(get_repo)):
    """D2 risk factors/context recorded on the active plan (empty until a D2 plan is confirmed)."""
    _patient(repo, patient_id)
    plan = repo.plan(patient_id)
    return {"plan_version": plan.get("version"), "profile": plan.get("clinical_profile") or {}}


@router.get("/integration/status")
def status(repo: Repo = Depends(get_repo)):
    """Which parts of D1 / D2 / D3 are wired and live on this server."""
    d1_ok, d1_reason = d1_bridge.available()
    return {
        "llm_mode": settings.llm_mode, "llm_provider": settings.llm_provider, "d2_langchain_provider": get_active_provider(),
        "d1": {"package": d1_bridge.D1_SRC.exists(), "expected_recovery": d1_ok, "reason": d1_reason or None,
               "patient_twin": d1_bridge.D1_SRC.exists()},
        "d2": {"documents_v1": "/v1/documents/upload", "rag_chat_v1": "/v1/chat", "checkin_v1": "/v1/checkin",
               "plan_drafts_engine": "d2", "ocr_images": bool(settings.mistral_api_key),
               "embeddings": "mistral" if settings.mistral_api_key and settings.llm_mode == "live" else "fake (keyword-like)"},
        "d3": {"patients": len(repo.all(m.Patient)), "open_alerts": sum(len(repo.open_alerts(p.id)) for p in repo.all(m.Patient))},
        "ui": {"patient_family_app": "/app/", "agent_dashboard": "/agent-demo/", "d3_workflow": "/demo",
               "prototype_console": "/prototype", "api_docs": "/docs",
               "patient_app_built": (ROOT / "mobile" / "dist-web" / "index.html").exists()},
    }
