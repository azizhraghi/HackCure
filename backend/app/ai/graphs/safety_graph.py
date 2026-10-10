"""
LangGraph : Agent 2 — Medical Safety Checker
Deux niveaux de vérification :
  1. Règles déterministes (rapide, 100% fiable) → Allergies + interactions critiques
  2. LLM critique (cas complexes non couverts par les règles)
"""
from __future__ import annotations
import os
from typing import TypedDict, Optional, List
from dataclasses import dataclass, field
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from app.config import get_chat_llm
from app.schemas.protocol import ExtractedProtocol

load_dotenv()
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-small-latest")


# ── Schéma de sortie ────────────────────────────────────────────────────────
class SafetyAlert(BaseModel):
    severity: str = Field(description="'CRITICAL' | 'WARNING' | 'INFO'")
    rule_type: str = Field(description="'allergy' | 'drug_interaction' | 'dosage' | 'llm_check'")
    message: str = Field(description="Message clair pour le médecin, en français")
    medications_involved: List[str] = Field(default_factory=list)


class SafetyReport(BaseModel):
    status: str = Field(description="'SAFE' | 'WARNING' | 'BLOCKED'")
    alerts: List[SafetyAlert] = Field(default_factory=list)
    llm_analysis: Optional[str] = Field(None, description="Analyse libre du LLM si des alertes complexes ont été détectées")


# ── Base de Connaissances Déterministe ─────────────────────────────────────
# Allergens → Familles médicamenteuses concernées
ALLERGY_RULES: dict[str, list[str]] = {
    "pénicilline":         ["beta-lactamine", "penicilline", "aminopenicilline", "carbapenem"],
    "penicilline":         ["beta-lactamine", "penicilline", "aminopenicilline", "carbapenem"],
    "aspirine":            ["ains", "salicyle", "acetylsalicylique"],
    "ains":                ["ains", "cox-2", "cox2", "salicyle"],
    "sulfamide":           ["sulfamide", "sulfone"],
    "latex":               [],
    # English names (documents in English, e.g. the Sarah Miller demo)
    "penicillin":          ["beta-lactamine", "penicilline", "aminopenicilline", "carbapenem"],
    "aspirin":             ["ains", "salicyle", "acetylsalicylique"],
    "nsaid":               ["ains", "cox-2", "cox2", "salicyle"],
    "nsaids":              ["ains", "cox-2", "cox2", "salicyle"],
    "sulfa":               ["sulfamide", "sulfone"],
    "sulfonamide":         ["sulfamide", "sulfone"],
}

# Médicaments connus appartenant aux familles à risque
DRUG_FAMILY_MAP: dict[str, str] = {
    "amoxicilline":            "beta-lactamine",
    "augmentin":               "beta-lactamine",
    "clamoxyl":                "beta-lactamine",
    "amoxicilline/acide clavulanique": "beta-lactamine",
    "ampicilline":             "beta-lactamine",
    "oxacilline":              "beta-lactamine",
    "pipéracilline":           "beta-lactamine",
    "tazobactam":              "beta-lactamine",
    "céfazoline":              "cephalosporine",
    "céfuroxime":              "cephalosporine",
    "céfotaxime":              "cephalosporine",
    "imipénème":               "carbapenem",
    "méropénème":              "carbapenem",
    "ibuprofène":              "ains",
    "kétoprofène":             "ains",
    "diclofénac":              "ains",
    "naproxène":               "ains",
    "célécoxib":               "ains",
    "aspirine":                "ains",
    # English names
    "amoxicillin":             "beta-lactamine",
    "amoxicillin/clavulanate": "beta-lactamine",
    "co-amoxiclav":            "beta-lactamine",
    "ampicillin":              "beta-lactamine",
    "flucloxacillin":          "beta-lactamine",
    "piperacillin":            "beta-lactamine",
    "cefazolin":               "cephalosporine",
    "cefuroxime":              "cephalosporine",
    "cefotaxime":              "cephalosporine",
    "imipenem":                "carbapenem",
    "meropenem":               "carbapenem",
    "ibuprofen":               "ains",
    "ketoprofen":              "ains",
    "diclofenac":              "ains",
    "naproxen":                "ains",
    "celecoxib":               "ains",
    "aspirin":                 "ains",
}

# Interactions médicamenteuses critiques (paires qui ne doivent pas être co-prescrites sans surveillance)
CRITICAL_INTERACTIONS: list[tuple[str, str, str, str]] = [
    ("hbpm", "ains",
     "WARNING",
     "Association HBPM + AINS : risque hémorragique augmenté. Surveillance plaquettes et saignement renforcée."),
    ("hbpm", "anticoagulant",
     "CRITICAL",
     "Double anticoagulation détectée : risque hémorragique majeur."),
    ("ains", "ains",
     "CRITICAL",
     "Double prescription d'AINS détectée : contre-indiqué (risque gastro-intestinal et rénal sévère)."),
    ("inh. pompe à protons", "ipp",
     "INFO",
     "Double IPP prescrit — vérifier si intentionnel."),
]

