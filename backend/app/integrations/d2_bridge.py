"""Developer 2 <-> the shared backend.

1. D2A drafts the care plan: its extraction graph (20+ clinical fields) and deterministic safety graph run on
   the patient's uploaded documents. The result is mapped onto the plan-draft format, so the same code
   grounding (every medication/dose/date must appear in the documents), patient review and confirmation apply.
2. "D2 JSON" for Developer 1: the latest D2A extraction for the patient, or one built from the active plan.
3. D2B RAG: the active plan is indexed per patient so the assistant answers from this patient's plan only.
"""

import logging
import re
from datetime import date

from pydantic import ValidationError

from .. import audit, clock, runner
from .. import models as m
from ..agents import protocol
from ..db import Repo, session_scope

log = logging.getLogger("surgiguard.d2")
AGENT = "d2:protocol_compiler"
HHMM = re.compile(r"\b([01]?\d|2[0-3])[:hH]([0-5]\d)\b")
# Usual times when a document gives only "n times a day"; always flagged for the patient to check.
USUAL_TIMES = {1: ["08:00"], 2: ["08:00", "20:00"], 3: ["08:00", "14:00", "20:00"], 4: ["08:00", "12:00", "16:00", "20:00"]}
SEVERITY = {"CRITICAL": "high", "WARNING": "medium", "INFO": "low"}


# ------------------------------------------------------------------ 1. D2A -> plan draft

def start_draft(repo: Repo, patient_id: str, document_ids: list[str]) -> m.PlanDraft:
    docs = protocol.documents(repo, patient_id, document_ids)
    if not docs:
        raise ValueError("no readable documents: upload a PDF first")
    draft = repo.add(m.PlanDraft(patient_id=patient_id, document_ids=[d.id for d in docs], mode="d2"))
    audit.log(repo, patient_id, AGENT, "plan_draft.started", {"engine": "d2", "documents": [d.filename for d in docs]},
              "plan_draft", draft.id)
    runner.submit("d2_protocol", draft.id)
    return draft


@runner.job("d2_protocol")
def run(draft_id: str) -> None:
    from ..ai.graphs.protocol_graph import protocol_graph
    from ..ai.graphs.safety_graph import safety_graph
    from ..config import get_active_provider

    with session_scope() as repo:
        draft = repo.get(m.PlanDraft, draft_id)
        if draft is None or draft.status != "analyzing":
            return
        patient = repo.patient(draft.patient_id)
        docs = protocol.documents(repo, draft.patient_id, draft.document_ids)
        text = "\n\n".join(f"=== {d.filename} ===\n{d.text}" for d in docs)[:protocol.MAX_TEXT]
        mode = f"d2/{get_active_provider()}"

        def fail(error: str):
            draft.status, draft.error, draft.mode = "failed", error[:400], mode
            repo.add(draft)
            audit.log(repo, draft.patient_id, AGENT, "plan_draft.failed", {"error": draft.error}, "plan_draft", draft.id)

        state = protocol_graph.invoke({"document_text": text, "source_file": ", ".join(d.filename for d in docs),
                                       "word_count": len(text.split()), "extracted_data": None, "errors": [],
                                       "low_confidence": False})
        d2 = state.get("extracted_data")
        if d2 is None:
            return fail("D2 extraction failed: " + "; ".join(state.get("errors", []))[:300])
        safety = safety_graph.invoke({"extracted_protocol": d2, "patient_allergies": list(patient.allergies if patient else []),
                                      "safety_report": None, "deterministic_alerts": [], "needs_llm_check": False})
        report = safety.get("safety_report")
        try:
            extraction = to_extraction(d2, text)
        except ValidationError as e:
            return fail(f"D2 extraction could not be mapped: {e}"[:300])

        warnings = protocol.fix_dates(extraction, text) + protocol.ground(extraction, text, patient)
        warnings += [{"level": SEVERITY.get(a.severity, "medium"), "item": ", ".join(a.medications_involved) or a.rule_type,
                      "message": f"D2 safety check ({a.rule_type}): {a.message}"} for a in (report.alerts if report else [])]
        warnings += [{"level": "low", "item": f.label, "message": f"Missing from the documents: {f.reason}".strip()}
                     for f in d2.missing_fields]
        warnings += [{"level": "low", "item": "D2 extraction", "message": e} for e in state.get("errors", [])]

        plan = protocol.build_plan(repo.plan(draft.patient_id), extraction, draft.document_ids)
        plan["clinical_profile"] = clinical_profile(d2)
        draft.extracted = {**extraction.model_dump(), "d2": d2.model_dump(mode="json"),
                           "d2_safety": report.model_dump(mode="json") if report else None}
        draft.plan, draft.warnings, draft.status, draft.mode = plan, warnings, "ready", mode
        repo.add(draft)
        audit.log(repo, draft.patient_id, AGENT, "plan_draft.ready",
                  {"engine": "d2", "medications": len(extraction.medications),
                   "safety_status": report.status if report else None, "warnings": len(warnings)},
                  "plan_draft", draft.id)


