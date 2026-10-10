"""Wound photo measurements computed by code (no AI). Explainable, not clinically validated.

1. Quality: too dark / overexposed / blurry / no skin visible -> "retake", never a measurement.
2. Redness: pixels much redder than the patient's own surrounding skin (CIELAB a* channel,
   relative to the median skin a*), inside the central area of the frame where the wound is aimed.
3. Comparison with a reference photo: change in redness area and intensity.

Swelling, drainage and depth cannot be measured from one 2-D photo: they are reported as
"not measured" (unknown), never as "none". Different framing, distance or light changes the numbers.
"""

import io

import numpy as np
from PIL import Image, ImageOps

MAX_SIDE = 512


def _lab(rgb: np.ndarray) -> np.ndarray:
    """sRGB (0-255) -> CIELAB (D65)."""
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    xyz = c @ np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]).T
    xyz /= np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    L = 116 * f[..., 1] - 16
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], axis=-1)


def load(data: bytes) -> np.ndarray:
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    im.thumbnail((MAX_SIDE, MAX_SIDE))
    return np.asarray(im, dtype=np.float64)


def analyze(data: bytes) -> dict:
    try:
        rgb = load(data)
    except Exception as e:  # not an image / corrupt
        return {"quality": "unusable", "problems": [f"not a readable image ({type(e).__name__})"]}
    h, w, _ = rgb.shape
    lab = _lab(rgb)
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]

    problems = []
    brightness = float(L.mean())
    if brightness < 22:
        problems.append("too dark: add light")
    elif brightness > 92:
        problems.append("overexposed: move away from direct light")
    gray = rgb.mean(axis=2)
    lap = (-4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:])
    sharpness = float(lap.var())
    if sharpness < 12:
        problems.append("blurry: hold the phone still")

    # Skin: warm, not too dark/bright, reasonably saturated (works across skin tones, not perfect).
    skin = (L > 20) & (L < 95) & (a > 2) & (a < 50) & (b > 2) & (b < 50)
    # Central region where the user aims the wound (the frame corners on screen).
    yy, xx = np.mgrid[0:h, 0:w]
    centre = (np.abs(yy - h / 2) < h * 0.4) & (np.abs(xx - w / 2) < w * 0.4)
    region = skin & centre
    skin_fraction = float(region.sum() / centre.sum())
    if skin_fraction < 0.25:
        problems.append("no skin visible in the frame: centre the wound")

    out = {"quality": "good", "problems": problems, "brightness": round(brightness, 1), "sharpness": round(sharpness, 1),
           "skin_fraction": round(skin_fraction, 2), "method": "code: CIELAB redness vs. surrounding skin (not AI)",
           "not_measured": ["swelling", "drainage", "depth", "warmth"]}
    if problems:
        out["quality"] = "unusable" if skin_fraction < 0.25 or brightness < 22 else "questionable"
    if skin_fraction < 0.25:
        return out

    ref_a = float(np.median(a[region]))
    # Strongly red pixels fall outside the skin colour range, so look for them in the whole centre area,
    # otherwise the most inflamed tissue would not be counted.
    red = centre & (L > 15) & (L < 95) & (a > ref_a + 10)
    area = region | red
    out["skin_redness_ref"] = round(ref_a, 1)
    out["redness_area_pct"] = round(float(red.sum() / area.sum() * 100), 1)
    out["redness_intensity"] = round(float((a[red] - ref_a).mean()) if red.any() else 0.0, 1)
    return out


def compare(reference: dict | None, current: dict | None) -> dict:
    """Change from the reference photo to the current one. Unknown stays unknown."""
    if not reference or not current or "redness_area_pct" not in reference or "redness_area_pct" not in current:
        return {"available": False, "reason": "one of the photos could not be measured: unknown"}
    if "unusable" in (reference.get("quality"), current.get("quality")):
        return {"available": False, "reason": "photo quality too low to compare: unknown"}
    ra, ca = reference["redness_area_pct"], current["redness_area_pct"]
    rel = round((ca - ra) / ra * 100) if ra >= 0.5 else None
    points = round(ca - ra, 1)
    if points >= 3 or (rel is not None and rel >= 30):
        trend, label = "up", "more redness than the reference photo"
    elif points <= -3 or (rel is not None and rel <= -30):
        trend, label = "down", "less redness than the reference photo"
    else:
        trend, label = "stable", "no clear change in redness"
    return {"available": True, "redness_area_ref_pct": ra, "redness_area_now_pct": ca, "redness_area_change_points": points,
            "redness_area_change_pct": rel, "redness_intensity_change": round(current["redness_intensity"] - reference["redness_intensity"], 1),
            "trend": trend, "summary": label,
            "not_measured": ["swelling", "drainage", "depth", "warmth"],
            "caution": "Measured by code from two photos; framing, distance and light change the numbers. Not a diagnosis.",
            "quality": "questionable" if "questionable" in (reference.get("quality"), current.get("quality")) else "good"}
