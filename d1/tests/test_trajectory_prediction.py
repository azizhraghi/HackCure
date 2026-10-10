import json
import re
from datetime import date
from pathlib import Path

import pytest

from surgiguard_d1.trajectory_prediction import RecoveryTrajectory, deidentify, predict_normal_trajectory
from surgiguard_d1.trajectory_prediction.predict import checkpoint_days, default_llm

SAMPLE = json.loads((Path(__file__).resolve().parents[1] / "examples" / "d2_sample.json").read_text())

def checkpoint(n, pain=(3, 6), hr=(70, 92)):
    return {"day": n, "heart_rate": list(hr), "spo2": [94, 99], "systolic_bp": [110, 140],
            "diastolic_bp": [65, 88], "temperature": [36.4, 37.8], "pain": list(pain)}


def course(days):
    """The first-step answer, in the flat form the LLM returns."""
    wanted = checkpoint_days(days)
    return {
        "surgery": "Prothèse totale du genou", "summary": "Récupération progressive.",
        "full_recovery_typically_weeks": 26, "noticeable_pain_until_day": 20,
        "phases": [{"from_day": 0, "to_day": 14, "description": "phase aiguë"}],
        "lasting_symptoms": [{"symptom": "gonflement", "typically_lasts_days": 90}],
        "personal_factors": [{"factor": "64 ans", "effect": "récupération un peu plus lente"}],
        "assumptions": ["sexe non précisé"],
        "events": [{"day": 14, "description": "ablation des agrafes"},
                   {"day": 28, "description": "fin de l'interdiction de conduire"}],
        # pain falls from 5-8 on day 0 to 1-4 on the last day; heart rate from 80-104 to 60-84
        "checkpoints": [
            checkpoint(d, pain=(5 - 4 * i / (len(wanted) - 1), 8 - 4 * i / (len(wanted) - 1)),
                       hr=(80 - 20 * d / days, 104 - 20 * d / days))
            for i, d in enumerate(wanted)],
    }


class FakeLLM:
    """Stands in for the LLM: answers each part of the plan and records what it was sent.

    `spoil` maps a call number to a function that damages that answer, to test the checks.
    """

    def __init__(self, spoil=None):
        self.calls, self.spoil = [], spoil or {}

    def __call__(self, system, request, part):
        self.calls.append((system, request, part))
        if part == "course":
            answer = course(int(re.search(r"day 0 to day (\d+)", request).group(1)))
        else:
            first, last = map(int, re.search(r"Write days (\d+) to (\d+)", request).groups())
            answer = {"days": [{"day": n, "expected_signs": ["gonflement du genou"],
                                "patient_message": f"Jour {n}: c'est normal."}
                               for n in range(first, last + 1)]}
        damage = self.spoil.get(len(self.calls))
        return damage(answer) if damage else json.dumps(answer)


@pytest.fixture
def llm():
    return FakeLLM()


def predict(document, llm, tmp_path, days=24):
    return predict_normal_trajectory(document, days=days, llm=("fake-model", llm), cache_dir=tmp_path)


def test_identity_is_removed_and_every_medical_fact_is_passed_through():
    sent = deidentify(SAMPLE)
    text = json.dumps(sent, ensure_ascii=False)
    for secret in ("MILLER", "Sarah", "Ruiz", "1961", "04/06/2025", "confidence"):
        assert secret not in text
    assert sent["age"] == 64
    assert sent["surgery_type"] == "Prothèse Totale du Genou Droite"
    assert [m["dci"] for m in sent["medications"]] == ["paracétamol", "célécoxib", "énoxaparine sodique"]
    assert sent["medications"][2]["dosage_raw"] == "4000 UI / 0.4 mL"
    assert sent["physical_restrictions"] and sent["followup_appointments"] and sent["known_allergies"]
    assert sent["general_instructions"].startswith("Ne pas prendre")


