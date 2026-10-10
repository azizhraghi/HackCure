"""
API Endpoint : Check-in quotidien du patient (données de l'app mobile)
Reçoit les métriques du patient (douleur, fatigue, mobilité, symptômes)
et retourne une analyse de risque.

Correspond au CheckInScreen de l'app mobile qui envoie :
  - pain (0-10), fatigue (0-10), mobility (0-10)
  - wound_symptoms: ["redness", "drainage", "warmth", ...]
  - other_symptoms: ["chills", "fever", "shortness_of_breath", ...]
"""
from __future__ import annotations
from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


# ── Request / Response schemas ─────────────────────────────────────────
class CheckInRequest(BaseModel):
    patient_id: str = Field(default="sarah_miller", description="ID du patient")
    pain: int = Field(ge=0, le=10, description="Score douleur EVA 0-10")
    fatigue: int = Field(ge=0, le=10, description="Score fatigue 0-10")
    mobility: int = Field(ge=0, le=10, description="Score mobilité 0-10")
    wound_symptoms: List[str] = Field(default_factory=list, description="Symptômes plaie: redness, swelling, drainage, warmth, odor")
    other_symptoms: List[str] = Field(default_factory=list, description="Autres symptômes: chills, fever, nausea, vomiting, shortness_of_breath, calf_pain")
    wound_temp: Optional[float] = Field(None, description="Température plaie (capteur)")
    heart_rate: Optional[int] = Field(None, description="Fréquence cardiaque")
    dressing_temp: Optional[float] = Field(None, description="Température pansement (capteur)")


class CheckInAlert(BaseModel):
    severity: str  # "INFO" | "WARNING" | "EMERGENCY"
    message: str
    action: str    # "monitor" | "contact_surgeon" | "call_emergency"


class CheckInResponse(BaseModel):
    status: str  # "OK" | "WARNING" | "EMERGENCY"
    recovery_score: int  # 0-100
    alerts: List[CheckInAlert] = []
    recommendations: List[str] = []
    recorded: Optional[dict] = None  # shared backend: result of the D3 check-in pipeline when the patient exists


# ── Règles déterministes médicales ────────────────────────────────────
EMERGENCY_SYMPTOMS = {"shortness_of_breath", "chest_pain", "calf_pain", "fainting"}
WARNING_WOUND_SYMPTOMS = {"drainage", "warmth", "odor", "spreading_redness"}
WARNING_OTHER_SYMPTOMS = {"chills", "fever"}


@router.post("/checkin", response_model=CheckInResponse)
async def checkin_endpoint(req: CheckInRequest):
    """
    Analyse les données quotidiennes du patient.
    Logique déterministe + seuils médicaux validés.
    """
    alerts: list[CheckInAlert] = []
    recommendations: list[str] = []
    status = "OK"

    # ── 1. Douleur (EVA) ───────────────────────────────────────────
    if req.pain >= 8:
        alerts.append(CheckInAlert(
            severity="WARNING",
            message=f"Douleur EVA élevée : {req.pain}/10. Risque de complication ou analgésie insuffisante.",
            action="contact_surgeon"
        ))
        status = "WARNING"
    elif req.pain >= 7:
        alerts.append(CheckInAlert(
            severity="WARNING",
            message=f"Douleur EVA modérée-haute : {req.pain}/10. Vérifier l'observance du traitement antalgique.",
            action="monitor"
        ))
        if status != "EMERGENCY":
            status = "WARNING"

    # ── 2. Symptômes d'urgence ─────────────────────────────────────
    emergency_found = set(req.other_symptoms) & EMERGENCY_SYMPTOMS
    if emergency_found:
        alerts.append(CheckInAlert(
            severity="EMERGENCY",
            message=f"Symptôme d'URGENCE détecté : {', '.join(emergency_found)}. "
                    "Suspicion d'embolie pulmonaire ou thrombose veineuse profonde.",
            action="call_emergency"
        ))
        status = "EMERGENCY"

    # ── 3. Symptômes de plaie ──────────────────────────────────────
    wound_warnings = set(req.wound_symptoms) & WARNING_WOUND_SYMPTOMS
    if wound_warnings:
        alerts.append(CheckInAlert(
            severity="WARNING",
            message=f"Signes d'infection de la plaie : {', '.join(wound_warnings)}. "
                    "Contacter l'équipe chirurgicale dans la journée.",
            action="contact_surgeon"
        ))
        if status != "EMERGENCY":
            status = "WARNING"

    # ── 4. Fièvre / Frissons ──────────────────────────────────────
    other_warnings = set(req.other_symptoms) & WARNING_OTHER_SYMPTOMS
    if other_warnings:
        alerts.append(CheckInAlert(
            severity="WARNING",
            message=f"Signes généraux d'infection : {', '.join(other_warnings)}. "
                    "Prendre la température et contacter le chirurgien si > 38°C.",
            action="contact_surgeon"
        ))
        if status != "EMERGENCY":
            status = "WARNING"

    # ── 5. Température plaie (capteur) ─────────────────────────────
    if req.wound_temp and req.wound_temp >= 38.5:
        alerts.append(CheckInAlert(
            severity="WARNING",
            message=f"Température péri-cicatricielle élevée : {req.wound_temp}°C. "
                    "Possible infection locale débutante.",
            action="contact_surgeon"
        ))
        if status != "EMERGENCY":
            status = "WARNING"

    # ── 6. Calcul du Recovery Score ────────────────────────────────
    # Formule simplifiée : on part de 100 et on soustrait les facteurs de risque
    score = 100
    score -= req.pain * 4           # Douleur : -0 à -40
    score -= (10 - req.mobility) * 3  # Immobilité : -0 à -30
    score -= req.fatigue * 2        # Fatigue : -0 à -20
    score -= len(wound_warnings) * 5  # Symptômes plaie : -5 chacun
    score -= len(emergency_found) * 15  # Urgence : -15 chacun
    score = max(0, min(100, score))

    # ── 7. Recommandations ─────────────────────────────────────────
    if req.pain <= 4 and not alerts:
        recommendations.append("Continuez vos exercices de rééducation comme prévu.")
    if req.fatigue >= 6:
        recommendations.append("Fatigue importante — Pensez à vous reposer et à bien vous hydrater.")
    if req.mobility <= 3:
        recommendations.append("Mobilité réduite — Essayez de marcher quelques pas avec les béquilles.")
    if not alerts:
        recommendations.append("Tout semble normal. Continuez à suivre votre protocole de récupération.")

    return CheckInResponse(
        status=status,
        recovery_score=score,
        alerts=alerts,
        recommendations=recommendations,
        recorded=_record(req),
    )


def _record(req: CheckInRequest) -> Optional[dict]:
    """Store the check-in through the D3 pipeline (urgent rules -> monitor -> clarification) so the safety
    lane, the investigation agent and the clinic dashboard see it. None when the patient is unknown here."""
    import json
    from app import db
    from app.agents import checkin as d3_checkin
    from app.models import CheckinIn
    with db.session_scope() as repo:
        if repo.patient(req.patient_id) is None:
            return None
        out = d3_checkin.submit(repo, CheckinIn(patient_id=req.patient_id, pain=req.pain, fatigue=req.fatigue,
                                                mobility=req.mobility,
                                                chips=list(dict.fromkeys(req.wound_symptoms + req.other_symptoms))))
        return json.loads(json.dumps(out, default=lambda o: o.model_dump() if hasattr(o, "model_dump") else str(o)))
