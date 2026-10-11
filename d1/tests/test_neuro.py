import pytest

from surgiguard_d1.neuro import TESTS, Frame, Recording, analyze, compare_with_previous

from . import neuro_sim as sim


def said(result, text):
    return any(text in o for o in result.observations)


# ------------------------------------------------------------------ arm hold


def test_two_steady_arms_are_reported_as_level_and_need_no_review():
    r = analyze(sim.arm_hold())
    assert r.status == "complete" and not r.review_suggested
    assert r.value("drift", "left") == pytest.approx(0, abs=0.02)
    assert said(r, "The left arm stayed level.") and said(r, "The right arm stayed level.")


def test_one_arm_sinking_during_the_hold_is_measured_and_flagged():
    r = analyze(sim.arm_hold(drift_left=0.6))
    assert r.review_suggested
    assert r.value("drift", "left") == pytest.approx(0.6, abs=0.08)
    assert r.value("drift", "right") == pytest.approx(0, abs=0.02)
    assert said(r, "The left arm drifted down more than the other.")


def test_both_arms_tiring_equally_is_not_a_one_sided_sign():
    r = analyze(sim.arm_hold(drift_left=0.3, drift_right=0.3))
    assert not r.review_suggested and said(r, "The right arm sank by")


def test_an_arm_that_never_came_up_is_flagged_and_neither_arm_up_is_not_a_measurement():
    one = analyze(sim.arm_hold(start_right=-1.5))
    assert one.review_suggested
    assert said(one, "The right arm was not raised to shoulder level while the other was.")
    none = analyze(sim.arm_hold(start_left=-1.5, start_right=-1.5))
    assert none.status == "limited" and not none.review_suggested
    assert "not performed as instructed" in " ".join(none.limitations)


def test_distance_from_the_camera_does_not_change_the_measurement():
    near = sim.arm_hold(drift_left=0.6)
    # the same movement filmed from twice as far: everything half the size, around the image centre
    far = Recording("arm_hold", tuple(
        Frame(t=f.t, pose={k: (0.5 + (x - 0.5) / 2, 0.5 + (y - 0.5) / 2, v) for k, (x, y, v) in f.pose.items()})
        for f in near.frames))
    assert analyze(far).value("drift", "left") == pytest.approx(analyze(near).value("drift", "left"), abs=0.01)


# ---------------------------------------------------------------------- face


def test_an_even_smile_needs_no_review_and_a_one_sided_smile_does():
    even = analyze(sim.smile())
    assert even.status == "complete" and not even.review_suggested
    assert said(even, "Both sides of the mouth lifted about equally.")
    uneven = analyze(sim.smile(left=0.25, right=0.8))
    assert uneven.review_suggested and said(uneven, "The left side of the mouth lifted less")
    assert uneven.value("smile_asymmetry") > 0.6


def test_no_smile_means_nothing_to_compare_not_a_normal_result():
    r = analyze(sim.smile(left=0.05, right=0.05))
    assert r.status == "limited" and not r.review_suggested
    assert said(r, "No clear smile was seen")


def test_forehead_and_eye_closure_are_checked_separately():
    assert not analyze(sim.eyebrows_and_eyes()).review_suggested
    brow = analyze(sim.eyebrows_and_eyes(brow_right=0.1))
    assert brow.review_suggested and said(brow, "The right eyebrow lifted less")
    assert said(brow, "Both eyes closed about equally.")
    eye = analyze(sim.eyebrows_and_eyes(close_left=0.35))
    assert eye.review_suggested and said(eye, "The left eye closed less than the other.")
    assert said(eye, "Both eyebrows lifted about equally.")


# ------------------------------------------------------------- finger to nose


def test_both_fingers_reaching_the_nose_in_rhythm_needs_no_review():
    r = analyze(sim.finger_to_nose())
    assert r.status == "complete" and not r.review_suggested
    assert r.value("touches", "left") == 4 and r.value("touches", "right") == 4
    assert r.value("time_between_touches", "left") == pytest.approx(1.5, abs=0.1)
    assert r.value("closest_distance", "right") == pytest.approx(0.1, abs=0.03)


def test_a_slower_hand_a_missing_hand_and_a_shaky_rhythm_are_each_noticed():
    slow = analyze(sim.finger_to_nose(period_left=2.8))
    assert slow.review_suggested and said(slow, "The left hand was slower than the other.")
    miss = analyze(sim.finger_to_nose(miss_right=0.4))
    assert miss.review_suggested and said(miss, "The right index finger stopped further from the nose")
    shaky = analyze(sim.finger_to_nose(period_left=1.0, jitter_left=0.5))
    assert shaky.review_suggested and said(shaky, "The left hand moved in an irregular rhythm.")
    absent = analyze(sim.finger_to_nose(miss_left=1.0))
    assert absent.review_suggested and said(absent, "The left index finger was not seen reaching the nose.")


# ------------------------------------------------------------ hand open/close


