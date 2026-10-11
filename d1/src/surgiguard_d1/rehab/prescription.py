"""Personalized Rehabilitation Prescription Engine.

Generates tailored, clinician-approved rehabilitation exercise protocols based on:
1. Surgical procedure (e.g., PTG/TKR, PTH/THR, LCA/ACL, Shoulder, Spine)
2. Postoperative timeline (POD 1-7 early, POD 8-21 intermediate, POD 22+ consolidation)
3. Patient medical file (age, BMI, comorbidities such as DVT risk, hypertension, arthrose)
4. Explicit clinician orders, restrictions, and ROM ceilings.
"""

from datetime import datetime, timezone
import re
from typing import Any

from .models import (
    ExercisePrescription,
    PatientClinicalProfile,
    PatientPersonalizedPlan,
)


def _determine_postop_phase(postop_day: int) -> str:
    if postop_day <= 7:
        return f"Phase 1: Post-op Précoce & Démarrage (J{postop_day})"
    elif postop_day <= 21:
        return f"Phase 2: Récupération des Amplitudes & Verrouillage (J{postop_day})"
    elif postop_day <= 45:
        return f"Phase 3: Renforcement & Consolidation Fonctionnelle (J{postop_day})"
    else:
        return f"Phase 4: Réathlétisation & Autonomie Complète (J{postop_day})"


