"""
Schéma Pydantic enrichi — Dossier Médical Complet v2
═══════════════════════════════════════════════════════════
Tous les champs cliniques pertinents pour la récupération post-opératoire :
  - Démographie complète (âge, sexe, taille, poids, BMI auto-calculé)
  - Facteurs de risque chirurgical (tabac, obésité, diabète, HTA, ASA)
  - Contexte opératoire (date chirurgie, type anesthésie, hôpital)
  - Médicaments (inchangé + enrichi)
  - Champs manquants → formulaire côté frontend
"""
from __future__ import annotations
from pydantic import BaseModel, Field, model_validator, computed_field
from typing import List, Optional, Any, Literal


# ── Médicament ────────────────────────────────────────────────────────────────
class MedicationSchema(BaseModel):
    dci: str = Field(description="DCI (Dénomination Commune Internationale) — Nom générique OBLIGATOIRE")
    commercial_name: Optional[str] = Field(None, description="Nom commercial si mentionné (ex: Doliprane)")
    dosage_mg: Optional[float] = Field(None, description="Dose en mg (ex: 1000 pour 1g). None si non spécifié.")
    dosage_raw: Optional[str] = Field(None, description="Dosage tel qu'écrit dans le document (ex: '1 g', '4000 UI/0.4mL'). Null si absent.")
    frequency_per_day: Optional[int] = Field(None, description="Nombre de prises par jour (ex: 3)")
    frequency_raw: Optional[str] = Field(None, description="Fréquence telle qu'écrite (ex: '3 fois par jour, matin midi soir'). Null si absente.")
    duration_days: Optional[int] = Field(None, description="Durée du traitement en jours (ex: 14). None si non spécifié.")
    route: Optional[str] = Field(None, description="Voie d'administration: 'oral', 'injectable_sc', 'injectable_iv', 'topique', 'inhalation'. Null si non précisé.")
    drug_class: Optional[str] = Field(None, description="Classe thérapeutique si déductible (ex: AINS, HBPM, IPP, Antibiotique)")
    antibiotic_family: Optional[str] = Field(None, description="Si antibiotique: famille exacte (ex: 'beta-lactamine', 'macrolide', 'fluoroquinolone')")
    special_instructions: Optional[str] = Field(None, description="Instructions spéciales (ex: 'prendre au milieu du repas', 'à jeun')")
    confidence: float = Field(
        description="Score de confiance 0.0 à 1.0 pour l'extraction de CE médicament. "
                    "1.0 = toutes les informations sont explicitement écrites. "
                    "0.5 = certains champs déduits. <0.7 = incertitude, signaler."
    )
    confidence_notes: Optional[str] = Field(None, description="Explication du score si < 0.9 (qu'est-ce qui n'est pas clair)")


# ── Rendez-vous de suivi ──────────────────────────────────────────────────────
class FollowUpAppointment(BaseModel):
    description: str
    timing: str   # ex: "J+14", "6 semaines", "2025-06-18"
    type: str     # "chirurgien", "kinesitherapeute", "infirmiere", "radiologue"


# ── Champ manquant → demander à l'utilisateur ─────────────────────────────────
class MissingField(BaseModel):
    field: str          # nom du champ dans ExtractedProtocol
    label: str          # Label affiché à l'utilisateur
    type: str           # "int" | "float" | "str" | "bool" | "select"
    options: Optional[List[str]] = None  # Si type == "select"
    unit: Optional[str] = None           # Ex: "cm", "kg", "ans"
    importance: str = "medium"           # "critical" | "high" | "medium"
    reason: str = ""    # Pourquoi c'est important médicalement


