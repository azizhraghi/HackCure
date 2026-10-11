"""Made-up recordings for testing the guided tests: what a pose/hand/face model
would report for a patient performing each movement, normally or not."""

import math

from surgiguard_d1.neuro import Frame, Recording

FPS = 20
SHOULDER_Y, NOSE = 0.40, (0.50, 0.25)
SHOULDER_X = {"left": 0.60, "right": 0.40}  # shoulder width 0.2


def times(seconds):
    return [i / FPS for i in range(int(seconds * FPS) + 1)]


def body(extra=None, visible=1.0):
    pose = {"nose": (*NOSE, visible)}
    for side, x in SHOULDER_X.items():
        pose[f"{side}_shoulder"] = (x, SHOULDER_Y, visible)
    pose.update(extra or {})
    return pose


def arm_hold(drift_left=0.0, drift_right=0.0, start_left=0.0, start_right=0.0, seconds=10,
             visible=1.0, people=1):
    """Heights in shoulder-widths; drift is how far the wrist sinks over the hold."""
    frames = []
    for t in times(seconds):
        wrists = {}
        for side, start, drift in (("left", start_left, drift_left), ("right", start_right, drift_right)):
            height = start - drift * t / seconds
            wrists[f"{side}_wrist"] = (SHOULDER_X[side], SHOULDER_Y - height * 0.2, visible)
        frames.append(Frame(t=t, pose=body(wrists, visible), people=people))
    return Recording("arm_hold", tuple(frames))


def _expression(t, peak, rest_seconds=1.5):
    return 0.03 if t < rest_seconds else peak


def smile(left=0.8, right=0.8, seconds=5):
    return Recording("smile", tuple(
        Frame(t=t, face={"mouthSmileLeft": _expression(t, left), "mouthSmileRight": _expression(t, right)})
        for t in times(seconds)))


def eyebrows_and_eyes(brow_left=0.7, brow_right=0.7, close_left=0.9, close_right=0.9, seconds=8):
    frames = []
    for t in times(seconds):
        raising, closing = 1.5 <= t < 4, t >= 5
        frames.append(Frame(t=t, face={
            "browOuterUpLeft": brow_left if raising else 0.03,
            "browOuterUpRight": brow_right if raising else 0.03,
            "eyeBlinkLeft": close_left if closing else 0.05,
            "eyeBlinkRight": close_right if closing else 0.05}))
    return Recording("eyebrows_and_eyes", tuple(frames))


def finger_to_nose(period_left=1.5, period_right=1.5, miss_left=0.1, miss_right=0.1,
                   jitter_left=0.0, seconds=12):
    """Left hand works in the first half, right hand in the second; the idle hand rests far away.
    `miss` is how far from the nose the fingertip stops, in shoulder-widths."""
    frames = []
    for t in times(seconds):
        points = {}
        for side, active, period, miss, jitter in (
                ("left", t < seconds / 2, period_left, miss_left, jitter_left),
                ("right", t >= seconds / 2, period_right, miss_right, 0.0)):
            if active:
                phase = t / period + jitter * math.sin(1.7 * t)
                d = miss + (1.4 - miss) * (0.5 + 0.5 * math.cos(2 * math.pi * phase))
            else:
                d = 1.6
            sign = 1 if side == "left" else -1
            points[f"{side}_index"] = (NOSE[0] + sign * d * 0.2, NOSE[1], 1.0)
        frames.append(Frame(t=t, pose=body(points)))
    return Recording("finger_to_nose", tuple(frames))


def _hand(openness):
    """21 points with the given average fingertip distance, in palm lengths (palm = 0.1)."""
    hand = [(0.0, 0.0)] * 21
    hand[9] = (0.0, -0.1)
    for i, angle in zip((4, 8, 12, 16, 20), (-0.6, -0.25, 0.0, 0.25, 0.5)):
        hand[i] = (math.sin(angle) * openness * 0.1, -math.cos(angle) * openness * 0.1)
    return tuple(hand)


def hand_open_close(rate_left=2.0, rate_right=2.0, open_left=1.9, open_right=1.9,
                    show_left=True, show_right=True, seconds=8):
    frames = []
    for t in times(seconds):
        hands = {}
        for side, rate, top, show in (("left", rate_left, open_left, show_left),
                                      ("right", rate_right, open_right, show_right)):
            if show:
                closed = 1.0
                hands[f"{side}_hand"] = _hand(closed + (top - closed) * (0.5 + 0.5 * math.cos(2 * math.pi * rate * t)))
        frames.append(Frame(t=t, **hands))
    return Recording("hand_open_close", tuple(frames))


def head_and_gaze(reach_left=0.7, reach_right=0.7, right_eye_lag=0.0, tilt=0.0, head_turn=0.0, seconds=8):
    """The dot goes to the patient's left, then right. `right_eye_lag` is the share of the
    movement the right eye fails to make."""
    frames = []
    for t in times(seconds):
        s = math.sin(2 * math.pi * t / seconds)
        target = s * (reach_left if s > 0 else reach_right)
        left_eye, right_eye = target, target * (1 - right_eye_lag)
        frames.append(Frame(t=t, head=(head_turn * s, 0.0, tilt), face={
            "eyeLookOutLeft": max(0.0, left_eye), "eyeLookInLeft": max(0.0, -left_eye),
            "eyeLookInRight": max(0.0, right_eye), "eyeLookOutRight": max(0.0, -right_eye)}))
    return Recording("head_and_gaze", tuple(frames))
