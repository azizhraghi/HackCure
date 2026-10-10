from datetime import timedelta

from surgiguard_d1.physiology import CodeConfig, PhysiologyConfig, build_series

from .conftest import make_obs


def flags(series, code):
    return [p.flags for p in series.by_code[code].points]


def test_replayed_event_is_counted_once():
    obs = make_obs(1, {"hr": 70})
    s = build_series([obs, obs, obs], PhysiologyConfig())
    assert len(s.by_code["hr"].points) == 1


def test_out_of_order_arrival_is_sorted_and_flagged():
    early_but_late = make_obs(1, {"hr": 70}, minutes=0, received_delay_s=3600)
    later = make_obs(2, {"hr": 74}, minutes=10)
    s = build_series([later, early_but_late], PhysiologyConfig())
    pts = s.by_code["hr"].points
    assert [p.value for p in pts] == [70, 74]
    assert "late_arrival" in pts[0].flags
    assert "late_arrival" not in pts[1].flags


def test_same_reading_under_a_new_event_id_is_a_duplicate():
    s = build_series(
        [make_obs(1, {"spo2": 96}), make_obs(2, {"spo2": 96})], PhysiologyConfig()
    )
    pts = s.by_code["spo2"].points
    assert len(pts) == 2  # still visible
    assert [p.usable for p in pts] == [True, False]


def test_correction_replaces_value_and_history_is_kept():
    wrong = make_obs(1, {"sbp": 210, "dbp": 80}, method="manual")
    fixed = make_obs(2, {"sbp": 120, "dbp": 80}, method="manual", supersedes_id="obs_001")
    s = build_series([wrong, fixed], PhysiologyConfig())
    assert [p.value for p in s.by_code["sbp"].points] == [120]
    assert "correction" in s.by_code["sbp"].points[0].flags
    assert s.corrections[0].superseded_id == "obs_001"
    assert s.corrections[0].superseding_id == "obs_002"


def test_gap_is_reported_not_filled():
    cfg = PhysiologyConfig(codes={"hr": CodeConfig(max_gap=timedelta(minutes=15))})
    obs = [make_obs(i, {"hr": 70 + i}, minutes=m) for i, m in enumerate([0, 10, 20, 200, 210])]
    series = build_series(obs, cfg).by_code["hr"]
    assert len(series.points) == 5  # no interpolated points
    assert len(series.gaps) == 1
    assert series.gaps[0].seconds == 180 * 60


def test_doubtful_values_are_flagged_but_never_removed():
    cfg = PhysiologyConfig(codes={"hr": CodeConfig(plausible_low=20, plausible_high=250)})
    obs = [
        make_obs(1, {"hr": 300}, minutes=0),
        make_obs(2, {"hr": 0}, minutes=5),
        make_obs(3, {"hr": 80}, minutes=10, quality="unusable", reasons=["detached"]),
        make_obs(4, {"hr": 80}, minutes=15, received_delay_s=-3600),
    ]
    pts = build_series(obs, cfg).by_code["hr"].points
    assert len(pts) == 4
    assert "outside_plausibility_config" in pts[0].flags and pts[0].usable
    assert "zero_value" in pts[1].flags and not pts[1].usable
    assert {"device_reported_unusable", "device_detached"} <= set(pts[2].flags)
    assert "clock_skew_future" in pts[3].flags


def test_device_change_is_visible():
    obs = [
        make_obs(1, {"temperature": 36.8}, minutes=0, device_id="thermo_a"),
        make_obs(2, {"temperature": 37.4}, minutes=60, device_id="thermo_b"),
    ]
    pts = build_series(obs, PhysiologyConfig()).by_code["temperature"].points
    assert "source_changed" in pts[1].flags
