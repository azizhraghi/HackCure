"""What the patient may notice today from their medicines, with reassurance and when to call the care team.

Short summaries of common product-leaflet information (FICTIONAL demo; not reviewed by a pharmacist). Matched to
the active care plan by name. A possible side effect never replaces the warning signs: every entry says when to call.
"""

import re

# key -> aliases, then per language: (common, usually mild) and (call the care team if)
GUIDE: dict[str, dict] = {
    "paracetamol": {
        "aliases": ["paracetamol", "paracétamol", "acetaminophen", "doliprane", "dafalgan", "efferalgan"],
        "en": (["Usually very well tolerated", "Occasionally mild nausea"],
               ["A skin rash or swelling", "Yellow skin or eyes", "You may have taken more than 4 g in a day"]),
        "fr": (["Généralement très bien toléré", "Parfois de légères nausées"],
               ["Une éruption cutanée ou un gonflement", "Peau ou yeux jaunes", "Plus de 4 g pris dans la journée"]),
    },
    "celecoxib": {
        "aliases": ["celecoxib", "célécoxib", "celebrex"],
        "en": (["Mild stomach upset or heartburn (take it with food)", "Headache", "Slight swelling of the ankles"],
               ["Black or bloody stools, or vomiting blood", "Chest pain or shortness of breath", "Severe stomach pain"]),
        "fr": (["Légers maux d'estomac ou brûlures (à prendre au repas)", "Maux de tête", "Chevilles un peu gonflées"],
               ["Selles noires ou sanglantes, ou vomissement de sang", "Douleur thoracique ou essoufflement", "Forte douleur au ventre"]),
    },
    "pantoprazole": {
        "aliases": ["pantoprazole", "inipomp", "eupantol", "omeprazole", "oméprazole", "esomeprazole", "ésoméprazole"],
        "en": (["Headache", "Loose stools, gas or mild nausea"],
               ["Severe or persistent watery diarrhoea", "A rash"]),
        "fr": (["Maux de tête", "Selles molles, gaz ou légères nausées"],
               ["Diarrhée liquide forte ou qui dure", "Une éruption cutanée"]),
    },
    "enoxaparin": {
        "aliases": ["enoxaparin", "énoxaparine", "enoxaparine", "lovenox", "heparin", "héparine"],
        "en": (["A small bruise or lump where you inject (very common)", "Mild itching at the injection site"],
               ["Bleeding that does not stop, or large bruises elsewhere", "Blood in urine or black stools",
                "Sudden severe headache"]),
        "fr": (["Un petit bleu ou une petite boule au point d'injection (très fréquent)", "Légères démangeaisons au point d'injection"],
               ["Un saignement qui ne s'arrête pas, ou de gros bleus ailleurs", "Sang dans les urines ou selles noires",
                "Mal de tête brutal et intense"]),
    },
    "cefuroxime": {
        "aliases": ["cefuroxime", "céfuroxime", "zinnat"],
        "en": (["Mild nausea or loose stools", "A slight change in taste"],
               ["Severe or bloody diarrhoea", "Rash, itching or swelling of the face or lips (allergy)"]),
        "fr": (["Légères nausées ou selles molles", "Goût un peu modifié"],
               ["Diarrhée forte ou sanglante", "Éruption, démangeaisons ou gonflement du visage ou des lèvres (allergie)"]),
    },
    "tramadol": {
        "aliases": ["tramadol", "contramal", "topalgic", "codeine", "codéine", "morphine", "oxycodone"],
        "en": (["Drowsiness or dizziness (get up slowly)", "Constipation", "Nausea"],
               ["Very slow breathing or you cannot stay awake", "Confusion"]),
        "fr": (["Somnolence ou vertiges (levez-vous lentement)", "Constipation", "Nausées"],
               ["Respiration très lente ou impossible de rester éveillé", "Confusion"]),
    },
}

REASSURANCE = {
    "en": "Most of these are common and pass on their own. Taking your medicines on time is helping you heal.",
    "fr": "La plupart sont fréquents et passent tout seuls. Prendre vos médicaments à l'heure vous aide à guérir.",
}
NOTE = {
    "en": "General information, not about you specifically. Warning signs always come first: call your care team.",
    "fr": "Information générale, pas spécifique à vous. Les signes d'alerte passent toujours avant : appelez votre équipe.",
}


def _key(name: str) -> str | None:
    n = (name or "").lower()
    for key, entry in GUIDE.items():
        if any(re.search(rf"\b{re.escape(a)}\b", n) for a in entry["aliases"]):
            return key
    return None


def for_plan(plan: dict, lang: str = "en") -> dict:
    lang = "fr" if lang.lower().startswith("fr") else "en"
    items = []
    for med in plan.get("medications", []):
        key = _key(med.get("name", ""))
        common, call_if = GUIDE[key][lang] if key else ([], [])
        items.append({"medication": f"{med.get('name', '')} {med.get('dose', '')}".strip(), "times": med.get("times", []),
                      "known": key is not None, "common": common, "call_if": call_if})
    return {"items": items, "reassurance": REASSURANCE[lang], "note": NOTE[lang],
            "source": "Summary of common leaflet information (demo, not pharmacist-reviewed)"}
