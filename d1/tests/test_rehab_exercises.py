"""Comprehensive tests for SurgiGuard Rehabilitation Pose Estimation & Personalization.

Validates:
1. 2D/3D angle mathematics and jitter smoothing.
2. Personalized exercise plan generation across diverse clinical profiles (PTG, PTH, LCA, Elderly, Obese).
3. Knee flexion FSM repetition tracking, hold timing, and incomplete repetition detection.
4. Straight leg raise quadriceps extension locking checks and lag detection.
5. Ankle pumps repetition counting.
6. Session runner and standard analysis.completed contract compliance.
7. Honest abstention on low-visibility camera feeds.
"""

import pytest

from surgiguard_d1.rehab.angles import (
    AngleSmoother,
    calculate_angle_2d,
    calculate_angle_3d,
    calculate_joint_angle_from_landmarks,
)
from surgiguard_d1.rehab.evaluator import format_analysis_payload
from surgiguard_d1.rehab.exercises.ankle_pumps import AnklePumpsTracker
from surgiguard_d1.rehab.exercises.knee_flexion import KneeFlexionTracker
from surgiguard_d1.rehab.exercises.leg_raise import StraightLegRaiseTracker
from surgiguard_d1.rehab.models import (
    ExercisePrescription,
    LandmarkIndex,
    PatientClinicalProfile,
    PoseFrame,
    PoseLandmark,
)
from surgiguard_d1.rehab.prescription import build_personalized_rehab_plan
from surgiguard_d1.rehab.session import RehabSessionRunner


# ---------------------------------------------------------------------------
# Helpers for synthetic landmark generation
# ---------------------------------------------------------------------------


def make_landmark(x: float, y: float, z: float = 0.0, visibility: float = 1.0) -> PoseLandmark:
    return PoseLandmark(x=x, y=y, z=z, visibility=visibility, presence=1.0)


def create_knee_frame(
    frame_idx: int,
    ts_ms: float,
    hip: tuple[float, float],
    knee: tuple[float, float],
    ankle: tuple[float, float],
    side: str = "right",
    visibility: float = 1.0,
) -> PoseFrame:
    is_left = side.lower() == "left"
    hip_idx = LandmarkIndex.LEFT_HIP if is_left else LandmarkIndex.RIGHT_HIP
    knee_idx = LandmarkIndex.LEFT_KNEE if is_left else LandmarkIndex.RIGHT_KNEE
    ankle_idx = LandmarkIndex.LEFT_ANKLE if is_left else LandmarkIndex.RIGHT_ANKLE

    landmarks = {
        hip_idx: make_landmark(hip[0], hip[1], visibility=visibility),
        knee_idx: make_landmark(knee[0], knee[1], visibility=visibility),
        ankle_idx: make_landmark(ankle[0], ankle[1], visibility=visibility),
    }
    return PoseFrame(
        frame_index=frame_idx,
        timestamp_ms=ts_ms,
        landmarks=landmarks,
    )


# ---------------------------------------------------------------------------
# Test Suite 1: Geometry & Angle Smoothing
# ---------------------------------------------------------------------------


def test_calculate_angle_2d():
    # Straight horizontal line: (0, 0) -> (1, 0) -> (2, 0) should be 180°
    angle_180 = calculate_angle_2d((0.0, 0.0), (1.0, 0.0), (2.0, 0.0))
    assert abs(angle_180 - 180.0) < 1e-4

    # Right angle: (1, 1) -> (1, 0) -> (2, 0) should be 90°
    angle_90 = calculate_angle_2d((1.0, 1.0), (1.0, 0.0), (2.0, 0.0))
    assert abs(angle_90 - 90.0) < 1e-4

    # 45 degree angle: (2, 1) -> (1, 0) -> (2, 0)
    angle_45 = calculate_angle_2d((2.0, 1.0), (1.0, 0.0), (2.0, 0.0))
    assert abs(angle_45 - 45.0) < 1e-4


def test_calculate_angle_3d():
    angle_90_3d = calculate_angle_3d(
        (0.0, 1.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0)
    )
    assert abs(angle_90_3d - 90.0) < 1e-4


def test_visibility_gating():
    landmarks = {
        LandmarkIndex.RIGHT_HIP: make_landmark(0.5, 0.2, visibility=0.9),
        LandmarkIndex.RIGHT_KNEE: make_landmark(0.5, 0.5, visibility=0.3),  # Low visibility!
        LandmarkIndex.RIGHT_ANKLE: make_landmark(0.5, 0.8, visibility=0.9),
    }
    angle, status = calculate_joint_angle_from_landmarks(
        landmarks,
        LandmarkIndex.RIGHT_HIP,
        LandmarkIndex.RIGHT_KNEE,
        LandmarkIndex.RIGHT_ANKLE,
        min_visibility=0.65,
    )
    assert angle is None
    assert status == "low_visibility"