# ── Protocole extrait complet ─────────────────────────────────────────────────
class ExtractedProtocol(BaseModel):
    # ── Type et identité document ──────────────────────────────────────────
    document_type: str = Field(
        description="Type de document: 'ordonnance', 'compte_rendu_operatoire', 'protocole_kine', 'fiche_sortie'"
    )

    # ── Identité patient ───────────────────────────────────────────────────
    patient_lastname: Optional[str] = None
    patient_firstname: Optional[str] = None
    patient_dob: Optional[str] = Field(None, description="Date de naissance JJ/MM/AAAA")
    patient_age: Optional[int] = Field(
        None,
        description="Âge du patient en années. Calculer depuis date_naissance si possible, sinon null."
    )
    patient_sex: Optional[Literal["M", "F", "unknown"]] = Field(
        None,
        description="Sexe: 'M' (masculin), 'F' (féminin), 'unknown' si non précisé."
    )

    # ── Anthropométrie et facteurs de risque métaboliques ──────────────────
    height_cm: Optional[float] = Field(
        None,
        description="Taille du patient en centimètres si mentionnée (ex: 165.0). Null sinon."
    )
    weight_kg: Optional[float] = Field(
        None,
        description="Poids du patient en kilogrammes si mentionné (ex: 78.5). Null sinon."
    )
    bmi_kg_m2: Optional[float] = Field(
        None,
        description="IMC calculé (poids/taille²). Null si taille ou poids manquant. NE PAS inventer."
    )

    # ── Facteurs de risque chirurgical (CRITIQUES pour sécurité) ───────────
    smoking_status: Optional[Literal["smoker", "ex-smoker", "non-smoker", "unknown"]] = Field(
        None,
        description=(
            "Statut tabagique: 'smoker' (fumeur actif), 'ex-smoker' (ancien fumeur), "
            "'non-smoker' (non fumeur), 'unknown' si non mentionné. "
            "Impact: cicatrisation, risque infectieux, anesthésie."
        )
    )
    diabetes: Optional[Literal["type1", "type2", "gestational", "none", "unknown"]] = Field(
        None,
        description="Diabète: 'type1', 'type2', 'gestational', 'none' si explicitement absent, 'unknown' si non mentionné."
    )
    hypertension: Optional[bool] = Field(
        None,
        description="Hypertension artérielle connue: true/false/null si non mentionné."
    )
    cardiac_history: Optional[bool] = Field(
        None,
        description="Antécédents cardiaques (FA, IDM, insuffisance cardiaque...): true/false/null."
    )
    anticoagulated_before_surgery: Optional[bool] = Field(
        None,
        description="Patient sous anticoagulants AVANT la chirurgie: true/false/null."
    )
    renal_insufficiency: Optional[bool] = Field(
        None,
        description="Insuffisance rénale connue: true/false/null."
    )
    hepatic_insufficiency: Optional[bool] = Field(
        None,
        description="Insuffisance hépatique connue: true/false/null."
    )

    # ── Classification médicale ────────────────────────────────────────────
    asa_score: Optional[int] = Field(
        None,
        description=(
            "Score ASA (American Society of Anesthesiologists) de 1 à 5 si mentionné. "
            "1=patient sain, 2=maladie modérée, 3=maladie sévère, 4=menace vie, 5=moribond. "
            "Ne pas inventer si absent."
        )
    )
    blood_type: Optional[str] = Field(
        None,
        description="Groupe sanguin (ex: 'A+', 'O-', 'AB+'). Null si non mentionné."
    )

    # ── Contexte opératoire ────────────────────────────────────────────────
    surgery_type: Optional[str] = Field(None, description="Type d'intervention (ex: 'PTG droite', 'PTH gauche')")
    surgery_date: Optional[str] = Field(None, description="Date de l'opération au format JJ/MM/AAAA")
    discharge_date: Optional[str] = Field(None, description="Date de sortie de l'hôpital JJ/MM/AAAA")
    hospital_name: Optional[str] = Field(None, description="Nom de l'hôpital ou clinique")
    anesthesia_type: Optional[Literal["general", "spinal", "epidural", "local", "combined", "unknown"]] = Field(
        None,
        description="Type d'anesthésie: 'general', 'spinal' (rachianesthésie), 'epidural', 'local', 'combined', 'unknown'."
    )
    comorbidities: List[str] = Field(
        default_factory=list,
        description="Liste des autres comorbidités mentionnées (ex: ['arthrose', 'ostéoporose', 'hypothyroïdie'])"
    )
    previous_surgeries: List[str] = Field(
        default_factory=list,
        description="Antécédents chirurgicaux mentionnés (ex: ['PTG gauche 2020', 'appendicectomie 1985'])"
    )

    # ── Prescripteur ──────────────────────────────────────────────────────
    prescriber: Optional[str] = Field(None, description="Nom du médecin prescripteur")
    prescription_date: Optional[str] = Field(None, description="Date de prescription JJ/MM/AAAA")

    # ── Allergies ─────────────────────────────────────────────────────────
    known_allergies: List[str] = Field(
        default_factory=list,
        description="Liste des allergies EXPLICITEMENT mentionnées (ex: ['pénicilline'])"
    )

    # ── Médicaments ───────────────────────────────────────────────────────
    medications: List[MedicationSchema] = Field(
        default_factory=list,
        description="Liste COMPLÈTE des médicaments prescrits. Ne rien omettre."
    )

    # ── Instructions et suivi ─────────────────────────────────────────────
    physical_restrictions: List[str] = Field(
        default_factory=list,
        description="Restrictions physiques explicites (ex: 'Pas de conduite', 'béquilles obligatoires')"
    )
    followup_appointments: List[FollowUpAppointment] = Field(
        default_factory=list,
        description="Rendez-vous de suivi mentionnés"
    )
    general_instructions: Optional[str] = Field(
        None,
        description=(
            "Instructions générales ou contre-indications absolues mentionnées. "
            "Si plusieurs instructions, les concaténer en une seule string séparée par des points-virgules. "
            "NE PAS retourner une liste Python ici, toujours une string ou null."
        )
    )

    # ── Qualité d'extraction ──────────────────────────────────────────────
    global_confidence: float = Field(
        description="Score de confiance global (moyenne pondérée). Si < 0.90 : vérification recommandée."
    )
    extraction_warnings: List[str] = Field(
        default_factory=list,
        description="Liste des points d'incertitude ou d'ambiguïté relevés lors de l'extraction"
    )

    # ── Champs manquants (calculés après extraction) ──────────────────────
    missing_fields: List[MissingField] = Field(
        default_factory=list,
        description="Champs cliniquement importants absents du document. Le frontend affichera un formulaire."
    )

    # ── Validators ────────────────────────────────────────────────────────
    @model_validator(mode="before")
    @classmethod
    def coerce_none_lists(cls, data: Any) -> Any:
        """Le LLM retourne parfois null au lieu de [] pour les listes. On corrige."""
        if isinstance(data, dict):
            for list_field in (
                "medications", "known_allergies", "physical_restrictions",
                "followup_appointments", "extraction_warnings",
                "comorbidities", "previous_surgeries", "missing_fields"
            ):
                if data.get(list_field) is None:
                    data[list_field] = []
        return data

    @model_validator(mode="after")
    def compute_derived_fields(self) -> "ExtractedProtocol":
        """Calcule le BMI automatiquement si taille + poids sont disponibles."""
        if self.height_cm and self.weight_kg and not self.bmi_kg_m2:
            h_m = self.height_cm / 100
            self.bmi_kg_m2 = round(self.weight_kg / (h_m * h_m), 1)
        return self

    @model_validator(mode="after")
    def compute_missing_fields(self) -> "ExtractedProtocol":
        """
        Détermine quels champs cliniquement importants sont manquants dans le document.
        Ces champs seront affichés dans un formulaire côté frontend pour complétion manuelle.
        """
        missing: list[MissingField] = []

        if self.patient_age is None and self.patient_dob is None:
            missing.append(MissingField(
                field="patient_age", label="Âge du patient", type="int", unit="ans",
                importance="high",
                reason="L'âge influence directement les seuils de surveillance (ex: paracétamol > 65 ans)"
            ))

        if self.patient_sex is None:
            missing.append(MissingField(
                field="patient_sex", label="Sexe du patient", type="select",
                options=["M", "F"],
                importance="medium",
                reason="Influence certaines posologies et risques thromboemboliques"
            ))

        if self.height_cm is None:
            missing.append(MissingField(
                field="height_cm", label="Taille du patient", type="float", unit="cm",
                importance="medium",
                reason="Nécessaire pour calculer l'IMC et évaluer le risque d'obésité"
            ))

        if self.weight_kg is None:
            missing.append(MissingField(
                field="weight_kg", label="Poids du patient", type="float", unit="kg",
                importance="medium",
                reason="Nécessaire pour calculer l'IMC et adapter certaines posologies"
            ))

        if self.smoking_status is None:
            missing.append(MissingField(
                field="smoking_status", label="Statut tabagique", type="select",
                options=["smoker", "ex-smoker", "non-smoker"],
                importance="critical",
                reason="Le tabagisme ralentit la cicatrisation de 40% et augmente le risque infectieux"
            ))

        if self.diabetes is None:
            missing.append(MissingField(
                field="diabetes", label="Diabète", type="select",
                options=["none", "type1", "type2"],
                importance="high",
                reason="Le diabète augmente fortement le risque d'infection de plaie post-opératoire"
            ))

        if self.surgery_date is None:
            missing.append(MissingField(
                field="surgery_date", label="Date de l'opération", type="str",
                importance="critical",
                reason="Nécessaire pour calculer le jour post-opératoire et la phase de récupération"
            ))

        if self.asa_score is None:
            missing.append(MissingField(
                field="asa_score", label="Score ASA (1-5)", type="int",
                options=["1", "2", "3", "4", "5"],
                importance="medium",
                reason="Classe le risque anesthésique et guide la surveillance post-opératoire"
            ))

        self.missing_fields = missing
        return self

    @property
    def bmi_class(self) -> Optional[str]:
        """Classe IMC selon les seuils OMS."""
        if self.bmi_kg_m2 is None:
            return None
        if self.bmi_kg_m2 < 18.5:
            return "underweight"
        elif self.bmi_kg_m2 < 25:
            return "normal"
        elif self.bmi_kg_m2 < 30:
            return "overweight"
        elif self.bmi_kg_m2 < 35:
            return "obese_class1"
        elif self.bmi_kg_m2 < 40:
            return "obese_class2"
        else:
            return "obese_class3_morbid"

    @property
    def is_high_risk(self) -> bool:
        """True si le patient présente ≥2 facteurs de risque majeurs."""
        risk_factors = [
            self.smoking_status == "smoker",
            self.diabetes not in (None, "none"),
            self.bmi_kg_m2 is not None and self.bmi_kg_m2 >= 30,
            self.cardiac_history is True,
            self.asa_score is not None and self.asa_score >= 3,
        ]
        return sum(risk_factors) >= 2
