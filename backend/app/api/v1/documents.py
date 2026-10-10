"""
API Endpoint : Upload de documents médicaux (PDF / JPEG / PNG)
═══════════════════════════════════════════════════════════════
Routes :
  POST /v1/documents/upload    → OCR + Extraction + Safety + missing_fields
  POST /v1/documents/complete  → Fusion extraction + champs manquants saisis par l'utilisateur

Pipeline D2A :
  OCR (pymupdf | vlm_pixtral) → LLM Extraction → Safety Check → missing_fields
"""
from __future__ import annotations

import base64
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.ai.graphs.protocol_graph import ProtocolState, protocol_graph
from app.ai.graphs.safety_graph import SafetyReport, SafetyState, safety_graph
from app.schemas.protocol import ExtractedProtocol, MissingField
from app.services.ocr_service import OcrResult, extract_text_from_pdf

router = APIRouter()

# ── Types de fichiers acceptés ─────────────────────────────────────────────
ACCEPTED_MIME = {
    "application/pdf":  ".pdf",
    "image/jpeg":       ".jpg",
    "image/png":        ".png",
    "image/webp":       ".webp",
}
ACCEPTED_EXT = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}


# ── Response schemas ──────────────────────────────────────────────────────
class DocumentUploadResponse(BaseModel):
    status:        str                         # SAFE | WARNING | BLOCKED | ERROR
    ocr_method:    str
    word_count:    int
    extraction:    Optional[ExtractedProtocol] = None
    safety_report: Optional[SafetyReport]      = None
    missing_fields: List[MissingField]         = []
    errors:        List[str]                   = []


class CompleteDocumentRequest(BaseModel):
    """
    Permet au frontend de renvoyer les champs manquants saisis par l'utilisateur.
    Le backend fusionne et relance le Safety Check avec le contexte complet.
    """
    extraction: ExtractedProtocol                # Extraction précédente (renvoyée telle quelle)
    patient_allergies: List[str] = []            # Allergies (du formulaire patient)
    user_supplied: Dict[str, Any] = {}           # Champs manquants remplis par l'utilisateur
    # Exemples user_supplied :
    #   { "patient_age": 64, "smoking_status": "smoker", "diabetes": "type2",
    #     "weight_kg": 95.0, "height_cm": 168.0, "surgery_date": "04/06/2025" }


class CompleteDocumentResponse(BaseModel):
    status:        str
    extraction:    ExtractedProtocol
    safety_report: Optional[SafetyReport] = None
    errors:        List[str] = []


# ── OCR dispatcher : PDF ou Image ─────────────────────────────────────────
def _ocr_from_file(tmp_path: Path, original_filename: str) -> OcrResult:
    """
    Dispatch OCR selon le type de fichier :
    - PDF  → PyMuPDF natif + VLM Pixtral si page scannée
    - Image (JPEG/PNG) → directement Pixtral (pas de PyMuPDF)
    """
    ext = Path(original_filename).suffix.lower()

    if ext == ".pdf":
        return extract_text_from_pdf(tmp_path)

    # ── Image directe (scan caméra mobile) ──────────────────────────────
    # On envoie l'image directement à Pixtral VLM sans passer par PyMuPDF
    return _ocr_image_with_vlm(tmp_path, original_filename)


def _ocr_image_with_vlm(image_path: Path, filename: str) -> OcrResult:
    """
    Envoie une image (JPEG/PNG) directement à Pixtral pour OCR.
    Utilisé quand le patient scanne via la caméra mobile.
    """
    from mistralai import Mistral
    api_key = os.getenv("MISTRAL_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="MISTRAL_API_KEY manquante pour l'OCR image.")

    ext = image_path.suffix.lower().lstrip(".")
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"

    with open(image_path, "rb") as f:
        b64 = base64.standard_b64encode(f.read()).decode("utf-8")

    client = Mistral(api_key=api_key)
    response = client.chat.complete(
        model="pixtral-12b-2409",
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                {"type": "text", "text": (
                    "Tu es un expert en lecture de documents médicaux français. "
                    "Lis ce document médical (ordonnance, compte-rendu, lettre de sortie…) "
                    "et retranscris TOUT le texte visible, y compris en-têtes, noms, "
                    "posologies, dates et signatures. "
                    "Retourne uniquement le texte brut, sans commentaire."
                )}
            ]
        }],
        max_tokens=2048,
        temperature=0.0,
    )
    text = response.choices[0].message.content.strip()
    word_count = len(text.split())

    return OcrResult(
        full_text=text,
        pages={1: text},
        method="vlm_pixtral_image",
        word_count=word_count,
        source_file=filename,
    )