def test_angle_smoother_outlier_rejection():
    smoother = AngleSmoother(window_size=5, alpha=0.5)

    # Steady 90° stream with a single noisy artifact spike (150°)
    angles = [90.0, 90.5, 90.0, 150.0, 90.2, 90.0]
    smoothed_results = [smoother.add(a) for a in angles]

    # The spike at index 3 should be heavily dampened by median filtering
    assert smoothed_results[3] < 115.0


# ---------------------------------------------------------------------------
# Test Suite 2: Patient Profile Personalization Engine
# ---------------------------------------------------------------------------


def test_personalization_sarah_miller_ptg():
    """Sarah Miller: 64 yo, F, PTG droite, POD 10, BMI 31.2, Arthrose, Obésité."""
    profile = PatientClinicalProfile(
        patient_id="pat_sarah_miller",
        patient_name="Sarah Miller",
        age=64,
        sex="F",
        surgery_type="PTG droite",
        affected_side="right",
        surgery_date="2025-06-04",
        postop_day=10,
        bmi=31.2,
        comorbidities=["arthrose", "obésité"],
        mobility_level="crutches",
    )

    plan = build_personalized_rehab_plan(profile)

    assert plan.patient_id == "pat_sarah_miller"
    assert plan.affected_side == "right"
    assert len(plan.exercises) == 3

    # Check exercise 1: Knee flexion adapted to right side and POD 10
    ex_flex = plan.exercises[0]
    assert ex_flex.category == "knee_flexion"
    assert ex_flex.target_side == "right"
    # Target ROM adjusted for POD 10 (target 95° - 5° for BMI > 30 = 90°)
    assert ex_flex.target_rom_deg == 90.0

    # Check exercise 2: SLR
    ex_slr = plan.exercises[1]
    assert ex_slr.category == "straight_leg_raise"
    assert ex_slr.target_side == "right"

    # Check exercise 3: Ankle pumps bilateral due to obesity / DVT risk
    ex_pump = plan.exercises[2]
    assert ex_pump.category == "ankle_pumps"
    assert ex_pump.target_side == "bilateral"
    assert ex_pump.target_reps == 20


def test_personalization_elderly_pth_with_doctor_ceiling():
    """Elderly patient (79 yo) with Total Hip Replacement & strict 80° flexion ceiling."""
    profile = PatientClinicalProfile(
        patient_id="pat_jean_dupont",
        patient_name="Jean Dupont",
        age=79,
        sex="M",
        surgery_type="PTH gauche",
        affected_side="left",
        surgery_date="2025-06-01",
        postop_day=6,
        bmi=24.0,
        comorbidities=["hypertension"],
        clinician_restrictions=["Interdiction stricte flexion hanche > 85°", "Pas d'adduction"],
        doctor_notes="Limiter flexion à 80 deg.",
    )

    plan = build_personalized_rehab_plan(profile)

    # Verifies elderly adaptation (reduced reps)
    ex_heel = plan.exercises[0]
    assert ex_heel.target_reps <= 8
    # Verifies max safety angle ceiling from doctor restriction
    assert ex_heel.max_safety_angle_deg <= 85.0
    # Verifies PTH dislocation warning included in guardrails
    assert any("luxation" in g.lower() for g in plan.general_guardrails)


def test_personalization_young_acl_reconstruction():
    """Young athlete (24 yo) with ACL reconstruction (LCA), POD 14."""
    profile = PatientClinicalProfile(
        patient_id="pat_lucas_martin",
        patient_name="Lucas Martin",
        age=24,
        sex="M",
        surgery_type="Ligamentoplastie LCA",
        affected_side="left",
        surgery_date="2025-06-01",
        postop_day=14,
        bmi=22.5,
        comorbidities=[],
    )

    plan = build_personalized_rehab_plan(profile)

    # Verifies extension SLR with 3s hold is prioritized
    assert plan.exercises[0].category == "straight_leg_raise"
    assert plan.exercises[0].min_hold_duration_sec == 3.0
    assert "extension complète" in plan.exercises[0].clinical_rationale.lower()


# ---------------------------------------------------------------------------
# Test Suite 3: Knee Flexion Tracking FSM
# ---------------------------------------------------------------------------