def test_plan_is_estimated_once_and_split_into_days(llm, tmp_path):
    t = predict(SAMPLE, llm, tmp_path)
    assert [d.day for d in t.days] == list(range(25))
    assert t.day(13).patient_message == "Jour 13: c'est normal."
    assert t.typical_course.lasting_symptoms[0].typically_lasts_days == 90
    assert t.personal_factors[0].factor == "64 ans"
    assert [c.day for c in t.checkpoints] == [0, 1, 3, 7, 14, 21, 24]
    assert (t.generated_by, t.language, t.prompt_version) == ("fake-model", "French", "recovery-v10")


def test_days_between_checkpoints_are_filled_in_by_our_code(llm, tmp_path):
    t = predict(SAMPLE, llm, tmp_path)
    # exactly the checkpoint on a checkpoint day
    assert (t.day(0).heart_rate.low, t.day(0).heart_rate.high) == (80, 104)
    assert (t.day(24).heart_rate.low, t.day(24).heart_rate.high) == (60, 84)
    # halfway between day 7 and day 14, heart rate is halfway too
    mid = (t.day(7).heart_rate.low + t.day(14).heart_rate.low) / 2
    assert abs(t.day(10).heart_rate.low - mid) <= 1.5
    # smooth: no jumps from one day to the next, and pain only eases
    for a, b in zip(t.days, t.days[1:]):
        assert abs(a.heart_rate.low - b.heart_rate.low) <= 2
        assert b.pain.high <= a.pain.high
    assert all(d.pain.high - d.pain.low >= 1.5 for d in t.days)


def test_checkpoints_are_dense_early_and_always_end_on_the_last_day():
    assert checkpoint_days(42) == [0, 1, 3, 7, 14, 21, 28, 42]
    assert checkpoint_days(90) == [0, 1, 3, 7, 14, 21, 28, 42, 56, 70, 84, 90]
    assert checkpoint_days(5) == [0, 1, 3, 5]


def test_foundations_come_first_and_every_block_of_text_is_written_against_them(llm, tmp_path):
    predict(SAMPLE, llm, tmp_path)
    assert [part for _, _, part in llm.calls] == ["course", "days", "days"]
    assert "Checkpoint days: 0, 1, 3, 7, 14, 21, 24." in llm.calls[0][1]
    for _, request, _ in llm.calls:
        assert "MILLER" not in request and "Sarah" not in request and "Ruiz" not in request
        assert '"age": 64' in request and "célécoxib" in request
    for _, request, _ in llm.calls[1:]:
        assert "Foundations:" in request and "gonflement" in request and "64 ans" in request
        assert "Ranges and facts for each day:" in request
    assert "Write days 0 to 13" in llm.calls[1][1] and "day 13: heart rate" in llm.calls[1][1]
    assert "Previous day's message" not in llm.calls[1][1]
    assert "Write days 14 to 24" in llm.calls[2][1]
    assert "Previous day's message: Jour 13" in llm.calls[2][1]


def test_same_patient_gets_the_saved_plan_without_asking_again(llm, tmp_path):
    first = predict(SAMPLE, llm, tmp_path)
    again = predict(SAMPLE, llm, tmp_path)
    assert again == first and len(llm.calls) == 3

    changed = json.loads(json.dumps(SAMPLE))
    changed["extraction"]["medications"].pop()
    predict(changed, llm, tmp_path)
    assert len(llm.calls) == 6  # a different dossier is a new plan


def spoiled(change):
    def damage(answer):
        change(answer)
        return json.dumps(answer)
    return damage


def too_narrow(a):
    a["checkpoints"][2]["systolic_bp"] = [108, 113]


def nearly_painless(a):
    a["checkpoints"][4]["pain"] = [0, 0.5]


def painless_too_early(a):  # wide enough to be a range, but contradicts the stated course
    a["checkpoints"][4]["pain"] = [0, 2]


def impossible(a):
    a["checkpoints"][1]["spo2"] = [96, 104]


def upside_down(a):
    a["checkpoints"][0]["pain"] = [6, 2]


def not_a_pair(a):
    a["checkpoints"][0]["heart_rate"] = [70]


def checkpoint_missing(a):
    del a["checkpoints"][3]


