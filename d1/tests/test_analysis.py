from datetime import timedelta

import pytest

from surgiguard_d1.physiology import (
    ApprovedReference,
    CodeConfig,
    PhysiologyConfig,
    analyze_physiology,
)
from surgiguard_d1.physiology.trends import rolling_median, theil_sen_slope_per_hour

from .conftest import T0, make_obs

DAY = timedelta(hours=24)


def finding(run, code):
    return next(f for f in run.payload.observations if f.code == code)


def test_slope_uses_real_elapsed_time_on_irregular_samples():
    # HR rises exactly 2 beats/min per hour, sampled at uneven times.
    minutes = [0, 7, 45, 50, 180, 300]
    obs = [make_obs(i, {"hr": 70 + 2 * m / 60}, minutes=m) for i, m in enumerate(minutes)]
    run = analyze_physiology(obs, PhysiologyConfig(), T0 + timedelta(hours=6), DAY)
    f = finding(run, "hr")
    assert f.state == "summarized"
    assert f.slope.value == pytest.approx(2.0)
    assert f.slope.unit == "beats/min/h"
    assert f.span_seconds == 300 * 60


def test_slope_ignores_a_single_outlier():
    times = [T0 + timedelta(minutes=10 * i) for i in range(12)]
    values = [70.0] * 12
    values[5] = 190.0
    slope, _ = theil_sen_slope_per_hour(times, values)
    assert slope == 0.0


def test_three_different_reasons_for_no_trend_are_distinguished():
    cfg = PhysiologyConfig(codes={"spo2": CodeConfig(), "hr": CodeConfig(), "temperature": CodeConfig()})
    obs = [make_obs(i, {"hr": 70 + i}, minutes=10 * i) for i in range(5)]
    obs.append(make_obs(99, {"temperature": 36.9}, minutes=5))
    run = analyze_physiology(obs, cfg, T0 + timedelta(hours=1), DAY)
    assert finding(run, "hr").state == "summarized"
    assert finding(run, "temperature").state == "insufficient_samples"
    assert finding(run, "temperature").latest.value == 36.9  # raw data still usable
    assert finding(run, "spo2").state == "no_recent_measurement"
    assert run.payload.status == "limited"
    assert "spo2:no_recent_measurement" in run.payload.quality.reasons


def test_no_data_abstains_instead_of_reporting_normal():
    cfg = PhysiologyConfig(codes={"spo2": CodeConfig()})
    run = analyze_physiology([], cfg, T0, DAY)
    assert run.payload.status == "abstained"
    assert run.payload.quality.status == "unusable"
    assert finding(run, "spo2").median is None


def test_old_readings_outside_the_window_do_not_count_as_recent():
    obs = [make_obs(i, {"spo2": 97}, minutes=i) for i in range(5)]
    run = analyze_physiology(obs, PhysiologyConfig(), T0 + timedelta(days=3), DAY)
    assert finding(run, "spo2").state == "no_recent_measurement"


def test_stale_latest_reading_shows_as_a_trailing_gap():
    cfg = PhysiologyConfig(codes={"hr": CodeConfig(max_gap=timedelta(minutes=30))})
    obs = [make_obs(i, {"hr": 70}, minutes=10 * i) for i in range(4)]
    run = analyze_physiology(obs, cfg, T0 + timedelta(hours=5), DAY)
    f = finding(run, "hr")
    assert f.seconds_since_latest == 4.5 * 3600
    assert f.gaps[-1].end == T0 + timedelta(hours=5)
    assert f.coverage == pytest.approx(30 / (24 * 60))


def test_bp_is_two_separate_curves():
    obs = [
        make_obs(i, {"sbp": 120 + i, "dbp": 80 - i}, minutes=60 * i, method="manual")
        for i in range(4)
    ]
    run = analyze_physiology(obs, PhysiologyConfig(), T0 + timedelta(hours=4), DAY)
    assert finding(run, "sbp").slope.value == pytest.approx(1.0)
    assert finding(run, "dbp").slope.value == pytest.approx(-1.0)
    assert not any(f.code == "bp" for f in run.payload.observations)


def test_reference_comparison_only_with_an_approved_reference():
    obs = [make_obs(i, {"hr": 100 + i}, minutes=10 * i) for i in range(5)]
    without = analyze_physiology(obs, PhysiologyConfig(), T0 + timedelta(hours=1), DAY)
    assert finding(without, "hr").reference is None

    ref = ApprovedReference("ref_demo_hr", "1", lower=50, upper=90, baseline=72)
    cfg = PhysiologyConfig(codes={"hr": CodeConfig(reference=ref)}, protocol_version="protocol_demo_v1")
    r = finding(analyze_physiology(obs, cfg, T0 + timedelta(hours=1), DAY), "hr").reference
    assert (r.latest, r.window_median) == ("above", "above")
    assert r.change_from_baseline == pytest.approx(30.0)
    assert r.reference_id == "ref_demo_hr"


def test_excluded_points_are_counted_and_still_cited_as_evidence():
    obs = [make_obs(i, {"hr": 70}, minutes=10 * i) for i in range(4)]
    obs.append(make_obs(50, {"hr": 0}, minutes=45))
    run = analyze_physiology(obs, PhysiologyConfig(), T0 + timedelta(hours=1), DAY)
    f = finding(run, "hr")
    assert (f.sample_count, f.usable_count) == (5, 4)
    assert f.excluded == {"zero_value": 1}
    assert "evref_obs_050_hr" in f.evidence_ids


def test_same_inputs_give_the_same_analysis_and_replays_change_nothing():
    obs = [make_obs(i, {"spo2": 96 + i % 2, "hr": 70 + i}, minutes=10 * i) for i in range(6)]
    args = (PhysiologyConfig(), T0 + timedelta(hours=2), DAY)
    a = analyze_physiology(obs, *args)
    b = analyze_physiology(list(reversed(obs)) + obs[:3], *args)
    assert a.payload == b.payload
    assert a.input_watermark == max(o.received_at for o in obs)

    c = analyze_physiology(obs + [make_obs(77, {"hr": 71}, minutes=65)], *args)
    assert c.payload.analysis_id != a.payload.analysis_id


def test_correction_changes_the_result():
    obs = [make_obs(i, {"hr": 70}, minutes=10 * i) for i in range(4)]
    fixed = make_obs(9, {"hr": 90}, minutes=30, supersedes_id="obs_003")
    run = analyze_physiology(obs + [fixed], PhysiologyConfig(), T0 + timedelta(hours=1), DAY)
    f = finding(run, "hr")
    assert f.latest.value == 90
    assert f.sample_count == 4


def test_rolling_median_reports_how_many_samples_it_used():
    times = [T0 + timedelta(minutes=m) for m in (0, 10, 20, 200)]
    out = rolling_median(times, [70, 72, 74, 90], timedelta(minutes=30))
    assert [(m, n) for _, m, n in out] == [(70, 1), (71, 2), (72, 3), (90, 1)]
