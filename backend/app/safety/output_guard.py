"""Checks on LLM text before it reaches a person. Agents may not suggest doses, change
medication or state a diagnosis. Violations are rejected (and replaced by plan/template text)."""

import re

MED_WORDS = (r"(dose|doses|dosage|medication|medicine|medicines|tablet|tablets|pill|pills|antibiotic|injection|"
             r"cefuroxime|enoxaparin|paracetamol|celecoxib|pantoprazole|ibuprofen)")

DOSE_AMOUNT = re.compile(r"\b\d+(\.\d+)?\s?(mg|mcg|µg|g|ml|units?|tablets?|pills?|capsules?)\b", re.I)
MED_CHANGE = re.compile(r"\b(stop|start|increase|decrease|double|reduce|change|switch|extra|catch[- ]up|"
                        r"take (another|an extra|two|2|a second))\b[^.!?]{0,40}\b" + MED_WORDS, re.I)
DIAGNOSIS = re.compile(
    r"\b(you have|she has|he has|patient has|this is|diagnos(is|ed) (of|with)|confirm(s|ed)?)\b[^.!?]{0,30}"
    r"\b(an? )?(infection|infected|sepsis|septic|thrombosis|dvt|embolism|pulmonary embolism|cellulitis|abscess)\b",
    re.I)


def violations(text: str | None, audience: str = "patient") -> list[str]:
    if not text:
        return []
    out = []
    if DIAGNOSIS.search(text):
        out.append("diagnosis wording")
    if audience in ("patient", "caregiver"):
        if DOSE_AMOUNT.search(text):
            out.append("dose amount")
        if MED_CHANGE.search(text):
            out.append("medication change")
    return out