@pytest.mark.parametrize("change, message", [
    (impossible, "physically plausible"), (upside_down, "upside down"),
    (checkpoint_missing, "checkpoints must be exactly days"),
    (not_a_pair, "heart_rate must be a .low, high. pair"),
])
def test_unusable_numbers_are_rejected_and_nothing_is_saved(change, message, tmp_path):
    always_bad = FakeLLM(spoil={1: spoiled(change), 2: spoiled(change)})
    with pytest.raises(ValueError, match=message):
        predict(SAMPLE, always_bad, tmp_path)
    assert len(always_bad.calls) == 2  # asked, then one retry
    assert list(tmp_path.iterdir()) == []


def test_too_narrow_ranges_are_widened_by_our_code_and_the_change_is_recorded(tmp_path):
    def narrow(a):
        a["checkpoints"][2]["systolic_bp"] = [108, 113]   # day 3
        a["checkpoints"][0]["spo2"] = [99, 100]           # day 0, against the upper limit
    llm = FakeLLM(spoil={1: spoiled(narrow)})
    t = predict(SAMPLE, llm, tmp_path)
    assert (t.checkpoints[2].systolic_bp.low, t.checkpoints[2].systolic_bp.high) == (100.5, 120.5)
    assert (t.checkpoints[0].spo2.low, t.checkpoints[0].spo2.high) == (97, 100)
    assert "day 3: systolic_bp range 108-113 widened to 100.5-120.5" in t.adjustments[1]
    assert len(llm.calls) == 3  # no retry was needed


def test_pain_cannot_be_near_zero_before_the_day_the_model_itself_gave(tmp_path):
    t = predict(SAMPLE, FakeLLM(spoil={1: spoiled(painless_too_early)}), tmp_path)
    day14 = t.checkpoints[4]
    assert (day14.day, day14.pain.low, day14.pain.high) == (14, 0, 3)
    assert "day 14: top of pain range raised from 2 to 3" in t.adjustments[0]
    assert predict(SAMPLE, FakeLLM(), tmp_path / "clean").adjustments == []


def text_day_missing(a):
    del a["days"][3]


def empty_message(a):
    a["days"][0]["patient_message"] = " "


@pytest.mark.parametrize("change, message", [
    (text_day_missing, "expected days 0 to 13"), (empty_message, "cannot be empty")])
