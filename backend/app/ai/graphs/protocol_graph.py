"""
LangGraph : Agent 1 — Extracteur de Protocoles v2
Pipeline : OCR text → LLM → ExtractedProtocol (enrichi)
"""
from __future__ import annotations
import os
from typing import TypedDict, Optional, List
from dotenv import load_dotenv
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langgraph.graph import StateGraph, END

from app.schemas.protocol import ExtractedProtocol

load_dotenv()
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_MODEL   = os.getenv("MISTRAL_MODEL", "open-mistral-nemo")


# ── State ──────────────────────────────────────────────────────────────────
class ProtocolState(TypedDict):
    document_text: str
    source_file: str
    word_count: int
    extracted_data: Optional[ExtractedProtocol]
    errors: List[str]
    low_confidence: bool


# ── LLM & Parser ───────────────────────────────────────────────────────────
llm = ChatMistralAI(
    model=MISTRAL_MODEL,
    mistral_api_key=MISTRAL_API_KEY,
    temperature=0.0,
    max_tokens=4000,
)
parser = PydanticOutputParser(pydantic_object=ExtractedProtocol)

EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Tu es un système expert d'extraction de données médicales pour la France.
Tu analyses des documents médicaux (ordonnances, comptes-rendus opératoires, lettres de sortie).

RÈGLES ABSOLUES :
1. Extrais UNIQUEMENT ce qui est EXPLICITEMENT écrit dans le document. JAMAIS d'invention.
2. Si une information est absente ou ambiguë → mets `null` et signale dans `extraction_warnings`.
3. Pour chaque médicament, le champ `dci` est OBLIGATOIRE.
4. `global_confidence` = moyenne des scores de confiance des médicaments.

DÉMOGRAPHIE — Cherche activement :
- Âge du patient (champ age_patient ou date de naissance → calculer l'âge)
- Sexe (M/F, Monsieur/Madame, Mr/Mme)
- Taille (cm) et Poids (kg) → calcule l'IMC si les deux sont présents
- Groupe sanguin (A+, B-, O+, AB+...)

FACTEURS DE RISQUE CHIRURGICAL — Cherche activement :
- Tabac : cherche "fumeur", "tabagisme", "non fumeur", "sevré depuis", "ex-fumeur", "paquet-année"
  → smoking_status: "smoker" | "ex-smoker" | "non-smoker" | null
- Diabète : cherche "diabète", "insuline", "metformine", "DID", "DNID", "HbA1c"
  → diabetes: "type1" | "type2" | "none" | null
- HTA : cherche "hypertension", "HTA", "antihypertenseur", "traitement TA"
  → hypertension: true | false | null
- Cardio : cherche "cardiopathie", "insuffisance cardiaque", "FA", "IDM", "stent", "pace-maker"
  → cardiac_history: true | false | null
- ASA : cherche "ASA I", "ASA II", "ASA III", "ASA score: X"
  → asa_score: 1-5 | null

CONTEXTE OPÉRATOIRE — Cherche activement :
- Date intervention (cherche "opéré le", "intervention le", "date : ")
  → surgery_date: JJ/MM/AAAA | null
- Date de sortie → discharge_date
- Type anesthésie : "rachianesthésie"=spinal, "anesthésie générale"=general, "péridurale"=epidural
- Nom hôpital / clinique

ANTIBIOTIQUES — Si antibiotique détecté :
- Amoxicilline/Augmentin/Clamoxyl/Penicilline → antibiotic_family: "beta-lactamine"
- Azithromycine/Clarithromycine/Érythromycine → "macrolide"
- Ciprofloxacine/Ofloxacine/Lévofloxacine → "fluoroquinolone"
- Ceftriaxone/Céfuroxime → "cephalosporine"
- Clindamycine → "lincosamide"
- Métronidazole → "nitroimidazole"

FORMAT DE SORTIE JSON :
{format_instructions}

IMPORTANT sur les champs `null` vs `unknown` :
- Si le document ne mentionne PAS du tout le tabac → smoking_status = null (absent du document)
- Si le document dit explicitement "non fumeur" → smoking_status = "non-smoker"
- Ne mets JAMAIS "unknown" si l'info est simplement absente du document → mets null
"""),
    ("user", """Analyse ce document médical et extrais toutes les informations structurées.

SOURCE : {source_file}
DOCUMENT :
---
{document_text}
---

Rappel : Extrais le maximum d'informations. Si un champ est absent du document, mets null.
Ne mets JAMAIS une valeur inventée. Les champs manquants seront demandés à l'utilisateur.""")
])

extraction_chain = EXTRACTION_PROMPT | llm | parser


# ── Nodes ──────────────────────────────────────────────────────────────────
def precheck_node(state: ProtocolState) -> dict:
    """Vérification minimale avant d'envoyer au LLM."""
    errors = state.get("errors", [])
    if state.get("word_count", 0) < 10:
        errors.append("Document trop court ou vide pour extraction.")
        return {"errors": errors, "low_confidence": True}
    return {"errors": errors}


def extract_node(state: ProtocolState) -> dict:
    """Appel LLM pour extraction structurée."""
    try:
        result: ExtractedProtocol = extraction_chain.invoke({
            "document_text": state["document_text"],
            "source_file":   state.get("source_file", "unknown"),
            "format_instructions": parser.get_format_instructions()
        })
        return {"extracted_data": result}
    except Exception as e:
        return {"errors": state.get("errors", []) + [f"Extraction LLM échouée: {str(e)}"]}


def confidence_check_node(state: ProtocolState) -> dict:
    """Vérifie le seuil de confiance global."""
    data = state.get("extracted_data")
    warnings = []

    if data is None:
        return {"low_confidence": True, "errors": state.get("errors", []) + ["Pas de données extraites."]}

    if data.global_confidence < 0.90:
        warnings.append(
            f"[CONFIANCE INSUFFISANTE] Score global : {data.global_confidence:.0%}. "
            f"Vérification manuelle recommandée avant utilisation clinique."
        )

    for med in data.medications:
        if med.confidence < 0.75:
            warnings.append(
                f"[MED INCERTAIN] {med.dci} : confiance {med.confidence:.0%}. "
                f"Note: {med.confidence_notes or 'Non précisé'}"
            )

    # Avertissement si patient à haut risque
    if data.is_high_risk:
        warnings.append(
            "[PATIENT HAUT RISQUE] ≥2 facteurs de risque chirurgical détectés. "
            "Surveillance renforcée recommandée."
        )

    is_low = data.global_confidence < 0.90
    return {
        "low_confidence": is_low,
        "errors": state.get("errors", []) + warnings
    }


# ── Graph ──────────────────────────────────────────────────────────────────
builder = StateGraph(ProtocolState)
builder.add_node("precheck",          precheck_node)
builder.add_node("extract",           extract_node)
builder.add_node("confidence_check",  confidence_check_node)

builder.set_entry_point("precheck")
builder.add_edge("precheck",         "extract")
builder.add_edge("extract",          "confidence_check")
builder.add_edge("confidence_check", END)

protocol_graph = builder.compile()
