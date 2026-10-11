"""Read a test video into frames, using Google's pretrained MediaPipe models.

Three models are used as they are (nothing is trained here): one finds the
body's joints, one the hands, one the face with its expression scores. Only
the models a given test needs are run.

Left and right: the models name sides for an unmirrored image. Phone front
cameras often save a mirrored video; pass `mirrored=True` for those so that
"left" still means the patient's own left.
"""

import math
from pathlib import Path

from .frames import Frame, Recording

MODEL_DIR = Path(__file__).resolve().parents[3] / "models" / "mediapipe"
MODEL_FILES = {"pose": "pose_landmarker_lite.task", "hands": "hand_landmarker.task",
               "face": "face_landmarker.task"}
NEEDS = {
    "arm_hold": {"pose"},
    "finger_to_nose": {"pose"},
    "hand_open_close": {"pose", "hands"},
    "smile": {"face"},
    "eyebrows_and_eyes": {"face"},
    "head_and_gaze": {"face"},
}
_POSE_INDEX = {"nose": 0, "left_shoulder": 11, "right_shoulder": 12, "left_elbow": 13,
               "right_elbow": 14, "left_wrist": 15, "right_wrist": 16, "left_index": 19,
               "right_index": 20}
TARGET_FPS = 15


def _swap(name: str) -> str:
    for a, b in (("left", "right"), ("Left", "Right")):
        if a in name:
            return name.replace(a, b)
        if b in name:
            return name.replace(b, a)
    return name


def read_video(path: str | Path, test: str, mirrored: bool = False,
               model_dir: str | Path = MODEL_DIR) -> Recording:
    """Run the models over the video and return what they saw, frame by frame."""
    import cv2
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision

    if test not in NEEDS:
        raise ValueError(f"unknown test '{test}'; known tests: {', '.join(NEEDS)}")
    model_dir = Path(model_dir)

    def options(kind):
        file = model_dir / MODEL_FILES[kind]
        if not file.exists():
            raise FileNotFoundError(f"{file} is missing; run scripts/fetch_neuro_models.sh")
        return mp_python.BaseOptions(model_asset_path=str(file))

    video = vision.RunningMode.VIDEO
    needs = NEEDS[test]
    pose = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
        base_options=options("pose"), running_mode=video, num_poses=2)) if "pose" in needs else None
    hands = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
        base_options=options("hands"), running_mode=video, num_hands=2)) if "hands" in needs else None
    face = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=options("face"), running_mode=video, num_faces=2,
        output_face_blendshapes=True, output_facial_transformation_matrixes=True,
    )) if "face" in needs else None

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError(f"could not open video {path}")
    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    every = max(1, round(fps / TARGET_FPS))

    frames, index = [], -1
    try:
        while True:
            ok, bgr = capture.read()
            if not ok:
                break
            index += 1
            if index % every:
                continue
            t = index / fps
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
            ms = int(t * 1000)
            people, body, left_hand, right_hand, expressions, head = 0, None, None, None, None, None

            if pose:
                found = pose.detect_for_video(image, ms).pose_landmarks
                people = max(people, len(found))
                if found:
                    body = {}
                    for name, i in _POSE_INDEX.items():
                        p = found[0][i]
                        body[_swap(name) if mirrored else name] = (p.x, p.y, p.visibility or 0.0)
            if hands:
                result = hands.detect_for_video(image, ms)
                for points, handedness in zip(result.hand_landmarks, result.handedness):
                    xy = tuple((p.x, p.y) for p in points)
                    side = _hand_side(xy[0], body, handedness[0].category_name, mirrored)
                    if side == "left":
                        left_hand = xy
                    else:
                        right_hand = xy
            if face:
                result = face.detect_for_video(image, ms)
                people = max(people, len(result.face_landmarks))
                if result.face_blendshapes:
                    expressions = {(_swap(c.category_name) if mirrored else c.category_name): c.score
                                   for c in result.face_blendshapes[0]}
                if result.facial_transformation_matrixes:
                    head = _head_angles(result.facial_transformation_matrixes[0], mirrored)

            frames.append(Frame(t=t, pose=body, left_hand=left_hand, right_hand=right_hand,
                                face=expressions, head=head, people=people or 1))
    finally:
        capture.release()
        for model in (pose, hands, face):
            if model:
                model.close()
    return Recording(test, tuple(frames))


def _hand_side(wrist, body, label: str, mirrored: bool) -> str:
    """Which of the patient's hands this is: the one whose wrist the body model puts nearest,
    or, without a body, the hand model's own label (which assumes a mirrored image)."""
    if body and "left_wrist" in body and "right_wrist" in body:
        d = {s: math.hypot(wrist[0] - body[f"{s}_wrist"][0], wrist[1] - body[f"{s}_wrist"][1])
             for s in ("left", "right")}
        return min(d, key=d.get)
    side = label.lower()
    return side if mirrored else ("right" if side == "left" else "left")


def _head_angles(matrix, mirrored: bool) -> tuple[float, float, float]:
    """Yaw, pitch and roll in degrees from the face model's rotation matrix."""
    r = matrix
    yaw = math.degrees(math.atan2(-r[2][0], math.hypot(r[2][1], r[2][2])))
    pitch = math.degrees(math.atan2(r[2][1], r[2][2]))
    roll = math.degrees(math.atan2(r[1][0], r[0][0]))
    return (-yaw, pitch, -roll) if mirrored else (yaw, pitch, roll)