def _extract_doctor_angle_limit(restrictions: list[str], doctor_notes: str | None) -> float | None:
    """Detect if clinician specified a hard ROM limit in notes or restrictions."""
    all_text = " ".join(restrictions)
    if doctor_notes:
        all_text += " " + doctor_notes

    # Look for patterns like "max 90°", "flexion < 90", "ne pas dépasser 100 deg"
    match = re.search(r"(?:max(?:imum)?|ne pas d[eé]passer|limiter? [aà]|inf[eé]rieure? [aà])\s*(\d{2,3})\s*(?:°|deg|degr[eé])", all_text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def build_personalized_rehab_plan(
    profile: PatientClinicalProfile,
    override_exercises: list[ExercisePrescription] | None = None,
) -> PatientPersonalizedPlan:
    """Build a personalized, clinician-aligned rehabilitation plan for a patient.

    Adapts exercise selection, target angles, repetition targets, hold durations,
    and clinical safety boundaries according to the patient's individual medical file.
    """
    if override_exercises:
        return PatientPersonalizedPlan(
            plan_id=f"plan_{profile.patient_id}_{profile.postop_day}",
            patient_id=profile.patient_id,
            surgery_type=profile.surgery_type,
            affected_side=profile.affected_side,
            postop_phase=_determine_postop_phase(profile.postop_day),
            postop_day=profile.postop_day,
            daily_sessions=2,
            exercises=override_exercises,
            general_guardrails=["Suivre rigoureusement les consignes du chirurgien."],
            approval_status="modified_by_clinician",
        )

    surgery_lower = profile.surgery_type.lower()
    postop_day = profile.postop_day
    side = profile.affected_side
    comorbidities_lower = [c.lower() for c in profile.comorbidities]
    age = profile.age
    bmi = profile.bmi or 25.0

    # Clinician explicit overrides
    doc_angle_limit = _extract_doctor_angle_limit(profile.clinician_restrictions, profile.doctor_notes)

    exercises: list[ExercisePrescription] = []
    guardrails: list[str] = [
        "Arrêter immédiatement l'exercice en cas de douleur aiguë (> 5/10 sur l'échelle EVA) ou de malaise.",
        "Ne jamais forcer au-delà du seuil de confort articulaire prescrit.",
        "Effectuer les mouvements avec fluidité et contrôle sans à-coups.",
    ]

    # Age & BMI adaptations
    rep_modifier = 0
    hold_modifier = 0.0
    if age >= 75:
        rep_modifier -= 2  # Adapt workload for elderly patients
        guardrails.append("Patient senior : favoriser des temps de repos suffisants entre les séries.")
    if bmi >= 32.0:
        guardrails.append("Indice de masse corporelle élevé : soutien doux du membre recommandé pour limiter les contraintes.")

    # Check for DVT risk or cardiovascular risk factors
    has_dvt_risk = any(
        risk in comorbidities_lower
        for risk in ["phlébite", "thrombose", "dvt", "anticoagulation", "alitement", "obésité"]
    ) or (bmi >= 30.0)

    # -------------------------------------------------------------
    # 1. Total Knee Arthroplasty (PTG / TKR)
    # -------------------------------------------------------------
    if "ptg" in surgery_lower or "genou" in surgery_lower or "knee" in surgery_lower:
        # Base ROM progression curve for Knee Flexion
        if postop_day <= 7:
            target_flexion = 85.0
            max_safety_flexion = 95.0
            reps_flexion = max(6, 8 + rep_modifier)
        elif postop_day <= 14:
            target_flexion = 95.0
            max_safety_flexion = 110.0
            reps_flexion = max(8, 10 + rep_modifier)
        elif postop_day <= 28:
            target_flexion = 110.0
            max_safety_flexion = 125.0
            reps_flexion = max(10, 12 + rep_modifier)
        else:
            target_flexion = 120.0
            max_safety_flexion = 135.0
            reps_flexion = max(10, 15 + rep_modifier)

        # Soft tissue bulk adjustment (high BMI / obesity)
        if bmi >= 30.0:
            target_flexion = max(80.0, target_flexion - 5.0)

        # Apply clinician ceiling if prescribed
        if doc_angle_limit is not None:
            target_flexion = min(target_flexion, doc_angle_limit)
            max_safety_flexion = min(max_safety_flexion, doc_angle_limit + 5.0)
            guardrails.append(f"Consigne stricte du prescripteur : limitation d'amplitude fixée à {doc_angle_limit}°.")

        # Exercise 1: Heel Slides / Knee Flexion
        exercises.append(
            ExercisePrescription(
                exercise_id=f"ptg_heel_slides_{side}",
                name="Flexions du genou (Glissés de talon)",
                category="knee_flexion",
                target_side=side,
                target_reps=reps_flexion,
                target_sets=2,
                # The tracker measures the knee's INTERIOR angle (180 = straight, smaller = more bent), while the clinical
                # numbers above are degrees of FLEXION. Convert, otherwise the target (85 deg) sat on the wrong side of
                # the safety ceiling (95 deg) and no repetition could be both reached and safe.
                target_rom_deg=180.0 - target_flexion,
                min_start_angle_deg=165.0,  # Starts near extension
                max_safety_angle_deg=180.0 - max_safety_flexion,
                min_hold_duration_sec=2.0 + hold_modifier,
                cadence_target_bpm=12.0,
                clinical_rationale=(
                    f"Récupération de la mobilité active du genou opéré ({side}) sans forcer sur les tissus cicatriciels."
                ),
                precautions=[
                    "Garder le talon en contact avec le plan du lit ou tapis.",
                    "Ne pas tourner le pied vers l'intérieur ou l'extérieur lors de la flexion.",
                ],
                forbidden_movements=["Torsion brutale du genou", "Forçage au-delà du seuil de tolérance"],
            )
        )

        # Exercise 2: Straight Leg Raise (SLR) - quadriceps active extension lock
        slr_reps = max(6, 10 + rep_modifier)
        exercises.append(
            ExercisePrescription(
                exercise_id=f"ptg_slr_{side}",
                name="Élévations jambe tendue (SLR)",
                category="straight_leg_raise",
                target_side=side,
                target_reps=slr_reps,
                target_sets=2,
                target_rom_deg=40.0,  # 35°-45° hip elevation
                min_start_angle_deg=0.0,
                max_safety_angle_deg=60.0,  # Do not lift too high to protect lumbar spine
                min_hold_duration_sec=2.0,
                cadence_target_bpm=10.0,
                clinical_rationale=(
                    "Réveil et renforcement du muscle quadriceps avec verrouillage actif de l'extension du genou."
                ),
                precautions=[
                    "Le genou doit rester STRICTEMENT tendu (verrouillé) pendant toute la montée.",
                    "Plaquer le bas du dos au sol pour éviter les compensations lombaires.",
                ],
                forbidden_movements=["Fléchir le genou pendant l'élévation", "Cambrer le bas du dos"],
            )
        )

        # Exercise 3: Ankle Pumps (Pompes de cheville) - Venous calf pump
        exercises.append(
            ExercisePrescription(
                exercise_id=f"ptg_ankle_pumps_{side}",
                name="Pompes de cheville (Dorsiflexion / Plantarflexion)",
                category="ankle_pumps",
                target_side=side if not has_dvt_risk else "bilateral",
                target_reps=20 if has_dvt_risk else 15,
                target_sets=3,
                target_rom_deg=35.0,  # Total excursion
                min_start_angle_deg=90.0,
                max_safety_angle_deg=None,
                min_hold_duration_sec=1.0,
                cadence_target_bpm=20.0,
                clinical_rationale=(
                    "Activation de la pompe musculo-veineuse du mollet pour la prévention de la thrombose veineuse profonde (phlébite)."
                ),
                precautions=["Mouvement régulier et ample des deux pieds."],
                forbidden_movements=[],
            )
        )

    # -------------------------------------------------------------
    # 2. Total Hip Arthroplasty (PTH / THR)
    # -------------------------------------------------------------
    elif "pth" in surgery_lower or "hanche" in surgery_lower or "hip" in surgery_lower:
        guardrails.append("IMPORTANT PTH : Interdiction stricte de fléchir la hanche à plus de 90° et de croiser les jambes (risque de luxation).")
        
        # Safe heel slides with strict 80° flexion cap
        exercises.append(
            ExercisePrescription(
                exercise_id=f"pth_heel_slides_{side}",
                name="Flexions prudentes hanche-genou",
                category="knee_flexion",
                target_side=side,
                target_reps=8 + rep_modifier,
                target_sets=2,
                target_rom_deg=75.0,
                min_start_angle_deg=165.0,
                max_safety_angle_deg=85.0,  # Strict cap to prevent hip dislocation
                min_hold_duration_sec=1.5,
                cadence_target_bpm=10.0,
                clinical_rationale="Mobilisation articulaire douce dans le respect des consignes anti-luxation.",
                precautions=["Ne JAMAIS ramener le genou plus haut que le niveau du nombril (angle < 90°)."],
                forbidden_movements=["Flexion hanche > 90°", "Rotation interne", "Adduction"],
            )
        )

        # Ankle pumps are vital for PTH
        exercises.append(
            ExercisePrescription(
                exercise_id=f"pth_ankle_pumps_{side}",
                name="Pompes de cheville bilatérales",
                category="ankle_pumps",
                target_side="bilateral",
                target_reps=20,
                target_sets=3,
                target_rom_deg=35.0,
                min_start_angle_deg=90.0,
                max_safety_angle_deg=None,
                min_hold_duration_sec=1.0,
                cadence_target_bpm=20.0,
                clinical_rationale="Drainage veino-lymphatique essentiel après prothèse de hanche.",
                precautions=["Répéter régulièrement dans la journée."],
                forbidden_movements=[],
            )
        )

    # -------------------------------------------------------------
    # 3. Ligamentoplastie LCA / ACL Reconstruction
    # -------------------------------------------------------------
    elif "lca" in surgery_lower or "acl" in surgery_lower or "crois" in surgery_lower:
        target_flex = 90.0 if postop_day <= 14 else 115.0
        exercises.append(
            ExercisePrescription(
                exercise_id=f"lca_extension_slr_{side}",
                name="Verrouillage en extension & Élévation (SLR)",
                category="straight_leg_raise",
                target_side=side,
                target_reps=10 + rep_modifier,
                target_sets=3,
                target_rom_deg=40.0,
                min_start_angle_deg=0.0,
                max_safety_angle_deg=55.0,
                min_hold_duration_sec=3.0,
                cadence_target_bpm=10.0,
                clinical_rationale="L'extension complète à 0° est prioritaire pour la greffe LCA afin d'éviter le flexum.",
                precautions=["Garder la rotule bien orientée au zénith."],
                forbidden_movements=["Mouvement avec flexum résiduel"],
            )
        )
        exercises.append(
            ExercisePrescription(
                exercise_id=f"lca_flexion_{side}",
                name="Flexions progressives contrôlées",
                category="knee_flexion",
                target_side=side,
                target_reps=10,
                target_sets=2,
                target_rom_deg=target_flex,
                min_start_angle_deg=170.0,
                max_safety_angle_deg=target_flex + 10.0,
                min_hold_duration_sec=2.0,
                cadence_target_bpm=12.0,
                clinical_rationale="Récupération progressive de la flexion dans la plage autorisée.",
                precautions=["Ne pas forcer en bout de course."],
                forbidden_movements=["Tiroir antérieur non contrôlé"],
            )
        )
        exercises.append(
            ExercisePrescription(
                exercise_id=f"lca_ankle_pumps_{side}",
                name="Pompes de cheville",
                category="ankle_pumps",
                target_side=side,
                target_reps=15,
                target_sets=2,
                target_rom_deg=35.0,
                min_start_angle_deg=90.0,
                min_hold_duration_sec=1.0,
                cadence_target_bpm=20.0,
                clinical_rationale="Pompe veineuse du mollet post-ligamentoplastie.",
            )
        )

    # -------------------------------------------------------------
    # 4. Default / General Orthopedic Rehabilitation
    # -------------------------------------------------------------
    else:
        exercises.append(
            ExercisePrescription(
                exercise_id=f"general_knee_flexion_{side}",
                name="Mobilisation en flexion",
                category="knee_flexion",
                target_side=side,
                target_reps=10,
                target_sets=2,
                target_rom_deg=90.0,
                min_start_angle_deg=160.0,
                max_safety_angle_deg=110.0,
                min_hold_duration_sec=1.5,
                cadence_target_bpm=12.0,
                clinical_rationale="Entretien des amplitudes articulaires post-opératoires.",
            )
        )
        exercises.append(
            ExercisePrescription(
                exercise_id=f"general_ankle_pumps_{side}",
                name="Pompes de cheville",
                category="ankle_pumps",
                target_side="bilateral",
                target_reps=15,
                target_sets=2,
                target_rom_deg=30.0,
                min_start_angle_deg=90.0,
                min_hold_duration_sec=1.0,
                cadence_target_bpm=20.0,
                clinical_rationale="Circulation veineuse de retour.",
            )
        )

    # Append any custom clinician restrictions
    if profile.clinician_restrictions:
        for r in profile.clinician_restrictions:
            guardrails.append(f"Prescription médecin : {r}")

    plan = PatientPersonalizedPlan(
        plan_id=f"plan_{profile.patient_id}_{profile.postop_day}",
        patient_id=profile.patient_id,
        surgery_type=profile.surgery_type,
        affected_side=profile.affected_side,
        postop_phase=_determine_postop_phase(profile.postop_day),
        postop_day=profile.postop_day,
        daily_sessions=2,
        exercises=exercises,
        general_guardrails=guardrails,
        approved_by="Clinician Protocol Team",
        approval_status="approved",
    )
    return plan