def to_extraction(d2, text: str) -> m.ProtocolExtraction:
    """D2A ExtractedProtocol -> the draft format (D2 has no clock times or side: they come from the text or
    are proposed and flagged, never silently invented)."""
    meds = []
    for med in d2.medications:
        written = [f"{int(h):02d}:{mm}" for h, mm in HHMM.findall(med.frequency_raw or "")]
        proposed = USUAL_TIMES.get(med.frequency_per_day or 0, []) if not written else []
        name = med.commercial_name if med.commercial_name and protocol.found(med.commercial_name, text) \
            and not protocol.found(med.dci, text) else med.dci
        meds.append(m.ExtractedMedication(
            name=name, dose=med.dosage_raw or (f"{med.dosage_mg:g} mg" if med.dosage_mg else ""), route=med.route or "",
            times=written or proposed, times_inferred=not written and bool(proposed),
            frequency_text=med.frequency_raw or "", purpose=med.drug_class or "", duration_days=med.duration_days,
            as_needed=bool(re.search(r"si besoin|as needed|if needed|prn", (med.frequency_raw or "") +
                                     (med.special_instructions or ""), re.I)),
            source_quote=med.special_instructions or ""))
    side = next((s for s, pat in (("right", r"\b(droit|droite|right)\b"), ("left", r"\b(gauche|left)\b"))
                 if re.search(pat, d2.surgery_type or "", re.I)), "")
    appointments = [m.ExtractedAppointment(title=a.description, date=_iso(a.timing), source_quote=a.timing)
                    for a in d2.followup_appointments]
    return m.ProtocolExtraction(
        surgery=d2.surgery_type or "", side=side, surgery_date=_iso(d2.surgery_date), discharge_date=_iso(d2.discharge_date),
        surgeon=d2.prescriber or "", allergies=list(d2.known_allergies), medications=meds,
        activity_restrictions=[m.ExtractedItem(text=r) for r in d2.physical_restrictions],
        wound_care=[d2.general_instructions] if d2.general_instructions else [], appointments=appointments)


def _iso(value: str | None) -> str | None:
    """JJ/MM/AAAA (D2) -> YYYY-MM-DD; relative timings such as 'J+14' are not dates."""
    if not value:
        return None
    mt = re.fullmatch(r"\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*", value)
    if mt:
        try:
            return date(int(mt[3]), int(mt[2]), int(mt[1])).isoformat()
        except ValueError:
            return None
    try:
        return date.fromisoformat(value.strip()).isoformat()
    except ValueError:
        return None


def clinical_profile(d2) -> dict:
    """D2 fields the plan did not have: risk factors and context (shown to the clinician; read by D1)."""
    keys = ["patient_age", "patient_sex", "height_cm", "weight_kg", "bmi_kg_m2", "smoking_status", "diabetes",
            "hypertension", "cardiac_history", "anticoagulated_before_surgery", "renal_insufficiency",
            "hepatic_insufficiency", "asa_score", "blood_type", "anesthesia_type", "hospital_name",
            "comorbidities", "previous_surgeries"]
    data = d2.model_dump(mode="json")
    profile = {k: data.get(k) for k in keys}
    profile["bmi_class"] = d2.bmi_class
    profile["is_high_risk"] = d2.is_high_risk
    profile["missing"] = [f.field for f in d2.missing_fields]
    profile["source"] = "D2A extraction (patient documents)"
    return profile


# ------------------------------------------------------------------ 2. "D2 JSON" for Developer 1