def test_bad_text_is_rejected_and_nothing_is_saved(change, message, tmp_path):
    always_bad = FakeLLM(spoil={2: spoiled(change), 3: spoiled(change)})
    with pytest.raises(ValueError, match=message):
        predict(SAMPLE, always_bad, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_a_rejected_answer_gets_one_retry_that_says_what_was_wrong(tmp_path):
    llm = FakeLLM(spoil={1: spoiled(impossible)})
    t = predict(SAMPLE, llm, tmp_path)
    assert len(t.days) == 25 and len(llm.calls) == 4
    retry = llm.calls[1][1]
    assert "rejected by an automatic check" in retry
    assert "day 1: spo2 96-104 is outside what is physically plausible" in retry


def test_text_that_is_not_json_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        predict(SAMPLE, FakeLLM(spoil={1: lambda _: "Sorry, no JSON", 2: lambda _: "Still none"}), tmp_path)


def test_each_day_shows_that_days_part_of_the_plan(llm, tmp_path):
    plan = predict(SAMPLE, llm, tmp_path, days=3)
    surgery = date(2026, 10, 7)
    assert plan.today(surgery, date(2026, 10, 7)).day == 0
    assert plan.today(surgery, date(2026, 10, 9)).patient_message == "Jour 2: c'est normal."
    assert plan.today(surgery, date(2026, 10, 6)) is None  # before surgery
    assert plan.today(surgery, date(2026, 10, 20)) is None  # plan is over


def test_plan_round_trips_as_json(llm, tmp_path):
    t = predict(SAMPLE, llm, tmp_path, days=3)
    assert RecoveryTrajectory.model_validate_json(t.model_dump_json()) == t


def test_without_any_key_the_error_says_what_to_set(monkeypatch, tmp_path):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        predict_normal_trajectory(SAMPLE, days=3, cache_dir=tmp_path)


def test_groq_is_used_when_its_key_is_set(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test")
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    assert default_llm()[0] == "groq/openai/gpt-oss-120b"
    monkeypatch.setenv("GROQ_MODEL", "another-model")
    assert default_llm()[0] == "groq/another-model"


def test_each_day_is_told_what_is_still_expected_and_which_medication_has_ended(llm, tmp_path):
    predict(SAMPLE, llm, tmp_path, days=30)
    lines = {int(m.group(1)): m.group(0) for _, request, part in llm.calls if part == "days"
             for m in re.finditer(r"^day (\d+): .*$", request, re.M)}
    assert "still expected: gonflement (usually until about day 90)" in lines[30]
    assert "paracétamol (course ends day 14)" in lines[13]
    assert "medication finished: none" in lines[13]
    assert "paracétamol (ended day 14)" in lines[14]
    assert "medication running: none" in lines[14]


def test_day_facts_drop_a_symptom_once_its_usual_duration_has_passed():
    from surgiguard_d1.trajectory_prediction.predict import day_facts
    from surgiguard_d1.trajectory_prediction.schema import TypicalCourse

    c = TypicalCourse(
        full_recovery_typically_weeks=26, noticeable_pain_until_day=20, phases=[],
        lasting_symptoms=[{"symptom": "fatigue", "typically_lasts_days": 10},
                          {"symptom": "raideur", "typically_lasts_days": 90}])
    patient = {"medications": [{"dci": "bisoprolol", "duration_days": None}]}
    assert day_facts(5, c, patient).startswith("still expected: fatigue (usually until about day 10); raideur")
    assert day_facts(10, c, patient).startswith("still expected: raideur (usually until about day 90) |")
    assert "medication running: bisoprolol |" in day_facts(40, c, patient)


def test_an_object_wrapped_in_a_one_item_list_is_unwrapped_and_other_junk_is_not():
    from surgiguard_d1.trajectory_prediction.predict import _unwrap

    assert json.loads(_unwrap('[{"surgery": "x"}]')) == {"surgery": "x"}
    assert _unwrap('[{"a": 1}, "personal_factors", ":"]') is None
    assert _unwrap('[{"a": 1') is None and _unwrap(None) is None and _unwrap('{"a": 1}') is None


def test_a_range_exactly_at_the_minimum_spread_is_accepted(llm, tmp_path):
    def exact(a):
        a["checkpoints"][0]["temperature"] = [36.2, 36.8]
    t = predict(SAMPLE, FakeLLM(spoil={1: spoiled(exact)}), tmp_path, days=3)
    assert t.checkpoints[0].temperature.low == 36.2


def test_appointments_are_placed_by_our_code_so_the_text_cannot_miscount(llm, tmp_path):
    t = predict(SAMPLE, llm, tmp_path, days=30)
    assert [(e.day, e.description) for e in t.events] == [
        (14, "ablation des agrafes"), (28, "fin de l'interdiction de conduire")]
    lines = {int(m.group(1)): m.group(0) for _, request, part in llm.calls if part == "days"
             for m in re.finditer(r"^day (\d+): .*$", request, re.M)}
    assert "today: ablation des agrafes" in lines[14]
    assert "coming up: ablation des agrafes in 1 day |" not in lines[13]
    assert lines[13].endswith("coming up: ablation des agrafes in 1 day")
    assert lines[11].endswith("coming up: ablation des agrafes in 3 days")
    assert lines[10].endswith("coming up: nothing in the next 3 days")
    assert "today: nothing scheduled" in lines[15]
    assert "today: fin de l'interdiction de conduire" in lines[28]


def test_home_screen_shows_what_is_normal_to_feel_today(llm, tmp_path):
    plan = predict(SAMPLE, llm, tmp_path, days=30)
    surgery = date(2026, 10, 7)
    assert plan.home_screen(surgery, date(2026, 10, 9)) == {
        "day": 2, "surgery": "Prothèse totale du genou", "message": "Jour 2: c'est normal.",
        "normal_today": ["gonflement du genou"],
        "normal_pain": {"low": 4.0, "high": 7.0, "scale": "0-10"}, "today": []}
    assert plan.home_screen(surgery, date(2026, 10, 21))["today"] == ["ablation des agrafes"]
    assert plan.home_screen(surgery, date(2026, 10, 6)) is None
    assert plan.home_screen(surgery, date(2026, 12, 25)) is None
