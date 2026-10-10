"""
OCR Service — Couche d'Acquisition (v2 — VLM)
═══════════════════════════════════════════════════════════
Stratégie en 2 niveaux :

  1. PyMuPDF  — extraction directe du texte natif (PDF numérique)
              → rapide, 0 API, ~0.1s

  2. Mistral Pixtral (VLM) — fallback pour PDFs scannés (images)
              → page rendue en PNG via PyMuPDF → encodée base64
              → envoyée à pixtral-12b-2409 qui lit l'image
              → retourne le texte reconnu + structure

Pourquoi VLM plutôt que Tesseract ?
  - Tesseract = OCR classique : mauvais sur les ordonnances manuscrites
    ou peu structurées, requiert un binaire Windows installé séparément
  - Pixtral = LLM multimodal : comprend la structure (tableau, en-tête,
    signature), résiste aux rotations et tampons, renvoie du texte propre
"""
from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from pathlib import Path

import pymupdf as fitz  # PyMuPDF
from dotenv import load_dotenv

load_dotenv()

MISTRAL_API_KEY  = os.getenv("MISTRAL_API_KEY", "")
# Modèle vision disponible sur Mistral La Plateforme
VLM_MODEL        = "pixtral-12b-2409"
# En dessous de ce seuil on considère que le PDF est un scan
MIN_WORDS_NATIVE = 40
# Résolution pour le rendu des pages en image (dpi)
RENDER_DPI       = 200


# ── Résultat OCR ─────────────────────────────────────────────────────────────
@dataclass
class OcrResult:
    full_text:   str
    pages:       dict[int, str]
    method:      str   # "pymupdf" | "vlm_pixtral" | "pymupdf+vlm_partial"
    word_count:  int
    source_file: str


# ── 1. Extraction native (texte embarqué) ────────────────────────────────────
def _extract_native(pdf_path: Path) -> dict[int, str]:
    """PyMuPDF : extrait le texte numérique directement."""
    doc = fitz.open(str(pdf_path))
    pages: dict[int, str] = {}
    for i, page in enumerate(doc):
        pages[i + 1] = page.get_text("text").strip()
    doc.close()
    return pages


# ── 2. Rendu d'une page en PNG base64 ────────────────────────────────────────
def _page_to_base64(page: fitz.Page, dpi: int = RENDER_DPI) -> str:
    """Transforme une page PDF en image PNG encodée base64."""
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
    png_bytes = pix.tobytes("png")
    return base64.standard_b64encode(png_bytes).decode("utf-8")


# ── 3. Fallback VLM (Pixtral) ───────────────────────────────────────────────
def _extract_with_vlm(pdf_path: Path, pages_to_ocr: list[int]) -> dict[int, str]:
    """
    Pour chaque page indiquée, envoie l'image à Pixtral-12b.
    Retourne un dict {page_num: texte_reconnu}.
    """
    if not MISTRAL_API_KEY:
        return {p: "[Erreur VLM: MISTRAL_API_KEY manquante]" for p in pages_to_ocr}

    try:
        from mistralai import Mistral
    except ImportError:
        return {p: "[Erreur VLM: mistralai non installé]" for p in pages_to_ocr}

    client = Mistral(api_key=MISTRAL_API_KEY)
    doc    = fitz.open(str(pdf_path))
    result: dict[int, str] = {}

    PROMPT = (
        "Tu es un expert en lecture de documents médicaux français. "
        "Lis ce document médical (ordonnance, compte-rendu, lettre de sortie…) "
        "et retranscris TOUT le texte visible, y compris en-têtes, noms, "
        "posologies, dates et signatures. "
        "Retourne uniquement le texte brut, sans commentaire."
    )

    for page_num in pages_to_ocr:
        page   = doc[page_num - 1]  # fitz est 0-indexé
        b64    = _page_to_base64(page)

        try:
            response = client.chat.complete(
                model=VLM_MODEL,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": PROMPT
                        }
                    ]
                }],
                max_tokens=2048,
                temperature=0.0,   # Déterministe — on veut du texte fidèle
            )
            result[page_num] = response.choices[0].message.content.strip()
        except Exception as exc:
            result[page_num] = f"[Erreur VLM page {page_num}: {exc}]"

    doc.close()
    return result


# ── Point d'entrée principal ──────────────────────────────────────────────────
def extract_text_from_pdf(pdf_path: str | Path) -> OcrResult:
    """
    Extrait le texte d'un PDF médical.

    Logique :
      • PyMuPDF extrait toutes les pages.
      • Les pages avec < MIN_WORDS_NATIVE mots (scan/image) sont soumises au VLM.
      • Pages natives OK + pages VLM fusionnées → résultat final.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF introuvable : {pdf_path}")

    # ── Étape 1 : extraction native ────────────────────────────────────────
    native_pages = _extract_native(path)

    # ── Étape 2 : identifier les pages pauvres (scannées) ─────────────────
    good_pages: dict[int, str] = {}
    scan_pages: list[int]      = []

    for num, text in native_pages.items():
        if len(text.split()) >= MIN_WORDS_NATIVE:
            good_pages[num] = text
        else:
            scan_pages.append(num)

    # ── Étape 3 : VLM sur les pages scannées ──────────────────────────────
    vlm_pages: dict[int, str] = {}
    if scan_pages:
        print(f"  [OCR] {len(scan_pages)} page(s) scannée(s) → VLM Pixtral: {scan_pages}")
        vlm_pages = _extract_with_vlm(path, scan_pages)

    # ── Étape 4 : fusion ──────────────────────────────────────────────────
    all_pages = {**good_pages, **vlm_pages}
    # Tri par numéro de page
    all_pages = dict(sorted(all_pages.items()))

    full_text  = "\n\n".join(
        f"[PAGE {n}]\n{t}" for n, t in all_pages.items() if t
    )
    word_count = len(full_text.split())

    # Déterminer la méthode utilisée
    if not scan_pages:
        method = "pymupdf"
    elif not good_pages:
        method = "vlm_pixtral"
    else:
        method = "pymupdf+vlm_pixtral"

    return OcrResult(
        full_text=full_text,
        pages=all_pages,
        method=method,
        word_count=word_count,
        source_file=str(path.name),
    )
