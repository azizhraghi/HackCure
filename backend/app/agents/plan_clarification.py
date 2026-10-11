"""Prepare focused questions from compiler warnings, retaining document sources."""
from .. import audit, models as m
from ..db import Repo
from ..notifications import notify


def prepare(repo: Repo, draft: m.PlanDraft) -> list[dict]:
    docs = [repo.get(m.Document, id_) for id_ in draft.document_ids]
    sources = [{"document_id": d.id, "filename": d.filename} for d in docs if d and d.patient_id == draft.patient_id]
    out = []
    for i, warning in enumerate(draft.warnings):
        item = warning.get("item", "Care plan")
        message = warning.get("message", "Missing information")
        low = message.lower()
        subject = "the exact dose" if "dose" in low else "the intended clock times" if "time" in low or "schedule" in low else "whether this medicine is appropriate given the recorded allergy" if "allergy" in low else "the missing or conflicting instruction"
        out.append({"id": f"{draft.id}:{i}", "item": item, "level": warning.get("level", "medium"),
                    "question": f"Please clarify {subject} for {item}.", "reason": message,
                    "sources": sources, "status": "unresolved"})
    return out


def request_review(repo: Repo, draft: m.PlanDraft, actor: str) -> dict:
    if actor != draft.patient_id:
        raise ValueError("only this patient can request plan clarification")
    questions = prepare(repo, draft)
    sent = []
    for clinician in repo.members(draft.patient_id, "clinician"):
        n = notify(repo, draft.patient_id, clinician.id, "request", "Care plan clarification requested",
                   "\n".join(q["question"] + " " + q["reason"] for q in questions),
                   "plan_draft", draft.id, dedupe_key=f"clarify:{draft.id}:{clinician.id}") if questions else None
        if n:
            sent.append(n.id)
    audit.log(repo, draft.patient_id, actor, "plan.clarification_requested",
              {"questions": questions, "notification_ids": sent}, "plan_draft", draft.id)
    return {"status": "requested" if questions else "nothing_to_clarify", "questions": questions,
            "notification_ids": sent, "delivery": "local inbox; external delivery is not configured"}
