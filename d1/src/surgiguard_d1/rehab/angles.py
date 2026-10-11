"""Deterministic joint angle calculations and temporal smoothing.

Implements projected 2D and 3D joint angle calculations between three anatomical
landmarks (e.g., Hip - Knee - Ankle), visibility gating, and jitter-filtering.
"""

from collections import deque
import math
from typing import Tuple

from .models import PoseLandmark


def calculate_angle_2d(
    p1: Tuple[float, float],
    vertex: Tuple[float, float],
    p3: Tuple[float, float],
) -> float:
    """Calculate the interior planar angle in degrees at vertex between p1 and p3.

    Returns an angle in degrees in the range [0.0, 180.0].
    """
    v1_x = p1[0] - vertex[0]
    v1_y = p1[1] - vertex[1]

    v2_x = p3[0] - vertex[0]
    v2_y = p3[1] - vertex[1]

    norm1 = math.hypot(v1_x, v1_y)
    norm2 = math.hypot(v2_x, v2_y)

    if norm1 < 1e-6 or norm2 < 1e-6:
        return 0.0

    dot = (v1_x * v2_x) + (v1_y * v2_y)
    cos_theta = dot / (norm1 * norm2)
    # Numerical stability clamping
    cos_theta = max(-1.0, min(1.0, cos_theta))

    angle_rad = math.acos(cos_theta)
    return math.degrees(angle_rad)


def calculate_angle_3d(
    p1: Tuple[float, float, float],
    vertex: Tuple[float, float, float],
    p3: Tuple[float, float, float],
) -> float:
    """Calculate the 3D spatial angle in degrees at vertex between p1 and p3."""
    v1_x = p1[0] - vertex[0]
    v1_y = p1[1] - vertex[1]
    v1_z = p1[2] - vertex[2]

    v2_x = p3[0] - vertex[0]
    v2_y = p3[1] - vertex[1]
    v2_z = p3[2] - vertex[2]

    norm1 = math.sqrt(v1_x**2 + v1_y**2 + v1_z**2)
    norm2 = math.sqrt(v2_x**2 + v2_y**2 + v2_z**2)

    if norm1 < 1e-6 or norm2 < 1e-6:
        return 0.0

    dot = (v1_x * v2_x) + (v1_y * v2_y) + (v1_z * v2_z)
    cos_theta = dot / (norm1 * norm2)
    cos_theta = max(-1.0, min(1.0, cos_theta))

    return math.degrees(math.acos(cos_theta))


def calculate_joint_angle_from_landmarks(
    landmarks: dict[int, PoseLandmark],
    idx1: int,
    idx_vertex: int,
    idx3: int,
    min_visibility: float = 0.65,
    use_3d: bool = False,
) -> Tuple[float | None, str]:
    """Extract coordinates for 3 landmarks and calculate joint angle with visibility gating.

    Returns:
        (angle_deg, status): status is 'ok' if computed, or an explanatory reason
        such as 'missing_landmarks' or 'low_visibility'.
    """
    if (
        idx1 not in landmarks
        or idx_vertex not in landmarks
        or idx3 not in landmarks
    ):
        return None, "missing_landmarks"

    l1 = landmarks[idx1]
    lv = landmarks[idx_vertex]
    l3 = landmarks[idx3]

    if (
        l1.visibility < min_visibility
        or lv.visibility < min_visibility
        or l3.visibility < min_visibility
    ):
        return None, "low_visibility"

    if use_3d:
        angle = calculate_angle_3d(
            (l1.x, l1.y, l1.z),
            (lv.x, lv.y, lv.z),
            (l3.x, l3.y, l3.z),
        )
    else:
        angle = calculate_angle_2d(
            (l1.x, l1.y),
            (lv.x, lv.y),
            (l3.x, l3.y),
        )

    return angle, "ok"


class AngleSmoother:
    """Sliding-window filter combining median rejection and exponential moving average.

    Eliminates camera pixel noise and landmark detection jitter while preserving
    true biomechanical peak angles.
    """

    def __init__(self, window_size: int = 5, alpha: float = 0.4):
        self.window_size = window_size
        self.alpha = alpha
        self.history: deque[float] = deque(maxlen=window_size)
        self.last_smoothed: float | None = None

    def add(self, raw_angle: float) -> float:
        """Add a raw angle sample and return the smoothed estimate."""
        self.history.append(raw_angle)

        # Median filter over recent window
        sorted_window = sorted(self.history)
        n = len(sorted_window)
        median_val = sorted_window[n // 2]

        if self.last_smoothed is None:
            self.last_smoothed = median_val
        else:
            # Exponential moving average blending towards median
            self.last_smoothed = (self.alpha * median_val) + (
                (1.0 - self.alpha) * self.last_smoothed
            )

        return self.last_smoothed

    def reset(self) -> None:
        """Reset internal filter state."""
        self.history.clear()
        self.last_smoothed = None
