import pytest
from pydantic import ValidationError

from surgiguard_d1.physiology import PhysiologyConfig, normalize_units, validate_physiology

from .conftest import make_obs

CFG = PhysiologyConfig()


def codes(obs, config=CFG):
    return [e.code for e in validate_physiology(obs.payload, config)]


def test_valid_readings_are_accepted():
    assert codes(make_obs(1, {"spo2": 97, "hr": 72})) == []
    assert codes(make_obs(2, {"temperature": 36.8})) == []
    assert codes(make_obs(3, {"sbp": 120, "dbp": 80}, method="manual")) == []


def test_wrong_unit_and_unknown_code_are_rejected():
    assert codes(make_obs(1, {"spo2": 97}, units={"spo2": "mmHg"})) == ["wrong_unit"]
    assert codes(make_obs(1, {"glucose": 5.0})) == ["unsupported_code"]


def test_impossible_values_are_rejected_but_unusual_ones_are_not():
    assert codes(make_obs(1, {"spo2": 104})) == ["over_100_percent"]
    assert codes(make_obs(1, {"hr": -5})) == ["negative"]
    assert codes(make_obs(1, {"hr": 210})) == []  # unusual is not invalid


def test_bp_must_be_paired_and_manual():
    assert codes(make_obs(1, {"sbp": 120}, method="manual")) == ["unpaired_bp"]
    assert codes(make_obs(1, {"sbp": 120, "dbp": 80}, method="iot")) == ["bp_not_manual"]
    assert codes(make_obs(1, {"sbp": 120, "dbp": 80}, method="smartphone_session")) == [
        "bp_not_manual"
    ]


def test_respiratory_rate_only_when_enabled():
    obs = make_obs(1, {"rr": 16})
    assert codes(obs) == ["unsupported_code"]
    assert codes(obs, PhysiologyConfig(rr_enabled=True)) == []


def test_empty_metrics_rejected():
    assert codes(make_obs(1, {})) == ["empty"]


def test_fahrenheit_is_converted_and_original_kept():
    obs = make_obs(1, {"temperature": 98.6}, units={"temperature": "[degF]"})
    payload, provenance = normalize_units(obs.payload)
    assert payload.metrics[0].unit == "Cel"
    assert payload.metrics[0].value == pytest.approx(37.0)
    assert provenance[0].original_value == 98.6
    assert provenance[0].original_unit == "[degF]"
    assert validate_physiology(payload, CFG) == []


def test_schema_rejects_extra_fields_and_naive_timestamps():
    good = make_obs(1, {"hr": 70}).model_dump()
    with pytest.raises(ValidationError):
        type(make_obs(1, {"hr": 70})).model_validate({**good, "role": "clinician"})
    with pytest.raises(ValidationError):
        type(make_obs(1, {"hr": 70})).model_validate(
            {**good, "occurred_at": "2026-10-10T08:00:00"}
        )
