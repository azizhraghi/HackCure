"""Checks on LLM text before it reaches a person. Agents may not suggest doses, change
medication or state a diagnosis. Violations are rejected (and replaced by plan/template text)."""

import re

MED_WORDS = (r"(dose|doses|dosage|medication|medicine|medicines|tablet|tablets|pill|pills|antibiotic|injection|"
             r"cefuroxime|enoxaparin|paracetamol|celecoxib|pantoprazole|ibuprofen)")
CONDITIONS = (r"(infection|infected|sepsis|septic|thrombosis|dvt|embolism|pulmonary embolism|cellulitis|abscess|"
              r"dehydration|pneumonia)")

DOSE_AMOUNT = re.compile(r"\b\d+(\.\d+)?\s?(mg|mcg|µg|g|ml|units?|tablets?|pills?|capsules?)\b", re.I)
MED_CHANGE = re.compile(r"\b(stop|start|increase|decrease|double|reduce|change|switch|extra|catch[- ]up|"
                        r"take (another|an extra|two|2|a second))\b[^.!?]{0,40}\b" + MED_WORDS, re.I)
DIAGNOSIS = re.compile(r"\b(you have|she has|he has|patient has|this is|diagnos(is|ed) (of|with)|confirm(s|ed)?)\b"
                       r"[^.!?]{0,30}\b(an? )?" + CONDITIONS + r"\b", re.I)
# Hedged speculation about a named condition is still diagnosis-flavoured wording.
SPECULATION = re.compile(r"\b(possible|potential|suspected|likely|probable|signs? of|assess(ing)? for|rule out|"
                         r"consistent with|suggestive of|indicative of|concern for)\b[^.!?]{0,25}\b" + CONDITIONS,
                         re.I)
# Patient messages may not ask for tests: requests go through the request tools (max 2, plan-approved).
ACTION_REQUEST = re.compile(r"\b(take|measure|check|record|send|upload)\b[^.!?]{0,30}\b"
                            r"(temperature|oxygen|spo2|blood pressure|heart rate|pulse|photo|picture)", re.I)


def violations(text: str | None, audience: str = "patient") -> list[str]:
    """audience: patient (questions), patient_message (final next-step text), caregiver, clinician."""
    if not text:
        return []
    out = []
    if DIAGNOSIS.search(text) or SPECULATION.search(text):
        out.append("diagnosis wording")
    if audience == "patient_message" and ACTION_REQUEST.search(text):
        out.append("asks the patient for a test outside the request tools")
    if audience in ("patient", "patient_message", "caregiver"):
        if DOSE_AMOUNT.search(text):
            out.append("dose amount")
        if MED_CHANGE.search(text):
            out.append("medication change")
    return out
