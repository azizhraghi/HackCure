from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app.safety import quality, urgent_rules as ur
from seed.demo_seed import PLAN

TH = PLAN["thresholds"]


def test_spo2_88_good_is_urgent():
    r = ur.evaluate_vital("spo2", {"value": 88}, "good", TH)
    assert r.urgent and r.rule == "spo2_low"


def test_spo2_88_unusable_not_urgent_but_flagged():
    r = ur.evaluate_vital("spo2", {"value": 88}, "unusable", TH)
    assert not r.urgent and r.level == "info" and r.rule == "unusable_reading"


def test_spo2_88_questionable_needs_attention_not_urgent():
    r = ur.evaluate_vital("spo2", 88, "questionable", TH)
    assert r.level == "attention" and r.investigate


@pytest.mark.parametrize("temp,level", [(37.9, "none"), (38.5, "attention"), (39.4, "attention"), (39.5, "urgent")])
def test_temperature_levels(temp, level):
    r = ur.evaluate_vital("temp", temp, "good", TH)
    assert r.level == level
    if level == "attention":
        assert r.investigate


@pytest.mark.parametrize("text", [
    "I have severe breathlessness since this morning",
    "chest pain when I stand",
    "I fainted in the kitchen",
    "I can’t breathe properly",  # curly apostrophe from a phone keyboard
    "j'ai une douleur thoracique",
    "pain in my calf and it is swollen, calf swelling",
])
def test_red_flag_phrases_are_urgent(text):
    assert ur.evaluate_text(text, PLAN["red_flags"]["phrases"]).urgent


def test_benign_text_is_not_urgent():
    assert ur.evaluate_text("A bit tired, knee is stiff", PLAN["red_flags"]["phrases"]).level == "none"


def test_red_flag_chip_and_nested_answer():
    assert ur.evaluate_chips(["nausea", "shortness_of_breath"], PLAN["red_flags"]["chips"]).urgent
    answer = {"items": {"pain": {"raw": 3}}, "chips": ["calf_pain"], "comment": None}
    assert ur.evaluate_answer(answer, PLAN).urgent
    assert not ur.evaluate_answer({"chips": ["nausea"], "comment": "ok"}, PLAN).urgent


def test_worst_picks_highest():
    assert ur.worst([ur.NONE, ur.RuleResult("attention"), ur.RuleResult("info")]).level == "attention"


# -- quality

def test_quality_assessment():
    assert quality.assess("spo2", {"value": 97}) == "good"
    assert quality.assess("spo2", {"value": 88, "signal_quality": 0.1}) == "unusable"
    assert quality.assess("spo2", {"value": 88, "signal_quality": 0.5}) == "questionable"
    assert quality.assess("hr", {"value": 400}) == "unusable"
    assert quality.assess("temp", {"value": "abc"}) == "unusable"
    assert quality.assess("hr", {"value": 70}, reported="questionable") == "questionable"


def _o(minutes_ago, q="good", v=97):
    now = datetime(2026, 10, 10, 12, 0)
    return SimpleNamespace(id=f"o{minutes_ago}", measured_at=now - timedelta(minutes=minutes_ago), quality=q,
                           value={"value": v})


def test_missing_data_is_unknown_never_normal():
    now = datetime(2026, 10, 10, 12, 0)
    assert quality.metric_status([], now)["status"] == "unknown"
    stale = quality.metric_status([_o(6 * 60)], now, stale_after_min=240)
    assert stale["status"] == "unknown" and stale["value"] is None


def test_unusable_latest_is_unreliable():
    now = datetime(2026, 10, 10, 12, 0)
    s = quality.metric_status([_o(5, "unusable", 70), _o(30)], now)
    assert s["status"] == "unreliable" and s["value"] is None and s["last_good_value"] == {"value": 97}


def test_gap_detection():
    now = datetime(2026, 10, 10, 12, 0)
    readings = [_o(m) for m in (600, 570, 540)]  # nothing in the last 9 h
    gaps = quality.find_gaps(readings, now - timedelta(hours=10), now, expected_every_min=30)
    assert gaps and gaps[-1]["hours"] == 9.0
