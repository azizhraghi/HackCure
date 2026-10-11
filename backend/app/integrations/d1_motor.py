"""Developer 1 motor work <-> the shared backend: rehabilitation (D1-E) and guided movement tests (D1-D).

Rehabilitation (d1 rehab): the personalised exercise plan is built from the patient's file (surgery, post-op day, D2
risk factors, clinician limits). A session = landmark frames per exercise -> repetitions, range of motion, hold,
form, honest abstention when the camera did not see the leg. Pain is ONLY what the patient reports (EVA 0-10).
Heart rate during the session comes from the ESP32 stream, so the clinician sees effort next to the movement.

Guided movement tests (d1 neuro): six short camera tests. They measure and compare left/right and earlier sessions;
they never diagnose. A result that deserves a look becomes an "attention" alert for the clinician, never an
emergency, and a patient who already reports a warning sign is not asked to do a test (the safety lane comes first).
Consent is opt-in and recorded.

Frames come from the phone/browser (MediaPipe running on the device) or from the built-in demo generators.
Everything stored is derived features: no video is kept.
"""

import importlib.util
import sys
from datetime import datetime, timedelta
from statistics import mean

from .. import alerts, audit, clock, monitor
from .. import models as m
from ..db import Repo
from .d1_bridge import D1_SRC, ROOT

ACTOR = "d1:motor"
_SIM = None


def _d1():
    if str(D1_SRC) not in sys.path:
        sys.path.insert(0, str(D1_SRC))


def _sim():
    """d1/tests/neuro_sim.py: the team's own generators of made-up recordings (used for the demo buttons)."""
    global _SIM
    if _SIM is None:
        _d1()
        spec = importlib.util.spec_from_file_location("neuro_sim", ROOT / "d1" / "tests" / "neuro_sim.py")
        _SIM = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_SIM)
    return _SIM


# ------------------------------------------------------------------ rehabilitation

def clinical_profile(repo: Repo, patient_id: str):
    _d1()
    from surgiguard_d1.rehab import PatientClinicalProfile
    p = repo.patient(patient_id)
    plan = repo.plan(patient_id)
    cp = plan.get("clinical_profile") or {}
    text = p.surgery.lower()
    side = "right" if "right" in text or "droit" in text else "left" if "left" in text or "gauche" in text else "bilateral"
    comorb = [str(x) for x in (cp.get("risk_factors") or cp.get("comorbidities") or []) if isinstance(x, str)]
    postop_day = max(0, (clock.now().date() - p.surgery_date.date()).days)
    return PatientClinicalProfile(
        patient_id=patient_id, patient_name=p.name, age=p.age, sex="other", surgery_type=p.surgery,
        affected_side=side, surgery_date=p.surgery_date.date().isoformat(), postop_day=postop_day,
        comorbidities=comorb, mobility_level="crutches",
        clinician_restrictions=list(plan.get("clinician_restrictions", [])), doctor_notes=plan.get("doctor_notes"))


def rehab_plan(repo: Repo, patient_id: str):
    _d1()
    from surgiguard_d1.rehab import build_personalized_rehab_plan
    return build_personalized_rehab_plan(clinical_profile(repo, patient_id))


def _frames_from_json(rows: list[dict]):
    from surgiguard_d1.rehab import PoseFrame, PoseLandmark
    frames = []
    for i, r in enumerate(rows):
        lms = {int(k): PoseLandmark(x=v[0], y=v[1], z=v[2] if len(v) > 2 else 0.0, visibility=v[3] if len(v) > 3 else 1.0)
               for k, v in r["landmarks"].items()}
        frames.append(PoseFrame(frame_index=i, timestamp_ms=float(r["t_ms"]), landmarks=lms))
    return frames


def demo_knee_frames(kind: str, side: str = "right"):
    """Synthetic knee-flexion recordings: good | incomplete | too_deep | occluded (same geometry as d1's tests)."""
    _d1()
    from surgiguard_d1.rehab import PoseFrame, PoseLandmark
    from surgiguard_d1.rehab.models import LandmarkIndex as L
    left = side == "left"
    idx = (L.LEFT_HIP, L.LEFT_KNEE, L.LEFT_ANKLE) if left else (L.RIGHT_HIP, L.RIGHT_KNEE, L.RIGHT_ANKLE)
    hip, knee, ext = (0.5, 0.2), (0.5, 0.5), (0.5, 0.8)
    flex = {"good": (0.7, 0.5), "incomplete": (0.65, 0.65), "too_deep": (0.55, 0.3), "occluded": (0.7, 0.5)}[kind]
    vis = 0.1 if kind == "occluded" else 1.0
    plan = [ext] * 3 + [flex] * 12 + [ext] * 8
    if kind in ("good", "too_deep", "occluded"):
        plan += [ext] * 3 + [flex] * 12 + [ext] * 8
    frames, t = [], 0.0
    for i, a in enumerate(plan):
        t += 250.0
        pts = dict(zip(idx, (hip, knee, a)))
        frames.append(PoseFrame(frame_index=i, timestamp_ms=t, landmarks={int(k): PoseLandmark(x=v[0], y=v[1], visibility=vis)
                                                                         for k, v in pts.items()}))
    return frames