# Correspondance DCI → classe pour les règles d'interaction
DRUG_CLASS_MAP: dict[str, list[str]] = {
    "énoxaparine":     ["hbpm", "anticoagulant"],
    "énoxaparine sodique": ["hbpm", "anticoagulant"],
    "héparine":        ["hbpm", "anticoagulant"],
    "fondaparinux":    ["hbpm", "anticoagulant"],
    "warfarine":       ["anticoagulant", "avk"],
    "rivaroxaban":     ["anticoagulant", "anticoagulant_oral"],
    "apixaban":        ["anticoagulant", "anticoagulant_oral"],
    "célécoxib":       ["ains", "cox2"],
    "ibuprofène":      ["ains"],
    "kétoprofène":     ["ains"],
    "diclofénac":      ["ains"],
    "naproxène":       ["ains"],
    "aspirine":        ["ains", "antiagregant"],
    "pantoprazole":    ["ipp", "inh. pompe à protons"],
    "oméprazole":      ["ipp", "inh. pompe à protons"],
    "ésoméprazole":    ["ipp", "inh. pompe à protons"],
    # English names
    "enoxaparin":      ["hbpm", "anticoagulant"],
    "heparin":         ["hbpm", "anticoagulant"],
    "warfarin":        ["anticoagulant", "avk"],
    "celecoxib":       ["ains", "cox2"],
    "ibuprofen":       ["ains"],
    "ketoprofen":      ["ains"],
    "diclofenac":      ["ains"],
    "naproxen":        ["ains"],
    "aspirin":         ["ains", "antiagregant"],
    "pantoprazole":    ["ipp", "inh. pompe à protons"],
    "omeprazole":      ["ipp", "inh. pompe à protons"],
    "esomeprazole":    ["ipp", "inh. pompe à protons"],
}


# ── State ──────────────────────────────────────────────────────────────────
class SafetyState(TypedDict):
    extracted_protocol: ExtractedProtocol
    patient_allergies: List[str]    # vient du dossier patient
    safety_report: Optional[SafetyReport]
    deterministic_alerts: List[SafetyAlert]
    needs_llm_check: bool


# ── Node 1 : Règles Déterministes ──────────────────────────────────────────
def deterministic_check_node(state: SafetyState) -> dict:
    protocol: ExtractedProtocol = state["extracted_protocol"]
    # Fusionner les allergies du dossier patient + celles du document
    patient_allergies = [a.lower().strip() for a in state.get("patient_allergies", [])]
    doc_allergies = [a.lower().strip() for a in (protocol.known_allergies or [])]
    all_allergies = list(set(patient_allergies + doc_allergies))

    alerts: list[SafetyAlert] = []
    needs_llm = False

    # Règle 1 : Vérification Allergie × Médicament prescrit
    for med in protocol.medications:
        dci_lower = med.dci.lower().strip()
        commercial_lower = (med.commercial_name or "").lower().strip()

        # Famille médicamenteuse du médicament prescrit
        med_family = (med.antibiotic_family or "").lower()
        if not med_family:
            med_family = DRUG_FAMILY_MAP.get(dci_lower, DRUG_FAMILY_MAP.get(commercial_lower, ""))

        for allergy in all_allergies:
            if not allergy:
                continue
            forbidden_families = ALLERGY_RULES.get(allergy, [])
            # Vérification directe (nom du médicament = allergène)
            if allergy in dci_lower or allergy in commercial_lower:
                alerts.append(SafetyAlert(
                    severity="CRITICAL",
                    rule_type="allergy",
                    message=f"[ALLERGIE DIRECTE] Le patient est allergique à '{allergy}' "
                            f"et '{med.dci}' ({med.commercial_name}) est prescrit. CONTRE-INDIQUÉ ABSOLU.",
                    medications_involved=[med.dci]
                ))
            # Vérification par famille
            elif med_family and any(f in med_family for f in forbidden_families):
                alerts.append(SafetyAlert(
                    severity="CRITICAL",
                    rule_type="allergy",
                    message=f"[ALLERGIE CROISÉE] Patient allergique à '{allergy}'. "
                            f"'{med.dci}' appartient à la famille '{med_family}' — CONTRE-INDIQUÉ.",
                    medications_involved=[med.dci]
                ))

    # Règle 2 : Interactions Médicamenteuses Critiques
    meds_classes: list[list[str]] = []
    for med in protocol.medications:
        dci_lower = med.dci.lower().strip()
        drug_class = med.drug_class or ""
        classes = DRUG_CLASS_MAP.get(dci_lower, [drug_class.lower()] if drug_class else [])
        meds_classes.append(classes)

    for i, classes_a in enumerate(meds_classes):
        for j, classes_b in enumerate(meds_classes):
            if i >= j:
                continue
            for rule_a, rule_b, severity, message in CRITICAL_INTERACTIONS:
                # a rule pair matches in either order of the prescription list
                if (any(rule_a in c for c in classes_a) and any(rule_b in c for c in classes_b)) or \
                        (any(rule_b in c for c in classes_a) and any(rule_a in c for c in classes_b)):
                    alerts.append(SafetyAlert(
                        severity=severity,
                        rule_type="drug_interaction",
                        message=message,
                        medications_involved=[
                            protocol.medications[i].dci,
                            protocol.medications[j].dci
                        ]
                    ))

    # Si des alertes complexes n'ont pas pu être catégorisées, on demande au LLM
    if not alerts and len(protocol.medications) > 3:
        needs_llm = True

    return {
        "deterministic_alerts": alerts,
        "needs_llm_check": needs_llm
    }


