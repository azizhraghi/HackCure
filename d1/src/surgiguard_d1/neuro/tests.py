"""The six guided tests for signs of neurological distress.

Each takes a recording and returns measurements, a left/right comparison and
plain observations. They look for the signs a clinician checks first: an arm
that drifts, a face that moves unevenly, a hand that is slower or clumsier,
eyes that do not move together.

The cut-offs in `Limits` decide when a difference is worth a clinician's
look. They are engineering defaults chosen to be visible on synthetic
examples; they have not been validated on patients and must be set with the
clinical team before real use.
"""

import math
from dataclasses import dataclass
from statistics import median

from ..physiology.models import Quality
from .frames import FINGERTIPS, MIDDLE_KNUCKLE, WRIST, Frame, Recording
from .results import Measurement, MotorResult

VERSION = "neuro-tests-0.1.0"


@dataclass(frozen=True)
class Limits:
    min_usable_fraction: float = 0.6  # share of frames where the needed points were seen
    min_seconds: float = 3.0
    # arm hold, in shoulder-widths
    arm_drift_difference: float = 0.25
    arm_not_raised: float = -0.6
    # face, as a share of the stronger side
    face_asymmetry: float = 0.35
    face_minimum_movement: float = 0.15
    eye_closure_difference: float = 0.3
    # finger to nose
    touch_near: float = 0.45  # fingertip-to-nose distance, in shoulder-widths
    touch_far: float = 0.9
    touch_distance_difference: float = 0.2
    rhythm_irregular: float = 0.4  # spread of the time between touches, relative to its average
    speed_ratio: float = 1.5  # one side this many times slower than the other
    # hand open and close
    amplitude_ratio: float = 1.5
    # gaze
    eyes_apart: float = 0.25
    gaze_range_ratio: float = 2.5
    head_tilt_degrees: float = 15.0
    head_turn_degrees: float = 25.0


