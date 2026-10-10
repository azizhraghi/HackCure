import math
from datetime import timedelta
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from surgiguard_d1.patient_twin import (
    ChronosForecaster, Forecast, ForecastConfig, PersistenceForecaster, TrendForecaster,
    backtest, forecast_metric, to_hourly,
)
from surgiguard_d1.physiology import PhysiologyConfig, build_series

from .conftest import T0, make_obs

CHRONOS_DIR = Path(__file__).resolve().parents[1] / "models" / "chronos-bolt-tiny"
NOW = T0 + timedelta(hours=48)


def hr_points(hours=48, per_hour=2, value=lambda h: 70 + 0.2 * h, skip=(), device="dev_demo_001"):
    obs, n = [], 0
    for i in range(hours * per_hour):
        h = i / per_hour
        if any(a <= h < b for a, b in skip):
            continue
        n += 1
        obs.append(make_obs(n, {"hr": value(h)}, minutes=60 * h + 10, device_id=device))
    return list(build_series(obs, PhysiologyConfig()).by_code["hr"].points)


def run(points, forecaster=None, code="hr", **cfg):
    return forecast_metric(code, "beats/min", points, NOW, forecaster or PersistenceForecaster(),
                           ForecastConfig(**cfg))


def test_hourly_grid_keeps_gaps_as_missing():
    hourly = to_hourly(hr_points(skip=[(20, 26)]), NOW, 48)
    assert len(hourly) == 48
    assert np.isnan(hourly[20:26]).all() and not np.isnan(hourly[:20]).any()
    assert hourly[-1] == pytest.approx(70 + 0.2 * 47.25, abs=0.1)


def test_persistence_repeats_the_latest_value_with_a_band():
    out = run(hr_points())
    assert [f.horizon_hours for f in out] == [6, 12, 24]
    assert all(f.status == "available" and f.point == pytest.approx(79.45, abs=0.1) for f in out)
    assert out[0].interval.coverage == 0.8
    assert out[0].interval.lower <= out[0].point <= out[0].interval.upper
    assert out[0].method_version == "persistence-0.1.0"
    assert out[0].evidence_ids and out[0].forecast_id != out[1].forecast_id


def test_trend_method_continues_a_steady_rise():
    out = run(hr_points(), TrendForecaster())
    assert out[0].point == pytest.approx(79.45 + 0.2 * 6, abs=0.3)
    assert out[2].point == pytest.approx(79.45 + 0.2 * 24, abs=0.5)


@pytest.mark.parametrize("points, kwargs, expected_reason", [
    (hr_points(hours=6), {}, "hours with readings"),
    (hr_points(skip=[(30, 44)]), {}, "of the last 24 hours"),
    (hr_points(skip=[(43, 48)]), {}, "hours old"),
    (hr_points(), {"code": "temperature"}, "not enabled"),
    ([], {}, "No usable readings"),
    (hr_points(hours=47) + hr_points(hours=1, device="other_device"), {}, "device changed"),
])
def test_it_abstains_whenever_history_cannot_support_a_forecast(points, kwargs, expected_reason):
    out = run(sorted(points, key=lambda p: p.occurred_at), **kwargs)
    assert len(out) == 3
    for f in out:
        assert f.status == "abstained" and f.point is None and f.interval is None
        assert f.method_version is None
        assert any(expected_reason in r for r in f.limitations)


def test_an_abstention_can_never_carry_numbers():
    base = run([])[0].model_dump()
    with pytest.raises(ValidationError):
        Forecast.model_validate({**base, "point": 80.0})
    with pytest.raises(ValidationError):
        Forecast.model_validate({**base, "limitations": []})


def test_forecast_is_reproducible():
    assert run(hr_points()) == run(hr_points())


def test_backtest_shows_which_method_is_better_on_a_given_signal():
    rising = np.array([70 + 0.3 * h for h in range(120)])
    rng = np.random.default_rng(0)
    flat = 75 + rng.normal(0, 2, 120)
    methods = {"persistence": PersistenceForecaster(), "trend": TrendForecaster()}
    up = backtest(methods, [rising])
    assert up["trend"][24]["mae"] < 0.1 < up["persistence"][24]["mae"]
    noisy = backtest(methods, [flat])
    assert noisy["persistence"][24]["mae"] < noisy["trend"][24]["mae"]
    assert noisy["persistence"][6]["n"] > 5


@pytest.mark.skipif(not (CHRONOS_DIR / "model.safetensors").exists(), reason="pretrained model not downloaded")
def test_pretrained_model_forecasts_a_daily_rhythm():
    daily = lambda h: 72 + 6 * math.sin(2 * math.pi * h / 24)  # noqa: E731
    points = hr_points(hours=48, value=daily)
    out = run(points, ChronosForecaster(CHRONOS_DIR))
    assert all(f.status == "available" and f.interval is not None for f in out)
    assert out[0].method_version == "chronos-bolt-tiny-zero-shot"
    for f in out:
        assert abs(f.point - daily(47.5 + f.horizon_hours)) < 5
        assert f.interval.lower <= f.point <= f.interval.upper
