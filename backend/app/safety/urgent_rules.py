"""S1 urgent rules. Pure functions, no I/O, no LLM. Highest priority in the system.

Thresholds come from the patient's approved plan (demo values, NOT clinical advice).
Text matching is deliberately conservative: a red-flag phrase anywhere fires, even if
negated ("no chest pain"). A false alarm is preferable to a missed emergency.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Iterable

LEVELS = {"none": 0, "info": 1, "attention": 2, "urgent": 3}

DEFAULT_THRESHOLDS = {"spo2_urgent_below": 90, "temp_attention_at": 38.5, "temp_urgent_at": 39.5}


@dataclass(frozen=True)
class RuleResult:
    level: str = "none"  # none | info | attention | urgent
    rule: str | None = None
    reason: str = ""
    matched: tuple[str, ...] = field(default_factory=tuple)
    investigate: bool = False

    @property
    def urgent(self) -> bool:
        return self.level == "urgent"


NONE = RuleResult()


def worst(results: Iterable[RuleResult]) -> RuleResult:
    best = NONE
    for r in results:
        if LEVELS[r.level] > LEVELS[best.level]:
            best = r
    return best


def normalize(text: str) -> str:
    # Drop apostrophes first so "can’t" (phone keyboards) == "can't" == "cant".
    t = re.sub(r"['’`´]", "", text)
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t).strip()


def _num(value: Any) -> float | None:
    if isinstance(value, dict):
        value = value.get("value")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def evaluate_vital(metric: str, value: Any, quality: str, thresholds: dict | None = None) -> RuleResult:
    """Unusable readings never trigger urgent alerts; they are flagged instead (see quality.py)."""
    th = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    v = _num(value)
    if v is None:
        return NONE
    if quality == "unusable":
        return RuleResult("info", "unusable_reading", f"{metric} reading {v:g} is unusable and was ignored")
    if metric == "spo2" and v < th["spo2_urgent_below"]:
        if quality == "good":
            return RuleResult("urgent", "spo2_low", f"SpO2 {v:g}% below {th['spo2_urgent_below']}% (good signal)")
        return RuleResult("attention", "spo2_low_questionable",
                          f"SpO2 {v:g}% below {th['spo2_urgent_below']}% but signal quality is questionable",
                          investigate=True)
    if metric == "temp":
        if v >= th["temp_urgent_at"]:
            return RuleResult("urgent", "temp_very_high", f"Temperature {v:g}°C ≥ {th['temp_urgent_at']}°C")
        if v >= th["temp_attention_at"]:
            return RuleResult("attention", "temp_high", f"Temperature {v:g}°C ≥ {th['temp_attention_at']}°C",
                              investigate=True)
    return NONE


def evaluate_text(text: str | None, phrases: Iterable[str]) -> RuleResult:
    if not text:
        return NONE
    t = normalize(text)
    hits = tuple(p for p in phrases if re.search(r"\b" + re.escape(normalize(p)), t))
    if hits:
        return RuleResult("urgent", "red_flag_text", f"Red-flag symptom reported: {', '.join(hits)}", hits)
    return NONE


def evaluate_chips(chips: Iterable[str] | None, red_chips: Iterable[str]) -> RuleResult:
    red = set(red_chips)
    hits = tuple(c for c in (chips or []) if c in red)
    if hits:
        return RuleResult("urgent", "red_flag_symptom", f"Red-flag symptom reported: {', '.join(hits)}", hits)
    return NONE


def evaluate_answer(answer: Any, plan: dict) -> RuleResult:
    """Gate for every patient/caregiver answer collected by any agent.

    Walks any nested structure: strings are checked against phrases, `chips` lists against red chips.
    """
    rf = plan.get("red_flags", {})
    phrases, chips = rf.get("phrases", []), rf.get("chips", [])
    results: list[RuleResult] = []

    def walk(x, key=None):
        if isinstance(x, str):
            results.append(evaluate_text(x, phrases))
            if key == "chips" or x in chips:
                results.append(evaluate_chips([x], chips))
        elif isinstance(x, dict):
            for k, v in x.items():
                walk(v, k)
        elif isinstance(x, (list, tuple)):
            for v in x:
                walk(v, key)

    walk(answer)
    return worst(results)


def evaluate_observation(obs_type: str, value: Any, quality: str, plan: dict) -> RuleResult:
    if obs_type in ("hr", "spo2", "temp", "bp"):
        return evaluate_vital(obs_type, value, quality, plan.get("thresholds"))
    if obs_type in ("checkin", "photo", "movement", "med_dose"):
        return evaluate_answer(value, plan)
    return NONE