def test_knee_flexion_successful_and_incomplete_reps():
    prescription = ExercisePrescription(
        exercise_id="test_knee_flex",
        name="Flexions du genou",
        category="knee_flexion",
        target_side="right",
        target_reps=2,
        target_rom_deg=90.0,
        min_start_angle_deg=170.0,
        max_safety_angle_deg=80.0,
        min_hold_duration_sec=1.5,
        allowed_angle_slack_deg=5.0,
    )
    tracker = KneeFlexionTracker(prescription)

    hip = (0.5, 0.2)
    knee = (0.5, 0.5)
    ankle_ext = (0.5, 0.8)  # ~180° extension line
    ankle_flex = (0.7, 0.5)  # ~90° flexion angle at knee

    # Frames 0-2: Baseline extension to prime the smoother
    for i in range(3):
        tracker.process_frame(create_knee_frame(i, i * 100.0, hip, knee, ankle_ext))
    assert len(tracker.completed_reps) == 0

    # --- REP 1: Complete successful repetition ---
    # Frames 3-14: Hold at ~90° flexion for ~12 frames (plenty for smoother + hold)
    for i in range(3, 15):
        tracker.process_frame(create_knee_frame(i, i * 250.0, hip, knee, ankle_flex))

    # Frames 15-22: Return to extension (multiple frames for smoother to converge)
    for i in range(15, 23):
        tracker.process_frame(create_knee_frame(i, 4000.0 + i * 250.0, hip, knee, ankle_ext))

    assert len(tracker.completed_reps) == 1, f"Expected 1 completed rep, got {len(tracker.completed_reps)}"
    assert tracker.completed_reps[0].completed is True
    assert tracker.completed_reps[0].target_met is True
    assert tracker.completed_reps[0].hold_duration_seconds >= 1.0

    # --- REP 2: Incomplete repetition (fails to reach target ROM) ---
    # ankle_partial creates ~135° angle: below starting threshold (145°) to leave IDLE,
    # but far above target (95°) so it never reaches peak → incomplete
    ankle_partial = (0.65, 0.65)
    for i in range(23, 33):
        tracker.process_frame(create_knee_frame(i, 10000.0 + i * 200.0, hip, knee, ankle_partial))
    # Return to extension without ever having reached target
    for i in range(33, 43):
        tracker.process_frame(create_knee_frame(i, 14000.0 + i * 200.0, hip, knee, ankle_ext))

    assert len(tracker.completed_reps) == 1
    assert len(tracker.incomplete_reps) >= 1
    assert tracker.incomplete_reps[0].completed is False
    assert tracker.incomplete_reps[0].incomplete_reason == "insufficient_rom"


def test_knee_flexion_safety_ceiling_violation():
    prescription = ExercisePrescription(
        exercise_id="test_knee_flex_safety",
        name="Flexions prudentes",
        category="knee_flexion",
        target_side="right",
        target_reps=5,
        target_rom_deg=90.0,
        min_start_angle_deg=170.0,
        max_safety_angle_deg=85.0,  # Strict safety ceiling!
        min_hold_duration_sec=1.0,
    )
    tracker = KneeFlexionTracker(prescription)

    hip = (0.5, 0.2)
    knee = (0.5, 0.5)
    # Extreme acute angle flexion (e.g. 50°)
    ankle_extreme = (0.45, 0.25)

    frame = create_knee_frame(1, 100.0, hip, knee, ankle_extreme)
    result = tracker.process_frame(frame)

    assert result["safety_alert"] is not None
    assert "dépassant le plafond prescrit" in result["safety_alert"]
    assert len(tracker.guardrail_warnings) >= 1


# ---------------------------------------------------------------------------
# Test Suite 4: Straight Leg Raise (SLR) Extension Locking
# ---------------------------------------------------------------------------


def test_straight_leg_raise_quad_lag_detection():
    prescription = ExercisePrescription(
        exercise_id="test_slr",
        name="Élévations jambe tendue",
        category="straight_leg_raise",
        target_side="right",
        target_reps=5,
        target_rom_deg=40.0,
        min_start_angle_deg=0.0,
        min_hold_duration_sec=1.5,
    )
    tracker = StraightLegRaiseTracker(prescription)

    # Patient raises leg with knee bent (knee angle ~ 140° instead of locked 180°)
    shoulder = make_landmark(0.5, 0.05)
    hip = make_landmark(0.5, 0.3)
    # Leg elevated: knee is up and forward
    knee = make_landmark(0.7, 0.15)
    # Ankle bent backwards (creates flexed knee)
    ankle = make_landmark(0.9, 0.3)

    landmarks = {
        LandmarkIndex.RIGHT_SHOULDER: shoulder,
        LandmarkIndex.RIGHT_HIP: hip,
        LandmarkIndex.RIGHT_KNEE: knee,
        LandmarkIndex.RIGHT_ANKLE: ankle,
    }
    frame = PoseFrame(frame_index=1, timestamp_ms=500.0, landmarks=landmarks)

    tracker.process_frame(frame)
    assert any("verrouillage_extension_insuffisant_quadriceps" in note for note in tracker.rep_form_notes)


