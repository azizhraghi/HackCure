"""What a guided test recording looks like once a pose/hand/face model has read it.

The measurement code works on these frames, so it does not matter whether the
positions were computed on the phone or from an uploaded video.

Sides are always the PATIENT'S OWN left and right. Whoever builds the frames
is responsible for that, including undoing a mirrored front-camera image.
"""

from dataclasses import dataclass

# Body points used, by name. Each is (x, y, visibility): x and y are fractions of the
# image width and height, y grows downward, visibility is 0-1.
POSE_POINTS = ("nose", "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
               "left_wrist", "right_wrist", "left_index", "right_index")

# Hand points follow the usual 21-point layout.
WRIST, THUMB_TIP, INDEX_TIP, MIDDLE_KNUCKLE, MIDDLE_TIP, RING_TIP, PINKY_TIP = 0, 4, 8, 9, 12, 16, 20
FINGERTIPS = (THUMB_TIP, INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP)


@dataclass(frozen=True)
class Frame:
    t: float  # seconds since the start of the recording
    pose: dict[str, tuple[float, float, float]] | None = None
    left_hand: tuple[tuple[float, float], ...] | None = None
    right_hand: tuple[tuple[float, float], ...] | None = None
    # Facial expression scores, 0-1, e.g. "mouthSmileLeft", "eyeBlinkRight", "eyeLookOutLeft".
    face: dict[str, float] | None = None
    head: tuple[float, float, float] | None = None  # yaw, pitch, roll in degrees
    people: int = 1  # how many people were seen in the frame


@dataclass(frozen=True)
class Recording:
    test: str
    frames: tuple[Frame, ...]

    @property
    def seconds(self) -> float:
        return self.frames[-1].t - self.frames[0].t if len(self.frames) > 1 else 0.0