# ── Node 2 : LLM Critique (optionnel) ─────────────────────────────────────
class LLMSafetyOutput(BaseModel):
    additional_alerts: List[SafetyAlert] = Field(default_factory=list)
    summary: str = Field(description="Résumé de l'analyse de sécurité en 2-3 phrases.")


llm_safety = get_chat_llm(temperature=0.0)  # shared provider (LLM_ROUTE_D2 / LLM_PROVIDER)
llm_safety_parser = PydanticOutputParser(pydantic_object=LLMSafetyOutput)

SAFETY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Tu es un pharmacien clinicien expert en pharmacovigilance française.
Analyse la liste de médicaments ci-dessous et identifie des interactions médicamenteuses, 
des contre-indications ou des problèmes de dosage NON DÉJÀ signalés dans les alertes existantes.
Sois précis, basé sur les données médicales. Ne répète pas les alertes déjà listées.

FORMAT : {format_instructions}"""),
    ("user", """PROFIL PATIENT :
Allergies connues : {allergies}

MÉDICAMENTS PRESCRITS :
{meds_list}

ALERTES DÉJÀ DÉTECTÉES (ne pas répéter) :
{existing_alerts}""")
])

llm_safety_chain = SAFETY_PROMPT | llm_safety | llm_safety_parser


def llm_safety_check_node(state: SafetyState) -> dict:
    if not state.get("needs_llm_check"):
        return {}

    protocol = state["extracted_protocol"]
    meds_list = "\n".join([
        f"- {m.dci} {m.dosage_raw} — {m.frequency_raw} — Classe: {m.drug_class or 'non précisée'}"
        for m in protocol.medications
    ])
    existing = "\n".join([a.message for a in state.get("deterministic_alerts", [])])

    try:
        result = llm_safety_chain.invoke({
            "allergies": ", ".join(state.get("patient_allergies", [])) or "Aucune connue",
            "meds_list": meds_list,
            "existing_alerts": existing or "Aucune",
            "format_instructions": llm_safety_parser.get_format_instructions()
        })
        extra_alerts = result.additional_alerts
        return {
            "deterministic_alerts": state.get("deterministic_alerts", []) + extra_alerts,
            "safety_report": SafetyReport(
                status="WARNING" if extra_alerts else "SAFE",
                alerts=state.get("deterministic_alerts", []) + extra_alerts,
                llm_analysis=result.summary
            )
        }
    except Exception as e:
        return {"deterministic_alerts": state.get("deterministic_alerts", [])}


# ── Node 3 : Consolidation du rapport final ────────────────────────────────
def consolidate_node(state: SafetyState) -> dict:
    all_alerts = state.get("deterministic_alerts", [])

    if state.get("safety_report") and state["safety_report"].alerts:
        all_alerts = state["safety_report"].alerts

    has_critical = any(a.severity == "CRITICAL" for a in all_alerts)
    has_warning = any(a.severity == "WARNING" for a in all_alerts)

    if has_critical:
        status = "BLOCKED"
    elif has_warning:
        status = "WARNING"
    else:
        status = "SAFE"

    report = SafetyReport(status=status, alerts=all_alerts)
    return {"safety_report": report}


# ── Graph ──────────────────────────────────────────────────────────────────
builder = StateGraph(SafetyState)
builder.add_node("deterministic_check", deterministic_check_node)
builder.add_node("llm_safety_check", llm_safety_check_node)
builder.add_node("consolidate", consolidate_node)

builder.set_entry_point("deterministic_check")
builder.add_edge("deterministic_check", "llm_safety_check")
builder.add_edge("llm_safety_check", "consolidate")
builder.add_edge("consolidate", END)

safety_graph = builder.compile()