# ---------------------------------------------------------------------------
# Test Suite 5: Full Session Runner & Standard Analysis Payload Contract
# ---------------------------------------------------------------------------


def test_rehab_session_runner_and_contract_payload():
    profile = PatientClinicalProfile(
        patient_id="pat_sarah_miller",
        patient_name="Sarah Miller",
        age=64,
        sex="F",
        surgery_type="PTG droite",
        affected_side="right",
        surgery_date="2025-06-04",
        postop_day=10,
        bmi=31.2,
        comorbidities=["arthrose", "obésité"],
    )
    plan = build_personalized_rehab_plan(profile)
    runner = RehabSessionRunner(plan=plan, episode_id="ep_ptg_2025_001")

    # Feed a series of frames for exercise 1
    ex1_id = plan.exercises[0].exercise_id
    runner.set_current_exercise(ex1_id)

    hip = (0.5, 0.2)
    knee = (0.5, 0.5)
    ankle_ext = (0.5, 0.8)
    ankle_flex = (0.7, 0.5)

    # Frame 0: rest
    runner.process_frame(create_knee_frame(0, 0.0, hip, knee, ankle_ext))
    # Frames 1-8: hold at 90°
    for i in range(1, 9):
        runner.process_frame(create_knee_frame(i, i * 250.0, hip, knee, ankle_flex))
    # Frame 9: return to rest
    runner.process_frame(create_knee_frame(9, 2300.0, hip, knee, ankle_ext))

    # Finalize session with patient-reported pain (EVA 3/10)
    session_result = runner.finalize_session(
        patient_pain_eva=3,
        patient_difficulty="modéré",
    )

    assert session_result.status == "complete"
    assert session_result.patient_reported_pain_eva == 3
    assert session_result.patient_reported_difficulty == "modéré"

    # Convert to standard AnalysisInput (analysis.completed schema)
    payload = format_analysis_payload(session_result)

    assert payload.analysis_type == "rehabilitation"
    assert payload.status == "complete"
    assert payload.quality.status == "usable"
    assert len(payload.observations) >= 3
    assert len(payload.evidence) >= 1
    # Clinician safety: payload must NOT include any autonomous diagnosis
    assert not hasattr(payload, "diagnosis")


def test_rehab_session_honest_abstention():
    """Verify that when landmark visibility is critically poor, the engine abstains."""
    profile = PatientClinicalProfile(
        patient_id="pat_occluded",
        age=50,
        sex="M",
        surgery_type="PTG droite",
        affected_side="right",
        surgery_date="2025-06-01",
        postop_day=5,
    )
    plan = build_personalized_rehab_plan(profile)
    runner = RehabSessionRunner(plan=plan)

    hip = (0.5, 0.2)
    knee = (0.5, 0.5)
    ankle = (0.5, 0.8)

    # Send 10 heavily occluded frames (visibility = 0.1)
    for i in range(10):
        frame = create_knee_frame(i, i * 100.0, hip, knee, ankle, visibility=0.1)
        runner.process_frame(frame)

    result = runner.finalize_session()

    assert result.status == "abstained"
    assert "camera_coverage_critically_low" in result.quality_flags

    payload = format_analysis_payload(result)
    assert payload.status == "abstained"
    assert payload.quality.status == "unusable"


@pytest.mark.parametrize("postop_day", [3, 10, 20, 40])
def test_knee_flexion_target_is_reachable_and_below_the_safety_ceiling(postop_day):
    """Prescribed flexion (degrees of bend) must become a knee angle (180 = straight) that is reachable AND safe."""
    profile = PatientClinicalProfile(patient_id="p", age=60, sex="F", surgery_type="PTG droite", affected_side="right",
                                     surgery_date="2025-06-01", postop_day=postop_day)
    ex = build_personalized_rehab_plan(profile).exercises[0]
    assert ex.category == "knee_flexion"
    assert ex.max_safety_angle_deg < ex.target_rom_deg  # the ceiling is deeper than the target
    assert ex.target_rom_deg + ex.allowed_angle_slack_deg > ex.max_safety_angle_deg - 5.0