def test_two_hands_opening_and_closing_alike_need_no_review():
    r = analyze(sim.hand_open_close())
    assert r.status == "complete" and not r.review_suggested
    assert r.value("cycles", "left") == r.value("cycles", "right") == 16
    assert r.value("opening_range", "left") == pytest.approx(0.75, abs=0.1)


def test_a_slower_or_weaker_hand_is_noticed():
    slow = analyze(sim.hand_open_close(rate_right=0.9))
    assert slow.review_suggested and said(slow, "The right hand was slower than the other.")
    weak = analyze(sim.hand_open_close(open_left=1.35))
    assert weak.review_suggested and said(weak, "The left hand opened less than the other.")
    still = analyze(sim.hand_open_close(open_left=1.02))
    assert still.review_suggested and said(still, "The left hand did not open and close.")


def test_two_still_hands_are_not_compared_with_each_other():
    r = analyze(sim.hand_open_close(open_left=1.012, open_right=1.006))
    assert r.status == "limited" and not r.review_suggested
    assert "Neither hand was seen opening and closing" in " ".join(r.limitations)
    assert not said(r, "opened less")


def test_one_hand_out_of_view_is_a_limit_not_a_finding():
    r = analyze(sim.hand_open_close(show_right=False))
    assert r.status == "limited" and not r.review_suggested
    assert "The right hand was not visible" in " ".join(r.limitations)


# ----------------------------------------------------------------- head, gaze


def test_eyes_moving_together_to_both_sides_need_no_review():
    r = analyze(sim.head_and_gaze())
    assert r.status == "complete" and not r.review_suggested
    assert r.value("gaze_reach", "left") == pytest.approx(0.7, abs=0.05)
    assert said(r, "The two eyes moved together.")


def test_eyes_apart_a_one_sided_gaze_and_a_tilted_head_are_each_noticed():
    apart = analyze(sim.head_and_gaze(right_eye_lag=0.9))
    assert apart.review_suggested and said(apart, "The two eyes did not move together.")
    one_way = analyze(sim.head_and_gaze(reach_right=0.15))
    assert one_way.review_suggested and said(one_way, "The eyes reached much less far to the right.")
    tilted = analyze(sim.head_and_gaze(tilt=22))
    assert tilted.review_suggested and said(tilted, "The head was tilted by about 22 degrees.")


def test_turning_the_head_instead_of_the_eyes_is_a_limit_on_the_measurement():
    r = analyze(sim.head_and_gaze(head_turn=30))
    assert r.status == "limited" and "head turned" in " ".join(r.limitations)


# ---------------------------------------------------------- quality, in common


@pytest.mark.parametrize("recording", [
    sim.arm_hold(visible=0.2),                                   # body not clearly visible
    sim.arm_hold(seconds=1.5),                                   # too short
    Recording("smile", tuple(Frame(t=t) for t in sim.times(5))),  # no face found
    Recording("hand_open_close", tuple(Frame(t=t) for t in sim.times(5))),
])
def test_a_recording_that_cannot_be_read_gives_no_numbers_and_no_reassurance(recording):
    r = analyze(recording)
    assert r.status == "not_interpretable" and r.measurements == [] and not r.review_suggested
    assert r.quality.status == "unusable"
    assert "says nothing about the patient's condition" in " ".join(r.limitations)


def test_a_second_person_in_view_limits_the_result():
    r = analyze(sim.arm_hold(drift_left=0.6, people=2))
    assert r.status == "limited" and "more_than_one_person" in r.quality.reasons
    assert r.review_suggested  # the observation is kept, with the reservation


def test_every_result_says_it_is_not_a_diagnosis_and_never_names_a_condition():
    recordings = [sim.arm_hold(drift_left=0.6), sim.smile(left=0.2), sim.finger_to_nose(period_left=2.8),
                  sim.hand_open_close(open_left=1.3), sim.eyebrows_and_eyes(close_left=0.3),
                  sim.head_and_gaze(right_eye_lag=0.9)]
    assert {r.test for r in recordings} == set(TESTS)
    for rec in recordings:
        r = analyze(rec)
        text = " ".join(r.observations).lower()
        assert "not a diagnosis" in " ".join(r.limitations)
        for word in ("stroke", "avc", "paralysis", "palsy", "weakness", "deficit"):
            assert word not in text


def test_unknown_test_name_is_refused():
    with pytest.raises(ValueError, match="unknown test"):
        analyze(Recording("jumping_jacks", ()))


# ------------------------------------------------- compared with earlier tests


def test_change_since_the_patients_earlier_session_is_reported():
    before, today = analyze(sim.arm_hold()), analyze(sim.arm_hold(drift_left=0.6))
    changes = {(c.code, c.side): c for c in compare_with_previous(today, before)}
    assert changes[("drift", "left")].change == pytest.approx(0.6, abs=0.08)
    assert changes[("drift", "right")].change == pytest.approx(0, abs=0.02)


def test_sessions_that_are_not_comparable_are_not_compared():
    arm, face = analyze(sim.arm_hold()), analyze(sim.smile())
    unreadable = analyze(sim.arm_hold(visible=0.2))
    assert compare_with_previous(arm, face) == []
    assert compare_with_previous(arm, unreadable) == []
