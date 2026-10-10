"""A3 Evidence summary: validate the Investigation Agent's findings, or build a rule-based fallback.

Guarantees on every stored summary:
- every claim cites an existing observation of this patient, in the right section
  (patient_reported <- patient/caregiver sources, device_measured <- device source);
- device quality is the stored quality (never the model's opinion);
- no diagnosis wording; ai_interpretation states it is not a diagnosis;
- missing / unusable data is listed as unknown (computed by code, merged in);
- patient / caregiver messages contain no doses or medication changes.
"""

from datetime import timedelta

from pydantic import ValidationError

from .. import clock
from .. import models as m
from ..db import Repo
from ..safety import output_guard, quality

DISCLAIMER = "This is not a diagnosis."
PATIENT_SOURCES = {"patient", "caregiver_on_behalf"}


def validate(repo: Repo, patient_id: str, data: dict) -> tuple[m.EvidenceSummary | None, list[str]]:
    try:
        s = m.EvidenceSummary.model_validate(data)
    except ValidationError as e:
        return None, [f"schema: {err['loc']}: {err['msg']}" for err in e.errors()[:6]]

    errors: list[str] = []
    for claim in s.patient_reported:
        o = repo.get(m.Observation, claim.observation_id)
        if o is None or o.patient_id != patient_id:
            errors.append(f"patient_reported cites unknown observation_id {claim.observation_id}")
        elif o.source not in PATIENT_SOURCES:
            errors.append(f"{claim.observation_id} is {o.source} data; move it to device_measured")
    for claim in s.device_measured:
        o = repo.get(m.Observation, claim.observation_id)
        if o is None or o.patient_id != patient_id:
            errors.append(f"device_measured cites unknown observation_id {claim.observation_id}")
        elif o.source != "device":
            errors.append(f"{claim.observation_id} is {o.source} data; move it to patient_reported")
        else:
            claim.quality = o.quality  # stored quality wins
    if not s.patient_reported and not s.device_measured:
        errors.append("no evidence cited")

    for field, text, audience in [("what_changed", s.what_changed, "clinician"),
                                  ("ai_interpretation", s.ai_interpretation, "clinician"),
                                  ("messages.clinician", s.messages.clinician, "clinician")]:
        if "diagnosis wording" in output_guard.violations(text, audience):
            errors.append(f"{field} uses diagnosis wording; describe observations and uncertainty instead")
    if errors:
        return None, errors
    return finalize(repo, patient_id, s), []


def finalize(repo: Repo, patient_id: str, s: m.EvidenceSummary) -> m.EvidenceSummary:
    if "not a diagnosis" not in s.ai_interpretation.lower():
        s.ai_interpretation = f"{s.ai_interpretation.rstrip()} {DISCLAIMER}"
    plan = repo.plan(patient_id)
    texts = plan.get("patient_texts", {})
    if output_guard.violations(s.messages.patient, "patient"):
        s.messages.patient = texts.get("attention_next_step", "Your care team will review your recent readings.")
    if output_guard.violations(s.messages.caregiver, "caregiver"):
        s.messages.caregiver = "The care team is reviewing a change today. Please check in and keep the phone nearby."
    seen = {x.lower() for x in s.missing_or_conflicting}
    for item in missing_data(repo, patient_id):
        if item.lower() not in seen:
            s.missing_or_conflicting.append(item)
    return s


def missing_data(repo: Repo, patient_id: str) -> list[str]:
    """Computed by code so 'unknown' can never silently become 'normal'."""
    now = clock.now()
    th = repo.plan(patient_id).get("thresholds", {})
    labels = {"hr": "Heart rate", "spo2": "SpO2", "temp": "Temperature", "bp": "Blood pressure"}
    stale = {"bp": 24 * 60}
    out = []
    for metric, label in labels.items():
        rows = repo.observations(patient_id, metric, since=now - timedelta(hours=24))
        st = quality.metric_status(rows, now, stale.get(metric, th.get("stale_after_min", 240)))
        if st["status"] == "unknown":
            out.append(f"{label}: unknown ({st['reason']})")
        elif st["status"] == "unreliable":
            out.append(f"{label}: unreliable ({st['reason']})")
    for r in repo.all(m.PatientRequest, m.PatientRequest.patient_id == patient_id,
                      m.PatientRequest.status == "expired", m.PatientRequest.created_at >= now - timedelta(hours=6)):
        out.append(f"No answer to: {r.prompt}")
    return out


def fallback(repo: Repo, inv: m.Investigation, reason: str) -> m.EvidenceSummary:
    """Rule-built summary used when the LLM is unavailable, times out or fails validation twice."""
    pid = inv.patient_id
    p = repo.patient(pid)
    device, patient = [], []
    for metric in ("hr", "temp", "spo2"):
        o = repo.latest(pid, metric)
        if o:
            base = (p.baselines or {}).get(metric) if p else None
            device.append(m.DeviceClaim(text=f"Latest {metric}: {o.value.get('value')} (baseline {base})",
                                        observation_id=o.id, quality=o.quality))
    ci = next((o for o in repo.observations(pid, "checkin", newest_first=True, limit=10) if "items" in o.value), None)
    if ci:
        scores = ", ".join(f"{k} {v['scale5']}/5" for k, v in ci.value["items"].items())
        patient.append(m.PatientClaim(text=f"Latest check-in: {scores}", observation_id=ci.id))
    for o in repo.observations(pid, "med_dose", since=clock.now() - timedelta(hours=48)):
        if o.value.get("status") == "not_taken":
            patient.append(m.PatientClaim(text=f"Dose not taken: {o.value['med_id']} at {o.value['scheduled_for'][11:16]}",
                                          observation_id=o.id))
    signals = "; ".join(s["text"] for s in inv.trigger.get("signals", [])) or "Monitor deviation"
    plan = repo.plan(pid)
    s = m.EvidenceSummary(
        what_changed=signals,
        started_at=inv.started_at,
        persistent=False,
        patient_reported=patient,
        device_measured=device,
        ai_interpretation=f"Automated rule-based summary ({reason}); no AI interpretation available. {DISCLAIMER}",
        missing_or_conflicting=[f"Evidence incomplete: {reason}"],
        suggested_priority="attention",
        messages=m.SummaryMessages(
            patient=plan.get("patient_texts", {}).get("attention_next_step", "Your care team will review your readings."),
            caregiver="The care team is reviewing a change today. Please check in and keep the phone nearby.",
            clinician=f"Investigation ended without a full AI summary ({reason}). Please review the raw evidence."),
    )
    return finalize(repo, pid, s)
