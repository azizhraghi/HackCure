"""Independent deterministic review: render cited facts from stored evidence.

Free-text interpretations are explicitly unverified. This is not a clinical
validation and does not assign a model-generated confidence percentage.
"""
import json

from .. import clock, models as m
from ..db import Repo


def review(repo: Repo, patient_id: str, summary: m.EvidenceSummary) -> dict:
    checks, issues = [], []
    stale_min = repo.plan(patient_id).get("thresholds", {}).get("stale_after_min", 240)
    for claim in [*summary.patient_reported, *summary.device_measured]:
        obs = repo.get(m.Observation, claim.observation_id)
        if obs is None or obs.patient_id != patient_id:
            issues.append(f"Invalid evidence reference: {claim.observation_id}")
            continue
        age = (clock.now() - obs.measured_at).total_seconds() / 60
        freshness = "future" if age < 0 else "historical" if obs.type in ("med_dose", "photo") else "stale" if age > stale_min else "recent"
        value = json.dumps(obs.value, ensure_ascii=False, sort_keys=True, default=str)
        proposed = claim.text
        # Never present a model's paraphrase as a validated measurement. Structured
        # values and timestamps are the authoritative fact beside its citation.
        label = obs.type
        if obs.type == "med_dose":
            med = next((x for x in repo.plan(patient_id).get("medications", []) if x["id"] == obs.value.get("med_id")), {})
            label = med.get("name", "Medication") + " dose record"
        claim.text = f"{label} at {obs.measured_at.isoformat()}: {value} {obs.unit}".strip()
        checks.append({"observation_id": obs.id, "type": obs.type, "source": obs.source,
                       "value": obs.value, "unit": obs.unit, "at": obs.measured_at.isoformat(),
                       "quality": obs.quality, "freshness": freshness, "simulated": obs.simulated,
                       "proposed_text": proposed, "display_text": claim.text})
        if freshness in ("future", "stale") or obs.quality != "good":
            issues.append(f"{obs.id}: {freshness}, quality {obs.quality}; do not treat as current usable evidence.")
    # Record disagreements for the same metric and timestamp, without deciding
    # which source is correct or averaging conflicting measurements.
    groups = {}
    for check in checks:
        key = (check["type"], check["at"])
        groups.setdefault(key, []).append(check)
    for group in groups.values():
        if group[0]["type"] in ("hr", "temp", "spo2", "bp") and len({json.dumps(c["value"], sort_keys=True) for c in group}) > 1:
            issues.append("Conflicting same-time observations: " + ", ".join(c["observation_id"] for c in group))
    summary.missing_or_conflicting = list(dict.fromkeys([*summary.missing_or_conflicting, *issues]))
    return {"method": "deterministic_source_rendering", "checked_at": clock.now().isoformat(),
            "status": "needs_review" if issues else "sources_checked", "checks": checks, "issues": issues,
            "interpretation_status": "AI narrative, temporal trends and clinical interpretation require clinician review"}
