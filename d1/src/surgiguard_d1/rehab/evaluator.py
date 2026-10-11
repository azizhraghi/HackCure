"""Integration adapter formatting rehab session outcomes into standard analysis.completed payloads.

Conforms strictly to the shared SurgiGuard contract (observations, quality, evidence, limitations)
without any autonomous diagnosis field.
"""

from datetime import datetime, timezone
from typing import Any

from ..physiology.models import Evidence, Quality
from ..twin.models import AnalysisInput
from .models import RehabSessionResult


def format_analysis_payload(
    session_result: RehabSessionResult,
    model_version: str = "surgiguard-rehab-cv-v1.0.0",
) -> AnalysisInput:
    """Transform RehabSessionResult into standard analysis.completed payload."""
    observations: list[dict[str, Any]] = []
    evidence: list[Evidence] = []
    limitations: list[str] = list(session_result.limitations)

    for ex in session_result.exercise_results:
        # 1. Primary ROM observation
        obs_rom = {
            "code": f"rehab_{ex.exercise_id}_max_rom_deg",
            "name": f"{ex.exercise_name} - Amplitude maximale atteinte",
            "value": ex.max_rom_achieved_deg,
            "unit": "degrees",
            "target_value": ex.target_rom_deg,
            "target_met": ex.target_met,
            "side": ex.target_side,
        }
        observations.append(obs_rom)

        # 2. Completed repetitions observation
        obs_reps = {
            "code": f"rehab_{ex.exercise_id}_completed_reps",
            "name": f"{ex.exercise_name} - Répétitions validées",
            "value": ex.completed_reps,
            "unit": "reps",
            "target_value": ex.target_reps,
            "incomplete_reps": ex.incomplete_reps,
            "side": ex.target_side,
        }
        observations.append(obs_reps)

        # 3. Form quality and hold time
        obs_form = {
            "code": f"rehab_{ex.exercise_id}_form_score",
            "name": f"{ex.exercise_name} - Score de qualité posturale",
            "value": ex.average_form_score,
            "unit": "ratio",
            "mean_hold_seconds": ex.mean_hold_duration_sec,
            "side": ex.target_side,
        }
        observations.append(obs_form)

        # Link evidence
        evidence.append(
            Evidence(
                evidence_id=f"ev_{session_result.session_id}_{ex.exercise_id}",
                kind="analysis",
                resource_id=f"rehab_{ex.exercise_id}",
                resource_version="1",
                observed_at=session_result.session_end_time,
                locator=f"exercise/{ex.exercise_id}",
            )
        )

    # Patient reported pain observation (if available)
    if session_result.patient_reported_pain_eva is not None:
        observations.append(
            {
                "code": "patient_reported_pain_eva_post_rehab",
                "name": "Douleur ressentie après rééducation (Auto-évaluation patient)",
                "value": session_result.patient_reported_pain_eva,
                "unit": "scale_0_10",
                "difficulty_feedback": session_result.patient_reported_difficulty,
            }
        )
        evidence.append(
            Evidence(
                evidence_id=f"ev_{session_result.session_id}_feedback",
                kind="symptom",
                resource_id=f"rehab_feedback_{session_result.session_id}",
                resource_version="1",
                observed_at=session_result.session_end_time,
                locator="patient_reported/pain_eva",
            )
        )

    # Determine Quality struct
    if session_result.status == "complete":
        quality_status = "usable"
        reasons = session_result.quality_flags
        usable_for = ["twin_functional_trajectory", "clinician_dashboard", "rehab_progression_review"]
    elif session_result.status == "limited":
        quality_status = "limited"
        reasons = session_result.quality_flags
        usable_for = ["clinician_dashboard_annotated"]
    else:
        quality_status = "unusable"
        reasons = session_result.quality_flags or ["insufficient_pose_confidence"]
        usable_for = []

    quality = Quality(
        status=quality_status,
        reasons=reasons,
        usable_for=usable_for,
    )

    return AnalysisInput(
        analysis_id=f"analysis_rehab_{session_result.session_id}",
        analysis_type="rehabilitation",
        status=session_result.status,
        observations=observations,
        quality=quality,
        evidence=evidence,
        limitations=limitations,
        model_version=model_version,
        created_at=datetime.now(timezone.utc),
    )