# ── Pipeline complet ──────────────────────────────────────────────────────
def _run_pipeline(
    ocr: OcrResult,
    filename: str,
    patient_allergies: List[str],
) -> tuple[Optional[ExtractedProtocol], Optional[SafetyReport], List[str]]:
    """Extraction LLM + Safety Check. Retourne (extracted, report, errors)."""
    proto_state: ProtocolState = {
        "document_text": ocr.full_text,
        "source_file":   filename,
        "word_count":    ocr.word_count,
        "extracted_data": None,
        "errors":         [],
        "low_confidence": False,
    }
    proto_result = protocol_graph.invoke(proto_state)
    extracted    = proto_result.get("extracted_data")
    errors       = proto_result.get("errors", [])

    if not extracted:
        return None, None, errors

    safety_state: SafetyState = {
        "extracted_protocol":   extracted,
        "patient_allergies":    patient_allergies,
        "safety_report":        None,
        "deterministic_alerts": [],
        "needs_llm_check":      False,
    }
    safety_result = safety_graph.invoke(safety_state)
    report = safety_result.get("safety_report")

    return extracted, report, errors


# ══════════════════════════════════════════════════════════════════════════
# Route 1 : Upload initial
# ══════════════════════════════════════════════════════════════════════════
@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(..., description="PDF, JPEG ou PNG du document médical"),
    patient_allergies: str = Form(
        default="",
        description="Allergies connues, séparées par des virgules (ex: 'pénicilline,aspirine')"
    ),
):
    """
    Pipeline D2A complet :
    1. OCR  → PyMuPDF (PDF natif) ou Pixtral VLM (scan/image)
    2. LLM  → ExtractedProtocol enrichi (20+ champs cliniques)
    3. Safety → Vérification allergies + interactions
    4. missing_fields → Liste des champs absents à demander à l'utilisateur

    Accepte : PDF, JPEG, PNG, WebP
    """
    # ── Validation du type de fichier ─────────────────────────────────
    fname = (file.filename or "").lower()
    ext   = Path(fname).suffix
    if ext not in ACCEPTED_EXT:
        raise HTTPException(
            status_code=400,
            detail=f"Format non supporté: {ext}. Acceptés: PDF, JPEG, PNG, WebP"
        )

    # ── Sauvegarde temporaire ──────────────────────────────────────────
    content = await file.read()
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        # ── OCR ────────────────────────────────────────────────────────
        ocr = _ocr_from_file(tmp_path, file.filename or "document")

        # ── LLM Extraction + Safety ────────────────────────────────────
        allergies = [a.strip() for a in patient_allergies.split(",") if a.strip()]
        extracted, report, errors = _run_pipeline(ocr, file.filename or "document", allergies)

        if not extracted:
            return DocumentUploadResponse(
                status="ERROR",
                ocr_method=ocr.method,
                word_count=ocr.word_count,
                errors=errors or ["Extraction échouée — document illisible ou trop court"],
            )

        return DocumentUploadResponse(
            status=report.status if report else "SAFE",
            ocr_method=ocr.method,
            word_count=ocr.word_count,
            extraction=extracted,
            safety_report=report,
            missing_fields=extracted.missing_fields,   # ← Pour le formulaire frontend
            errors=errors,
        )

    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════
# Route 2 : Complétion des champs manquants
# ══════════════════════════════════════════════════════════════════════════
@router.post("/documents/complete", response_model=CompleteDocumentResponse)
async def complete_document(body: CompleteDocumentRequest):
    """
    Reçoit les champs manquants saisis par l'utilisateur dans le formulaire frontend.
    Fusionne avec l'extraction initiale et relance le Safety Check complet.

    Exemple de requête :
    {
      "extraction": { ...données du premier upload... },
      "patient_allergies": ["pénicilline"],
      "user_supplied": {
        "patient_age": 64,
        "smoking_status": "smoker",
        "diabetes": "type2",
        "weight_kg": 95.0,
        "height_cm": 168.0,
        "surgery_date": "04/06/2025",
        "asa_score": 2
      }
    }
    """
    # ── Fusionner les champs utilisateur dans l'extraction ─────────────
    extraction_dict = body.extraction.model_dump()

    for field, value in body.user_supplied.items():
        if field in extraction_dict and value is not None:
            extraction_dict[field] = value

    # ── Reconstruire l'objet ExtractedProtocol (re-run validators) ─────
    # Les validators vont recalculer BMI, missing_fields, is_high_risk...
    try:
        completed = ExtractedProtocol.model_validate(extraction_dict)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Données invalides: {e}")

    # ── Relancer Safety Check avec profil complet ──────────────────────
    safety_state: SafetyState = {
        "extracted_protocol":   completed,
        "patient_allergies":    body.patient_allergies,
        "safety_report":        None,
        "deterministic_alerts": [],
        "needs_llm_check":      False,
    }
    safety_result = safety_graph.invoke(safety_state)
    report = safety_result.get("safety_report")

    return CompleteDocumentResponse(
        status=report.status if report else "SAFE",
        extraction=completed,
        safety_report=report,
        errors=[],
    )