def d2_document(repo: Repo, patient_id: str) -> dict | None:
    """What Developer 1 reads: the D2A extraction of the active plan, else one built from the plan + record."""
    patient = repo.patient(patient_id)
    if patient is None:
        return None
    plan = repo.plan(patient_id)
    draft = repo.first(m.PlanDraft, m.PlanDraft.patient_id == patient_id, m.PlanDraft.status == "confirmed",
                       order=m.PlanDraft.confirmed_at.desc())
    if draft and draft.extracted and draft.extracted.get("d2"):
        doc = dict(draft.extracted["d2"])
    else:
        profile = plan.get("clinical_profile", {})
        doc = {
            "document_type": "care_plan", "patient_age": patient.age, "surgery_type": plan.get("pathway") or patient.surgery,
            "known_allergies": list(patient.allergies),
            "medications": [{"dci": x.get("name", ""), "dosage_raw": x.get("dose"), "route": x.get("route"),
                             "frequency_per_day": len(x.get("times", [])) or None, "duration_days": x.get("duration_days"),
                             "drug_class": x.get("purpose")} for x in plan.get("medications", [])],
            "physical_restrictions": plan.get("document_info", {}).get("activity_restrictions", []),
            **{k: v for k, v in profile.items() if k in ("patient_sex", "smoking_status", "diabetes", "hypertension",
                                                          "cardiac_history", "asa_score", "bmi_kg_m2", "comorbidities")},
        }
    doc["surgery_date"] = patient.surgery_date.strftime("%d/%m/%Y")  # D1 needs it; the record is authoritative
    return {"extraction": doc}


# ------------------------------------------------------------------ 3. active plan -> D2B RAG (per patient)

_indexed: dict[str, int] = {}  # patient -> plan version already in the store


def plan_passages(plan: dict, patient: m.Patient) -> list[tuple[str, str]]:
    """(access_scope, text) passages of the active plan, using D2B's scopes."""
    info = plan.get("document_info", {})
    out = [("protocol", f"{patient.first_name}'s care plan: {plan.get('pathway', patient.surgery)}, surgery on "
                        f"{patient.surgery_date.date().isoformat()}.")]
    for med in plan.get("medications", []):
        when = ", ".join(med.get("times", [])) or ("as needed" if med.get("as_needed") else "no fixed time")
        out.append(("medications", f"Medication {med.get('name')} {med.get('dose', '')} ({med.get('purpose', '')}) "
                                   f"at {when}. If a dose is missed: {med.get('missed_dose_text', '')}"))
    for r in plan.get("rehab", []):
        out.append(("exercises", f"Exercise: {r.get('name')} {r.get('detail', '')} {', '.join(r.get('times', []))}".strip()))
    for text in info.get("activity_restrictions", []):
        out.append(("protocol", f"Restriction: {text}"))
    for text in info.get("wound_care", []):
        out.append(("protocol", f"Wound care: {text}"))
    for key in ("warning_signs", "emergency_signs"):
        for text in info.get(key, []) or []:
            out.append(("warnings", f"{'Emergency sign' if key == 'emergency_signs' else 'Warning sign'}: {text}"))
    for flag in plan.get("red_flags", []) if isinstance(plan.get("red_flags"), list) else []:
        out.append(("warnings", f"Warning sign: {flag if isinstance(flag, str) else flag.get('text', flag)}"))
    for a in plan.get("appointments", []):
        out.append(("protocol", f"Appointment: {a.get('title')} (day {a.get('day_offset', '?')} after discharge) at {a.get('time')}"))
    return [(s, t) for s, t in out if t.strip()]


def index_plan(repo: Repo, patient_id: str, force: bool = False) -> int:
    """Add the active plan to the D2B vectorstore with patient_id metadata (once per plan version)."""
    plan, patient = repo.plan(patient_id), repo.patient(patient_id)
    if patient is None or not plan:
        return 0
    version = int(plan.get("version", 0))
    if not force and _indexed.get(patient_id) == version:
        return 0
    from langchain_core.documents import Document
    from ..ai.rag.vectorstore import add_documents_to_store
    docs = [Document(page_content=t, metadata={"access_scope": s, "patient_id": patient_id, "source": "active_care_plan",
                                                "plan_version": version})
            for s, t in plan_passages(plan, patient)]
    add_documents_to_store(docs, use_semantic_chunking=False)
    _indexed[patient_id] = version
    audit.log(repo, patient_id, "d2:rag", "rag.plan_indexed", {"plan_version": version, "passages": len(docs)})
    return len(docs)
