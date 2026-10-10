"""Read Developer 2's document-extraction JSON into the model's dossier.

Developer 2 extracts a discharge prescription ("ordonnance") into JSON. This
keeps what describes the patient medically and drops what identifies them:
names, prescriber and raw dates never reach the model or the Twin.

What is taken:
  patient_dob + prescription_date -> age
  surgery_type (French free text) -> a procedure code and the side
  medications[].drug_class        -> medication classes the model knows
  medications[].dci               -> the individual drugs
  known_allergies                 -> allergies
"""

import unicodedata
from datetime import date, datetime
from typing import Any

# French surgery wording -> procedure code. Checked in order; first match wins.
_PROCEDURES = [
    (("prothese totale du genou", "prothese totale de genou", "ptg"), "knee_replacement"),
    (("prothese totale de hanche", "prothese totale de la hanche", "pth"), "hip_replacement"),
    (("cholecystectomie",), "laparoscopic_cholecystectomy"),
    (("colectomie",), "colectomy"),
    (("lobectomie",), "lobectomy"),
    (("pontage",), "cabg"),
]
_SIDES = {"droite": "right", "droit": "right", "gauche": "left"}

# French drug-class wording -> class code. Substring match on the normalised text.
_CLASSES = [
    ("ains", "nsaid"), ("anti-inflammatoire", "nsaid"),
    ("hbpm", "anticoagulant"), ("anticoagulant", "anticoagulant"), ("heparine", "anticoagulant"),
    ("opio", "opioid"), ("morphin", "opioid"),
    ("betabloquant", "beta_blocker"), ("beta-bloquant", "beta_blocker"),
    ("cortico", "corticosteroid"),
    ("antihypertenseur", "antihypertensive"), ("iec", "antihypertensive"), ("ara2", "antihypertensive"),
    ("antibiotique", "antibiotic"),
    ("analgesique", "analgesic"), ("antalgique", "analgesic"),
]


def _norm(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(plain.lower().split())


def _slug(text: str) -> str:
    return _norm(text).replace(" ", "_")


def _date(text: str | None) -> date | None:
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text or "", fmt).date()
        except ValueError:
            continue
    return None


def normalise_procedure(surgery_type: str) -> tuple[str, str | None]:
    """('knee_replacement', 'right') from 'Prothèse Totale du Genou Droite'."""
    text = _norm(surgery_type)
    side = next((v for k, v in _SIDES.items() if k in text.split()), None)
    for phrases, code in _PROCEDURES:
        if any(p in text.split() if len(p) <= 3 else p in text for p in phrases):
            return code, side
    # Unrecognised wording is kept as-is; the model will say it has not learned it.
    return _slug(" ".join(w for w in text.split() if w not in _SIDES)), side


def normalise_drug_class(drug_class: str | None) -> str | None:
    text = _norm(drug_class or "")
    return next((code for needle, code in _CLASSES if needle in text), _slug(text) or None)


def dossier_from_d2(document: dict[str, Any], on: date | None = None) -> dict[str, Any]:
    """Build the model's dossier from Developer 2's JSON. `on` defaults to the prescription date."""
    x = document.get("extraction", document)
    dossier: dict[str, Any] = {}

    born = _date(x.get("patient_dob"))
    ref = on or _date(x.get("prescription_date"))
    if born and ref:
        dossier["age"] = ref.year - born.year - ((ref.month, ref.day) < (born.month, born.day))

    if x.get("surgery_type"):
        procedure, side = normalise_procedure(x["surgery_type"])
        dossier["surgery"] = {"procedure": procedure} | ({"side": side} if side else {})

    meds = x.get("medications") or []
    classes = sorted({c for m in meds if (c := normalise_drug_class(m.get("drug_class")))})
    dossier["medications"] = [{"name": c} for c in classes]  # by class, as the model was trained
    dossier["drugs"] = sorted({_slug(m["dci"]) for m in meds if m.get("dci")})
    dossier["medication_count"] = len(meds)
    dossier["allergies"] = sorted(_slug(a) for a in x.get("known_allergies") or [])
    return dossier
