"""D1-F wound photos: OpenCV analysis (d1 wound) + a vision-LLM second read, attached to every dressing-change photo.

When: only photos taken during a dressing change permitted by the care plan reach this code (app/wound_photos.py
enforces the windows; the patient confirms the dressing change; nobody is asked to uncover a wound for a photo).

What:
1. Code (no AI): photo quality (retake if poor), the incision outlined on an overlay image, redness against the
   patient's own surrounding skin, comparison with the reference photo ONLY if registration shows it is the same site.
2. Vision LLM (Mistral Pixtral / Groq Llama-4-Scout / OpenRouter, whichever key is set): describes what is visible in
   structured JSON, with a confidence per finding. Diagnosis words are filtered out (app/safety/output_guard.py). In stub
   mode it only restates the code's measurements and says so.
3. Rule (code): review_suggested when the code sees clearly more / spreading redness or a larger area, or when the LLM
   reports discharge, open edges or spreading redness with medium/high confidence -> an "attention" alert for the
   clinician. Never an emergency, never a diagnosis; the photo never replaces urgent assessment.
"""

import base64
import logging
import os
import sys
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from .. import alerts, audit, llm, runner
from .. import models as m
from ..config import settings
from ..db import Repo, session_scope
from ..safety import output_guard
from .d1_bridge import D1_SRC

log = logging.getLogger("surgiguard.d1.wound")
ACTOR = "d1:wound"
AGENT = "wound_vision"
# Multimodal model per provider (the default text models such as gpt-oss cannot see images).
VISION_MODELS = {"groq": "meta-llama/llama-4-scout-17b-16e-instruct", "mistral": "pixtral-12b-latest",
                 "openrouter": "google/gemma-3-27b-it:free"}
os.environ.setdefault(f"LLM_ROUTE_{AGENT.upper()}",
                      f"{settings.llm_provider}:{os.getenv('WOUND_VISION_MODEL') or VISION_MODELS.get(settings.llm_provider, '')}")


def _d1():
    if str(D1_SRC) not in sys.path:
        sys.path.insert(0, str(D1_SRC))
    from surgiguard_d1 import wound
    return wound


def photo_bytes(url: str | None) -> bytes | None:
    from .. import wounds
    if not url:
        return None
    name = url.rsplit("/", 1)[-1]
    for folder in (wounds.UPLOADS, wounds.DEMO_DIR):
        p = folder / name
        if p.exists():
            return p.read_bytes()
    return None


# ------------------------------------------------------------------ 1. code analysis

def analyze(repo: Repo, obs: m.Observation, data: bytes) -> dict:
    """Run the OpenCV pipeline on a stored photo, save the overlay, store the result on the observation."""
    from .. import wounds
    wound = _d1()
    ref_obs = wounds.reference(repo, obs.patient_id)
    ref_bytes = photo_bytes(ref_obs.value.get("url")) if ref_obs and ref_obs.id != obs.id else None
    res = wound.analyze(data, reference=ref_bytes)
    overlay_url = None
    if res.get("_bgr") is not None:
        wounds.UPLOADS.mkdir(exist_ok=True)
        name = f"{obs.id}_overlay.jpg"
        caption = "Outlined: area measured by code (check it)" if res.get("_mask") is not None else "No wound region found"
        (wounds.UPLOADS / name).write_bytes(wound.overlay(res["_bgr"], res.get("_mask"), caption))
        overlay_url = f"/uploads/{name}"
    out = {**wound.strip_private(res), "overlay_url": overlay_url, "reference_id": ref_obs.id if ref_bytes else None}
    obs.value = {**obs.value, "d1": out}
    repo.add(obs)
    audit.log(repo, obs.patient_id, ACTOR, "wound.analyzed",
              {"quality": out["quality"]["status"], "found": out["segmentation"].get("found"),
               "comparison": (out.get("comparison") or {}).get("summary") or (out.get("comparison") or {}).get("reason")},
              "observation", obs.id)
    return out


# ------------------------------------------------------------------ 2. vision LLM

Aspect = Literal["redness", "swelling_appearance", "discharge_appearance", "wound_edges", "closure_material",
                 "scab_or_crust", "bruising", "dressing_residue", "other"]


class Finding(BaseModel):
    aspect: Aspect
    finding: str = Field(max_length=300)
    confidence: Literal["low", "medium", "high"]


class VisionReview(BaseModel):
    image_usable: bool
    retake_advice: str | None = Field(default=None, max_length=300)
    findings: list[Finding] = Field(default_factory=list, max_length=10)
    review_suggested: bool = False
    reasons: list[str] = Field(default_factory=list, max_length=6)
    uncertainty: str = Field(default="", max_length=400)


SYSTEM = """You look at a photo of a post-operative surgical wound for a care team, next to measurements computed by code.
Describe only what is VISIBLE. You do not diagnose: never write infected, infection, healed, healthy, safe, cellulitis,
abscess, sepsis or any disease name, and never give treatment or medication advice.
A photo cannot show warmth, pain, depth, or confirm what a fluid is: say "appears" and give your confidence.
Return JSON only:
{"image_usable": bool, "retake_advice": str|null,
 "findings": [{"aspect": "redness|swelling_appearance|discharge_appearance|wound_edges|closure_material|scab_or_crust|bruising|dressing_residue|other",
               "finding": "short plain sentence", "confidence": "low|medium|high"}],
 "review_suggested": bool, "reasons": ["why a clinician should look, if so"], "uncertainty": "what limits this reading"}"""