def hr_during(repo: Repo, patient_id: str, start: datetime, end: datetime) -> dict:
    """ESP32 heart rate over the session window (device readings of good quality only)."""
    rows = [o for o in repo.observations(patient_id, "hr", since=start - timedelta(seconds=30), until=end + timedelta(seconds=30))
            if o.quality == "good" and not o.simulated]
    vals = [o.value["value"] for o in rows]
    if not vals:
        return {"status": "unknown", "reason": "no usable ESP32 heart-rate reading during the session"}
    return {"status": "ok", "mean": round(mean(vals)), "peak": max(vals), "samples": len(vals), "source": "ESP32"}


def run_rehab_session(repo: Repo, patient_id: str, exercises: list[dict], pain_eva: int | None, difficulty: str | None) -> dict:
    """exercises: [{exercise_id, frames: [{t_ms, landmarks}]}] (or frames already built, for the demo)."""
    _d1()
    from surgiguard_d1.rehab import RehabSessionRunner, format_analysis_payload
    plan = rehab_plan(repo, patient_id)
    runner = RehabSessionRunner(plan, episode_id=f"ep_{patient_id}")
    for ex in exercises:
        frames = ex["frames"] if ex.get("built") else _frames_from_json(ex["frames"])
        runner.process_frame_sequence(frames, ex["exercise_id"])
    result = runner.finalize_session(patient_pain_eva=pain_eva, patient_difficulty=difficulty)
    analysis = format_analysis_payload(result)
    vitals = hr_during(repo, patient_id, clock.now() - timedelta(minutes=3), clock.now())
    out = {"session": result.model_dump(mode="json"), "analysis": analysis.model_dump(mode="json"), "heart_rate": vitals,
           "plan_id": plan.plan_id, "alerts": []}
    obs = repo.add(m.Observation(patient_id=patient_id, type="rehab_session", source="patient", unit="",
                                 value={"session_id": result.session_id, "status": result.status, "pain_eva": pain_eva,
                                        "exercises": [{"id": e.exercise_id, "name": e.exercise_name, "completed": e.completed_reps,
                                                       "incomplete": e.incomplete_reps, "target_reps": e.target_reps,
                                                       "max_rom": e.max_rom_achieved_deg, "target_rom": e.target_rom_deg,
                                                       "form": e.average_form_score, "warnings": e.guardrail_warnings}
                                                      for e in result.exercise_results],
                                        "heart_rate": vitals}))
    audit.log(repo, patient_id, ACTOR, "rehab.session", {"session_id": result.session_id, "status": result.status,
                                                         "pain_eva": pain_eva}, "observation", obs.id)
    out["observation_id"] = obs.id
    # Safety lane: patient-reported pain and unsafe ranges go to the clinician; words go through the urgent gate.
    if difficulty:
        monitor.gate_answer(repo, patient_id, difficulty, {"source": "rehab_session"}, [obs.id])
    unsafe = [w for e in result.exercise_results for w in e.guardrail_warnings]
    if pain_eva is not None and pain_eva >= 6:
        a = alerts.create(repo, patient_id, "attention", "High pain reported during rehabilitation",
                          f"Patient-reported pain {pain_eva}/10 (EVA) after rehabilitation exercises. Pain is the patient's own report.",
                          "rule", rule="rehab_pain_high", evidence={"observation_ids": [obs.id]}, actor="rule:rehab_pain_high")
        out["alerts"].append(a.id)
    if unsafe:
        a = alerts.create(repo, patient_id, "attention", "Exercise range beyond the prescribed limit",
                          "; ".join(unsafe)[:400], "rule", rule="rehab_range_exceeded",
                          evidence={"observation_ids": [obs.id]}, actor="rule:rehab_range_exceeded")
        out["alerts"].append(a.id)
    return out


def rehab_history(repo: Repo, patient_id: str, limit: int = 20) -> list[dict]:
    return [{"id": o.id, "at": o.measured_at.isoformat(), **o.value}
            for o in repo.observations(patient_id, "rehab_session", newest_first=True, limit=limit)]


# ------------------------------------------------------------------ guided movement tests

TEST_INFO = {
    "arm_hold": ("Bras tendus", "Tendez les deux bras devant vous et gardez-les levés environ 10 secondes. Filmez-vous de face.", 10),
    "smile": ("Sourire", "Visage neutre, puis un grand sourire. Regardez la caméra.", 5),
    "finger_to_nose": ("Doigt sur le nez", "Touchez votre nez avec l'index, un bras après l'autre, plusieurs fois.", 15),
    "hand_open_close": ("Mains ouvertes/fermées", "Ouvrez grand les mains puis fermez le poing, rapidement, plusieurs fois.", 10),
    "eyebrows_and_eyes": ("Sourcils et yeux", "Levez les sourcils, puis fermez fort les yeux.", 8),
    "head_and_gaze": ("Tête et regard", "Regardez la caméra, puis suivez un point à gauche et à droite avec les yeux seulement.", 8),
}

