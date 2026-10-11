"""D1 motor endpoints: rehabilitation plan/sessions (D1-E) and opt-in guided movement tests (D1-D)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..db import Repo, get_repo
from ..integrations import d1_motor as d1

router = APIRouter(tags=["d1-motor"])


def _patient(repo: Repo, pid: str):
    if repo.patient(pid) is None:
        raise HTTPException(404, "unknown patient")


# ------------------------------------------------------------------ rehabilitation

@router.get("/patients/{patient_id}/rehab/plan")
def rehab_plan(patient_id: str, repo: Repo = Depends(get_repo)):
    """Personalised exercise prescription (D1 engine) built from this patient's file."""
    _patient(repo, patient_id)
    return d1.rehab_plan(repo, patient_id).model_dump(mode="json")


class RehabExerciseIn(BaseModel):
    exercise_id: str
    frames: list[dict]  # {"t_ms": 250, "landmarks": {"25": [x, y, z, visibility], ...}} (MediaPipe pose indices)


class RehabSessionIn(BaseModel):
    exercises: list[RehabExerciseIn] = Field(min_length=1)
    pain_eva: int | None = Field(default=None, ge=0, le=10)
    difficulty: str | None = Field(default=None, max_length=500)


@router.post("/patients/{patient_id}/rehab/session")
def rehab_session(patient_id: str, body: RehabSessionIn, repo: Repo = Depends(get_repo)):
    _patient(repo, patient_id)
    try:
        return d1.run_rehab_session(repo, patient_id, [e.model_dump() for e in body.exercises], body.pain_eva, body.difficulty)
    except (ValueError, KeyError) as e:
        raise HTTPException(422, str(e)) from e


class RehabDemoIn(BaseModel):
    kind: str = "good"  # good | incomplete | too_deep | occluded
    pain_eva: int | None = Field(default=None, ge=0, le=10)
    difficulty: str | None = None


@router.post("/patients/{patient_id}/rehab/demo")
def rehab_demo(patient_id: str, body: RehabDemoIn, repo: Repo = Depends(get_repo)):
    """Runs the knee-flexion exercise on a made-up recording (clearly synthetic) through the real engine."""
    _patient(repo, patient_id)
    if body.kind not in ("good", "incomplete", "too_deep", "occluded"):
        raise HTTPException(422, "kind must be good | incomplete | too_deep | occluded")
    plan = d1.rehab_plan(repo, patient_id)
    ex = next((e for e in plan.exercises if e.category == "knee_flexion"), None)
    if ex is None:
        raise HTTPException(409, "no knee-flexion exercise in this patient's plan")
    side = ex.target_side if ex.target_side in ("left", "right") else "right"
    out = d1.run_rehab_session(repo, patient_id, [{"exercise_id": ex.exercise_id, "built": True,
                                                   "frames": d1.demo_knee_frames(body.kind, side)}],
                               body.pain_eva, body.difficulty, simulated=True)
    out["synthetic"] = True
    return out


@router.get("/patients/{patient_id}/rehab/history")
def rehab_history(patient_id: str, repo: Repo = Depends(get_repo)):
    _patient(repo, patient_id)
    return d1.rehab_history(repo, patient_id)


# ------------------------------------------------------------------ guided movement tests

class ConsentIn(BaseModel):
    granted: bool


@router.get("/patients/{patient_id}/motor/tests")
def motor_tests(patient_id: str, repo: Repo = Depends(get_repo)):
    _patient(repo, patient_id)
    return {"consent": d1.consent(repo, patient_id), "blocked": d1.blocked_reason(repo, patient_id),
            "tests": [{"id": k, "name": v[0], "instructions": v[1], "seconds": v[2], "demo_variants": list(d1.DEMO_VARIANTS[k])}
                      for k, v in d1.TEST_INFO.items()],
            "note": "Opt-in. Declining or stopping is recorded as 'not completed', never as a failed test."}


@router.post("/patients/{patient_id}/motor/consent")
def motor_consent(patient_id: str, body: ConsentIn, repo: Repo = Depends(get_repo)):
    _patient(repo, patient_id)
    d1.set_consent(repo, patient_id, body.granted)
    return {"consent": body.granted}


class MotorTestIn(BaseModel):
    frames: list[dict] | None = None  # phone/browser output (see d1 neuro Frame); omit with `demo`
    demo: str | None = None           # a variant name from /motor/tests (synthetic recording)
    symptoms: dict | None = None      # post-assessment answers (pain, weakness, dizziness, difficulty)


@router.get("/patients/{patient_id}/motor/history")
def motor_history(patient_id: str, repo: Repo = Depends(get_repo)):
    _patient(repo, patient_id)
    return d1.motor_history(repo, patient_id)


@router.post("/patients/{patient_id}/motor/{test}")
def motor_test(patient_id: str, test: str, body: MotorTestIn, repo: Repo = Depends(get_repo)):
    _patient(repo, patient_id)
    if test not in d1.TEST_INFO:
        raise HTTPException(404, f"unknown test; known: {list(d1.TEST_INFO)}")
    if not d1.consent(repo, patient_id):
        raise HTTPException(403, "The patient has not agreed to guided movement tests (opt-in).")
    why = d1.blocked_reason(repo, patient_id)
    if why:
        raise HTTPException(409, why)
    try:
        if body.demo:
            rec = d1.demo_recording(test, body.demo)
        elif body.frames:
            rec = d1.recording_from_json(test, {"frames": body.frames})
        else:
            raise HTTPException(422, "send `frames` or `demo`")
        out = d1.run_motor_test(repo, patient_id, rec, body.symptoms, simulated=bool(body.demo))
    except (ValueError, KeyError) as e:
        raise HTTPException(422, str(e)) from e
    out["synthetic"] = bool(body.demo)
    return out