@llm.stub(AGENT)
def _stub(messages, ctx):
    """Offline: restate the code's measurements, clearly labelled as such."""
    cv = ctx.get("cv") or {}
    q, meas, comp = cv.get("quality", {}), cv.get("measurements") or {}, cv.get("comparison") or {}
    findings = []
    if meas:
        findings.append({"aspect": "redness", "finding": f"(offline, from code) redness along the wound: a* +{meas.get('redness_mean_delta_a')} vs own skin",
                         "confidence": "low"})
        cm = meas.get("closure_material") or {}
        if cm.get("staple_like_blobs"):
            findings.append({"aspect": "closure_material", "finding": f"(offline, from code) closure material visible ({cm['staple_like_blobs']} bright staple-like marks)",
                             "confidence": "low"})
    return {"image_usable": q.get("status") != "unusable", "retake_advice": "; ".join(q.get("problems") or []) or None,
            "findings": findings, "review_suggested": comp.get("trend") == "more_red",
            "reasons": [comp["summary"]] if comp.get("trend") == "more_red" else [],
            "uncertainty": "LLM offline (stub mode): no visual reading, only the code measurements."}


def _cv_brief(cv: dict) -> str:
    meas, comp = cv.get("measurements") or {}, cv.get("comparison") or {}
    keys = ("redness_mean_delta_a", "redness_area_pct", "redness_spread_ring_delta_a", "wound_area_pct_of_frame",
            "dark_crust_coloured_pct", "pale_yellow_pct", "closure_material")
    return (f"Photo quality: {cv.get('quality')}\nCode measurements: { {k: meas.get(k) for k in keys} }\n"
            f"Comparison with the reference photo: {comp.get('summary') or comp.get('reason') or 'none (first photo)'}")


def vision_review(repo: Repo, obs: m.Observation, data: bytes) -> dict:
    p = repo.patient(obs.patient_id)
    cv = obs.value.get("d1") or {}
    context = (f"Patient: {p.surgery if p else 'surgery'}; photo taken at a dressing change permitted by the care plan.\n"
               + _cv_brief(cv))
    uri = "data:image/jpeg;base64," + base64.b64encode(data).decode()
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": [{"type": "text", "text": context},
                                             {"type": "image_url", "image_url": {"url": uri}}]}]
    provider, model = llm.route(AGENT)
    try:
        raw = llm.chat_json(AGENT, messages, context={"cv": cv}, max_tokens=700)
        review = VisionReview.model_validate(raw)
        mode = llm.mode()
    except (llm.LLMUnavailable, llm.LLMBadOutput, ValidationError) as e:
        out = {"available": False, "reason": f"vision reading unavailable ({type(e).__name__}); code measurements only",
               "model": f"{provider}/{model}"}
        obs.value = {**obs.value, "vision_review": out}
        repo.add(obs)
        return out
    removed = []
    clean = []
    for f in review.findings:
        if output_guard.violations(f.finding, "clinician"):
            removed.append(f.finding)
        else:
            clean.append(f)
    review.findings = clean
    review.reasons = [r for r in review.reasons if not output_guard.violations(r, "clinician")]
    out = {"available": True, "mode": mode, "model": f"{provider}/{model}", **review.model_dump(),
           "removed_for_diagnosis_wording": removed,
           "note": "AI description of the visible wound, for clinician review. Not a diagnosis."}
    obs.value = {**obs.value, "vision_review": out}
    repo.add(obs)
    audit.log(repo, obs.patient_id, "agent:" + AGENT, "wound.vision_review",
              {"mode": mode, "review_suggested": review.review_suggested, "findings": len(clean), "removed": len(removed)},
              "observation", obs.id)
    return out


# ------------------------------------------------------------------ 3. rule

CONCERNING = {"discharge_appearance", "wound_edges", "redness"}


def decide(repo: Repo, obs: m.Observation) -> str | None:
    """Code decides whether the clinician should look; the LLM's reading is one input, never the only gate."""
    cv, vr = obs.value.get("d1") or {}, obs.value.get("vision_review") or {}
    reasons = []
    comp = cv.get("comparison") or {}
    if comp.get("available") and (comp.get("redness_spread_change", 0) >= 4 or comp.get("redness_change_delta_a", 0) >= 6):
        reasons.append(f"code: {comp['summary']}")
    if comp.get("available") and comp.get("area_change_pct", 0) >= 30:
        reasons.append(f"code: marked area {comp['area_change_pct']}% larger than the reference photo")
    if vr.get("available") and vr.get("mode") == "live" and vr.get("review_suggested"):
        strong = [f for f in vr.get("findings", []) if f["aspect"] in CONCERNING and f["confidence"] in ("medium", "high")]
        if strong:
            reasons.append("vision reading: " + "; ".join(f["finding"] for f in strong)[:300])
    if not reasons:
        return None
    a = alerts.create(repo, obs.patient_id, "attention", "Wound photo: clinician review suggested",
                      " | ".join(reasons) + " (A prompt to look at the photo, not a diagnosis.)", "rule",
                      rule="wound_review", evidence={"observation_ids": [obs.id]}, actor="rule:wound_review")
    obs.value = {**obs.value, "review_alert_id": a.id}
    repo.add(obs)
    return a.id


@runner.job("wound_review")
def _job(obs_id: str) -> None:
    with session_scope() as repo:
        obs = repo.get(m.Observation, obs_id)
        data = photo_bytes(obs.value.get("url")) if obs else None
        if obs is None or data is None:
            return
        vision_review(repo, obs, data)
        decide(repo, repo.get(m.Observation, obs_id))


def process(repo: Repo, obs: m.Observation, data: bytes) -> None:
    """Called for every stored wound photo: code analysis now (fast), vision reading + rule in the agent runner."""
    try:
        analyze(repo, obs, data)
    except Exception:  # analysis must never lose the photo itself
        log.exception("wound analysis failed for %s", obs.id)
        return
    runner.submit("wound_review", obs.id)