def _percentile(values: list[float], p: float) -> float:
    s = sorted(values)
    k = (len(s) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def _m(code, value, unit, side=None) -> Measurement:
    return Measurement(code=code, value=None if value is None else round(value, 3), unit=unit, side=side)


def _result(rec: Recording, used: int, limits: Limits, measurements, observations, review,
            extra_limits=(), force_limited=False, needs="the body") -> MotorResult:
    total = len(rec.frames)
    reasons, limitations = [], list(extra_limits)
    fraction = used / total if total else 0.0
    if any(f.people > 1 for f in rec.frames):
        reasons.append("more_than_one_person")
        limitations.append("More than one person was in view; the wrong person may have been measured.")
    if not measurements or fraction < limits.min_usable_fraction or rec.seconds < limits.min_seconds:
        why = ("too_short" if rec.seconds < limits.min_seconds else "not_enough_usable_frames")
        return MotorResult(
            test=rec.test, version=VERSION, status="not_interpretable", measurements=[],
            observations=[], review_suggested=False,
            quality=Quality(status="unusable", reasons=[why, *reasons], usable_for=[]),
            limitations=[f"Recording could not be interpreted: {needs} could be seen in only "
                         f"{fraction:.0%} of its {rec.seconds:.1f} seconds. This says nothing "
                         "about the patient's condition.", *limitations])
    limited = force_limited or bool(reasons)
    return MotorResult(
        test=rec.test, version=VERSION, status="limited" if limited else "complete",
        measurements=measurements, observations=observations, review_suggested=review,
        quality=Quality(status="limited" if limited else "usable", reasons=reasons,
                        usable_for=["clinician_review"]),
        limitations=["Describes what the camera saw; it is not a diagnosis.", *limitations])


def _seen(frame: Frame, *names: str) -> bool:
    return frame.pose is not None and all(
        n in frame.pose and frame.pose[n][2] >= 0.5 for n in names)


def _shoulder_width(frame: Frame) -> float | None:
    w = abs(frame.pose["left_shoulder"][0] - frame.pose["right_shoulder"][0])
    return w if w >= 0.05 else None  # too small: too far away or turned sideways


def _dist(a, b) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _cycles(times: list[float], values: list[float], low: float, high: float):
    """Times at which the signal comes down to `low` after having been above `high`."""
    events, armed, best = [], True, None
    for t, v in zip(times, values):
        if armed and v <= low:
            armed, best = False, (t, v)
        elif not armed:
            if v < best[1]:
                best = (t, v)
            if v >= high:
                events.append(best)
                armed, best = True, None
    if best is not None:
        events.append(best)
    return events


def _spread(xs: list[float]) -> float | None:
    """Standard deviation relative to the mean (0 = perfectly regular)."""
    if len(xs) < 2:
        return None
    mean = sum(xs) / len(xs)
    return math.sqrt(sum((x - mean) ** 2 for x in xs) / len(xs)) / mean if mean else None


# ------------------------------------------------------------------ 1. arm hold


def arm_hold(rec: Recording, limits: Limits = Limits()) -> MotorResult:
    """Both arms held straight out in front for about ten seconds.

    Looks for an arm that sinks during the hold, or does not come up at all.
    Height is how far the wrist is above (+) or below (-) the shoulder, in
    shoulder-widths, so it does not depend on distance from the camera.
    """
    heights = {"left": [], "right": []}
    for f in rec.frames:
        if _seen(f, "left_shoulder", "right_shoulder", "left_wrist", "right_wrist") and (
                w := _shoulder_width(f)):
            for side in heights:
                heights[side].append((f.pose[f"{side}_shoulder"][1] - f.pose[f"{side}_wrist"][1]) / w)
    n = len(heights["left"])
    if n < 5:
        return _result(rec, n, limits, [], [], False, needs="both shoulders and wrists")

    k = max(3, n // 10)  # the first and last tenth of the hold
    start = {s: median(h[:k]) for s, h in heights.items()}
    end = {s: median(h[-k:]) for s, h in heights.items()}
    drift = {s: start[s] - end[s] for s in heights}
    difference = abs(drift["left"] - drift["right"])
    down = [s for s in heights if start[s] < limits.arm_not_raised]

    measurements = [
        *(_m("start_height", start[s], "shoulder-widths", s) for s in heights),
        *(_m("end_height", end[s], "shoulder-widths", s) for s in heights),
        *(_m("drift", drift[s], "shoulder-widths", s) for s in heights),
        _m("drift_difference", difference, "shoulder-widths"),
    ]
    if len(down) == 2:
        return _result(rec, n, limits, measurements,
                       ["Neither arm was raised to shoulder level, so there was no hold to measure."],
                       False, ["The test was not performed as instructed."], force_limited=True)
    observations = [
        f"The {s} arm sank by {drift[s]:.2f} shoulder-widths during the hold." if drift[s] >= 0.1
        else f"The {s} arm stayed level." for s in heights if s not in down]
    observations += [f"The {s} arm was not raised to shoulder level while the other was." for s in down]
    if difference >= limits.arm_drift_difference and not down:
        lower = max(drift, key=drift.get)
        observations.append(f"The {lower} arm drifted down more than the other.")
    return _result(rec, n, limits, measurements, observations,
                   review=bool(down) or difference >= limits.arm_drift_difference,
                   needs="both shoulders and wrists")


# ------------------------------------------------------- 2 and 5. face symmetry


def _face_pair(rec: Recording, left: str, right: str):
    """Rise of a left/right pair of expression scores from the resting face to the peak."""
    frames = [f.face for f in rec.frames if f.face and left in f.face and right in f.face]
    if len(frames) < 5:
        return len(frames), None
    k = max(1, len(frames) // 7)
    rise = {}
    for side, key in (("left", left), ("right", right)):
        values = [f[key] for f in frames]
        rise[side] = max(0.0, _percentile(values, 0.9) - median(values[:k]))
    return len(frames), rise


def _asymmetry(rise: dict[str, float]) -> float:
    top = max(rise.values())
    return abs(rise["left"] - rise["right"]) / top if top else 0.0


def smile(rec: Recording, limits: Limits = Limits()) -> MotorResult:
    """A neutral face, then a wide smile. Looks for one side of the mouth lifting less."""
    n, rise = _face_pair(rec, "mouthSmileLeft", "mouthSmileRight")
    if rise is None:
        return _result(rec, n, limits, [], [], False, needs="the face")
    asym = _asymmetry(rise)
    measurements = [*(_m("smile_lift", rise[s], "0-1", s) for s in rise), _m("smile_asymmetry", asym, "0-1")]
    if max(rise.values()) < limits.face_minimum_movement:
        return _result(rec, n, limits, measurements, ["No clear smile was seen on either side."], False,
                       ["Without a smile, the two sides cannot be compared."], force_limited=True,
                       needs="the face")
    weaker = min(rise, key=rise.get)
    uneven = asym >= limits.face_asymmetry
    return _result(rec, n, limits, measurements,
                   [f"The {weaker} side of the mouth lifted less than the other." if uneven
                    else "Both sides of the mouth lifted about equally."], uneven, needs="the face")


def eyebrows_and_eyes(rec: Recording, limits: Limits = Limits()) -> MotorResult:
    """Eyebrows raised, then eyes squeezed shut. Looks for an uneven forehead or an eye that
    does not close, which a smile alone can miss."""
    n, brow = _face_pair(rec, "browOuterUpLeft", "browOuterUpRight")
    _, closure = _face_pair(rec, "eyeBlinkLeft", "eyeBlinkRight")
    if brow is None or closure is None:
        return _result(rec, n, limits, [], [], False, needs="the face")
    brow_asym = _asymmetry(brow)
    closure_gap = abs(closure["left"] - closure["right"])
    measurements = [
        *(_m("eyebrow_lift", brow[s], "0-1", s) for s in brow), _m("eyebrow_asymmetry", brow_asym, "0-1"),
        *(_m("eye_closure", closure[s], "0-1", s) for s in closure),
        _m("eye_closure_difference", closure_gap, "0-1")]
    observations, review, notes = [], False, []
    if max(brow.values()) < limits.face_minimum_movement:
        notes.append("The eyebrows were not clearly raised, so they cannot be compared.")
    elif brow_asym >= limits.face_asymmetry:
        observations.append(f"The {min(brow, key=brow.get)} eyebrow lifted less than the other.")
        review = True
    else:
        observations.append("Both eyebrows lifted about equally.")
    if max(closure.values()) < limits.face_minimum_movement:
        notes.append("The eyes were not clearly closed, so they cannot be compared.")
    elif closure_gap >= limits.eye_closure_difference:
        observations.append(f"The {min(closure, key=closure.get)} eye closed less than the other.")
        review = True
    else:
        observations.append("Both eyes closed about equally.")
    return _result(rec, n, limits, measurements, observations, review, notes,
                   force_limited=bool(notes), needs="the face")


# -------------------------------------------------------------- 3. finger to nose


def finger_to_nose(rec: Recording, limits: Limits = Limits()) -> MotorResult:
    """Each index finger in turn touches the nose several times.

    Looks for a hand that misses, is slower, or moves in an irregular rhythm.
    Distances are from fingertip to nose, in shoulder-widths.
    """
    track = {"left": ([], []), "right": ([], [])}
    used = 0
    for f in rec.frames:
        if not _seen(f, "nose", "left_shoulder", "right_shoulder") or not (w := _shoulder_width(f)):
            continue
        used += 1
        for side, (ts, ds) in track.items():
            if _seen(f, f"{side}_index"):
                ts.append(f.t)
                ds.append(_dist(f.pose[f"{side}_index"], f.pose["nose"]) / w)
    measurements, stats = [], {}
    for side, (ts, ds) in track.items():
        touches = _cycles(ts, ds, limits.touch_near, limits.touch_far)
        gaps = [b[0] - a[0] for a, b in zip(touches, touches[1:])]
        stats[side] = {
            "touches": len(touches),
            "closest": sum(v for _, v in touches) / len(touches) if touches else None,
            "cycle": sum(gaps) / len(gaps) if gaps else None,
            "irregular": _spread(gaps),
        }
        s = stats[side]
        measurements += [_m("touches", s["touches"], "count", side),
                         _m("closest_distance", s["closest"], "shoulder-widths", side),
                         _m("time_between_touches", s["cycle"], "s", side),
                         _m("rhythm_irregularity", s["irregular"], "0-1", side)]
    if used < 5:
        return _result(rec, used, limits, [], [], False, needs="the face and shoulders")

    observations, review, notes = [], False, []
    for side, s in stats.items():
        if s["touches"] == 0:
            observations.append(f"The {side} index finger was not seen reaching the nose.")
        else:
            observations.append(f"The {side} index finger reached the nose {s['touches']} times.")
        if s["irregular"] is not None and s["irregular"] >= limits.rhythm_irregular:
            observations.append(f"The {side} hand moved in an irregular rhythm.")
            review = True
    L, R = stats["left"], stats["right"]
    if (L["touches"] == 0) != (R["touches"] == 0):
        review = True
    if L["closest"] is not None and R["closest"] is not None and abs(
            L["closest"] - R["closest"]) >= limits.touch_distance_difference:
        far = "left" if L["closest"] > R["closest"] else "right"
        observations.append(f"The {far} index finger stopped further from the nose than the other.")
        review = True
    if L["cycle"] and R["cycle"] and max(L["cycle"], R["cycle"]) / min(
            L["cycle"], R["cycle"]) >= limits.speed_ratio:
        slow = "left" if L["cycle"] > R["cycle"] else "right"
        observations.append(f"The {slow} hand was slower than the other.")
        review = True
    if L["touches"] == 0 and R["touches"] == 0:
        notes.append("The test was not performed as instructed.")
        review = False
    return _result(rec, used, limits, measurements, observations, review, notes,
                   force_limited=bool(notes), needs="the face and shoulders")


# -------------------------------------------------------- 4. hand open and close


def _openness(hand) -> float | None:
    palm = _dist(hand[WRIST], hand[MIDDLE_KNUCKLE])
    if palm < 1e-4:
        return None
    return sum(_dist(hand[i], hand[WRIST]) for i in FINGERTIPS) / len(FINGERTIPS) / palm


def hand_open_close(rec: Recording, limits: Limits = Limits()) -> MotorResult:
    """Both hands opened wide and closed into a fist, quickly, several times.

    Looks for a hand that opens less, is slower, or tires. Openness is the
    average fingertip distance from the wrist, measured in palm lengths.
    """
    measurements, stats, used = [], {}, 0
    for side in ("left", "right"):
        ts, vs = [], []
        for f in rec.frames:
            hand = getattr(f, f"{side}_hand")
            if hand is not None and (o := _openness(hand)) is not None:
                ts.append(f.t)
                vs.append(o)
        used = max(used, len(vs))
        if len(vs) < 5:
            stats[side] = None
            continue
        lo, hi = _percentile(vs, 0.1), _percentile(vs, 0.9)
        amplitude = hi - lo
        closes = _cycles(ts, vs, lo + 0.3 * amplitude, lo + 0.7 * amplitude) if amplitude > 0.15 else []
        seconds = ts[-1] - ts[0]
        third = max(1, len(vs) // 3)
        early = _percentile(vs[:third], 0.9) - _percentile(vs[:third], 0.1)
        late = _percentile(vs[-third:], 0.9) - _percentile(vs[-third:], 0.1)
        stats[side] = {"cycles": len(closes), "amplitude": amplitude,
                       "rate": len(closes) / seconds if seconds else None,
                       "fade": late / early if early > 0.15 else None}
        s = stats[side]
        measurements += [_m("cycles", s["cycles"], "count", side),
                         _m("opening_range", s["amplitude"], "palm-lengths", side),
                         _m("cycles_per_second", s["rate"], "1/s", side),
                         _m("late_to_early_range", s["fade"], "ratio", side)]
    missing = [s for s, v in stats.items() if v is None]
    if len(missing) == 2:
        return _result(rec, 0, limits, [], [], False, needs="either hand")

    observations, review = [], False
    notes = [f"The {s} hand was not visible, so the two hands cannot be compared." for s in missing]
    for side, s in stats.items():
        if s:
            observations.append(f"The {side} hand opened and closed {s['cycles']} times.")
    L, R = stats["left"], stats["right"]
    if L and R:
        if min(L["cycles"], R["cycles"]) == 0 and max(L["cycles"], R["cycles"]) >= 2:
            observations.append(
                f"The {'left' if L['cycles'] == 0 else 'right'} hand did not open and close.")
            review = True
        elif L["rate"] and R["rate"] and max(L["rate"], R["rate"]) / min(
                L["rate"], R["rate"]) >= limits.speed_ratio:
            observations.append(
                f"The {'left' if L['rate'] < R['rate'] else 'right'} hand was slower than the other.")
            review = True
        # Only compare how far the hands open when both were actually opening and closing;
        # between two still hands the difference is just noise.
        if min(L["cycles"], R["cycles"]) >= 2 and max(L["amplitude"], R["amplitude"]) / min(
                L["amplitude"], R["amplitude"]) >= limits.amplitude_ratio:
            observations.append(
                f"The {'left' if L['amplitude'] < R['amplitude'] else 'right'} hand opened less than the other.")
            review = True
        if L["cycles"] == 0 and R["cycles"] == 0:
            notes.append("Neither hand was seen opening and closing; the test was not performed as instructed.")
    return _result(rec, used, limits, measurements, observations, review, notes,
                   force_limited=bool(notes), needs="the hands")


# --------------------------------------------------------------- 6. head and gaze


def head_and_gaze(rec: Recording, limits: Limits = Limits()) -> MotorResult:
    """Looking at the camera, then following a dot left and right with the eyes only.

    Looks for eyes that do not move together, a gaze that reaches much less far
    to one side, or a tilted head. Gaze is a 0-1 score per eye, positive towards
    the patient's own left.
    """
    left_eye, right_eye, yaw, roll = [], [], [], []
    keys = ("eyeLookOutLeft", "eyeLookInLeft", "eyeLookInRight", "eyeLookOutRight")
    for f in rec.frames:
        if f.face and all(k in f.face for k in keys):
            left_eye.append(f.face["eyeLookOutLeft"] - f.face["eyeLookInLeft"])
            right_eye.append(f.face["eyeLookInRight"] - f.face["eyeLookOutRight"])
            if f.head is not None:
                yaw.append(f.head[0])
                roll.append(f.head[2])
    n = len(left_eye)
    if n < 5:
        return _result(rec, n, limits, [], [], False, needs="the face")

    both = [(a + b) / 2 for a, b in zip(left_eye, right_eye)]
    to_left, to_right = max(0.0, _percentile(both, 0.95)), max(0.0, -_percentile(both, 0.05))
    apart = sum(abs(a - b) for a, b in zip(left_eye, right_eye)) / n
    measurements = [_m("gaze_reach", to_left, "0-1", "left"), _m("gaze_reach", to_right, "0-1", "right"),
                    _m("eyes_apart", apart, "0-1")]
    observations, review, notes = [], False, []
    if max(to_left, to_right) < limits.face_minimum_movement:
        notes.append("The eyes were not seen following the dot; the test was not performed as instructed.")
    else:
        if apart >= limits.eyes_apart:
            observations.append("The two eyes did not move together.")
            review = True
        else:
            observations.append("The two eyes moved together.")
        small, large = sorted((to_left, to_right))
        if small == 0 or large / small >= limits.gaze_range_ratio:
            observations.append(
                f"The eyes reached much less far to the {'left' if to_left < to_right else 'right'}.")
            review = True
    if yaw:
        turn = _percentile(yaw, 0.95) - _percentile(yaw, 0.05)
        tilt = median(roll)
        measurements += [_m("head_turn_range", turn, "degrees"), _m("head_tilt", tilt, "degrees")]
        if turn >= limits.head_turn_degrees:
            notes.append("The head turned to follow the dot, so how far the eyes moved is less reliable.")
        if abs(tilt) >= limits.head_tilt_degrees:
            observations.append(f"The head was tilted by about {abs(tilt):.0f} degrees.")
            review = True
    else:
        notes.append("Head position was not available.")
    return _result(rec, n, limits, measurements, observations, review, notes,
                   force_limited=bool(notes), needs="the face")


TESTS = {
    "arm_hold": arm_hold,
    "smile": smile,
    "finger_to_nose": finger_to_nose,
    "hand_open_close": hand_open_close,
    "eyebrows_and_eyes": eyebrows_and_eyes,
    "head_and_gaze": head_and_gaze,
}


def analyze(rec: Recording, limits: Limits = Limits()) -> MotorResult:
    if rec.test not in TESTS:
        raise ValueError(f"unknown test '{rec.test}'; known tests: {', '.join(TESTS)}")
    return TESTS[rec.test](rec, limits)