DEMO_VARIANTS = {
    "arm_hold": {"normal": {}, "left_arm_drifts": {"drift_left": 0.8}},
    "smile": {"normal": {}, "left_side_weaker": {"left": 0.25}},
    "eyebrows_and_eyes": {"normal": {}, "left_eye_closes_less": {"close_left": 0.3}},
    "finger_to_nose": {"normal": {}, "left_slower": {"period_left": 3.0}},
    "hand_open_close": {"normal": {}, "left_smaller": {"open_left": 1.0}},
    "head_and_gaze": {"normal": {}, "right_eye_lags": {"right_eye_lag": 0.5}},
}


def consent(repo: Repo, patient_id: str) -> bool:
    row = repo.first(m.Observation, m.Observation.patient_id == patient_id, m.Observation.type == "motor_consent",
                     order=m.Observation.measured_at.desc())
    return bool(row and row.value.get("granted"))


def set_consent(repo: Repo, patient_id: str, granted: bool) -> None:
    o = repo.add(m.Observation(patient_id=patient_id, type="motor_consent", source="patient", value={"granted": granted}))
    audit.log(repo, patient_id, patient_id, "motor.consent", {"granted": granted}, "observation", o.id)


def recording_from_json(test: str, payload: dict):
    _d1()
    from surgiguard_d1.neuro import Frame, Recording

    def hand(h):
        return tuple(tuple(p) for p in h) if h else None

    frames = []
    for f in payload["frames"]:
        pose = {k: tuple(v) for k, v in (f.get("pose") or {}).items()} or None
        frames.append(Frame(t=float(f["t"]), pose=pose, left_hand=hand(f.get("left_hand")), right_hand=hand(f.get("right_hand")),
                            face=f.get("face"), head=tuple(f["head"]) if f.get("head") else None, people=int(f.get("people", 1))))
    return Recording(test, tuple(frames))


def demo_recording(test: str, variant: str):
    sim = _sim()
    kwargs = DEMO_VARIANTS[test].get(variant)
    if kwargs is None:
        raise ValueError(f"variant must be one of {list(DEMO_VARIANTS[test])}")
    return getattr(sim, test)(**kwargs)


def blocked_reason(repo: Repo, patient_id: str) -> str | None:
    if any(a.level == "urgent" for a in repo.open_alerts(patient_id)):
        return "An urgent alert is open: the care team comes first. The movement test is not offered right now."
    return None


def run_motor_test(repo: Repo, patient_id: str, rec, symptoms: dict | None = None) -> dict:
    _d1()
    from surgiguard_d1.neuro import MotorResult, analyze, compare_with_previous
    result = analyze(rec)
    previous = None
    for o in repo.observations(patient_id, "motor", newest_first=True, limit=30):
        if o.value.get("test") == rec.test:
            previous = MotorResult.model_validate(o.value["result"])
            break
    changes = [c.model_dump(mode="json") for c in compare_with_previous(result, previous)] if previous else []
    obs = repo.add(m.Observation(patient_id=patient_id, type="motor", source="patient",
                                 value={"test": rec.test, "result": result.model_dump(mode="json"), "changes": changes,
                                        "symptoms": symptoms or {}}))
    audit.log(repo, patient_id, ACTOR, "motor.test", {"test": rec.test, "status": result.status,
                                                      "review_suggested": result.review_suggested}, "observation", obs.id)
    out = {"result": result.model_dump(mode="json"), "changes_since_previous": changes, "observation_id": obs.id,
           "compared_with_previous": previous is not None, "alert_id": None,
           "note": "Measurements and observations only: not a diagnosis. Camera placement can change a result."}
    if symptoms:  # post-assessment answers go through the same urgent gate as every other patient answer
        rule = monitor.gate_answer(repo, patient_id, symptoms, {"source": "motor_test", "test": rec.test}, [obs.id])
        out["urgent_gate"] = {"level": rule.level, "rule": rule.rule}
    if result.review_suggested and result.status != "not_interpretable":
        a = alerts.create(repo, patient_id, "attention", f"Movement test ({rec.test}): clinician review suggested",
                          "; ".join(result.observations)[:500] + " (A prompt to review, not a finding of illness.)",
                          "rule", rule=f"motor_review_{rec.test}", evidence={"observation_ids": [obs.id]},
                          actor=f"rule:motor_review_{rec.test}")
        out["alert_id"] = a.id
    return out


def motor_history(repo: Repo, patient_id: str, limit: int = 30) -> list[dict]:
    rows = []
    for o in repo.observations(patient_id, "motor", newest_first=True, limit=limit):
        r = o.value["result"]
        rows.append({"id": o.id, "at": o.measured_at.isoformat(), "test": o.value["test"], "status": r["status"],
                     "review_suggested": r["review_suggested"], "observations": r["observations"],
                     "changes": o.value.get("changes", [])})
    return rows
