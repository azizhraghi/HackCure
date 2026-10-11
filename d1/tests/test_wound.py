"""D1-F wound-photo pipeline, checked against synthetic photos whose ground truth we drew ourselves,
and on the three real (openly licensed) photos shipped in backend/seed/photos."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from surgiguard_d1.wound import analyze, overlay, strip_private
from surgiguard_d1.wound.pipeline import load

PHOTOS = Path(__file__).resolve().parents[2] / "backend" / "seed" / "photos"
SKIN = (150, 170, 215)  # BGR, a light skin tone


def skin_image(seed=0, h=480, w=640, tone=SKIN):
    rng = np.random.default_rng(seed)
    img = np.empty((h, w, 3), np.float32)
    img[:] = tone
    img += rng.normal(0, 6, (h, w, 1))                                   # skin texture
    img *= np.linspace(0.85, 1.1, w)[None, :, None]                    # uneven light
    return img


def incision(img, redness=60, staples=True, p0=(170, 330), p1=(470, 150), width=7):
    """Draw an incision line with red margin and staples; returns (image, ground-truth mask of the line + margin)."""
    gt = np.zeros(img.shape[:2], np.uint8)
    cv2.line(gt, p0, p1, 1, width + 10)
    out = img.copy()
    margin = cv2.GaussianBlur(gt.astype(np.float32), (0, 0), 4)[..., None]
    out = out * (1 - margin) + margin * (out * np.array([0.75, 0.7, 1.0]) + np.array([0, 0, redness * 0.3]))
    cv2.line(out, p0, p1, (60, 60, 120), 3)                            # dark scab line
    if staples:
        for t in np.linspace(0.05, 0.95, 12):
            x, y = int(p0[0] + t * (p1[0] - p0[0])), int(p0[1] + t * (p1[1] - p0[1]))
            cv2.line(out, (x - 6, y - 8), (x + 6, y + 8), (235, 235, 235), 2)
    return np.clip(out, 0, 255).astype(np.uint8), gt.astype(bool)


def jpg(img):
    return cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 92])[1].tobytes()


def mask_of(data):
    r = analyze(data)
    return r, r["_mask"]


@pytest.mark.parametrize("staples", [True, False])
def test_finds_the_drawn_incision(staples):
    img, gt = incision(skin_image(), staples=staples)
    r, mask = mask_of(jpg(img))
    assert r["quality"]["status"] == "good" and r["segmentation"]["found"]
    m = cv2.resize(mask.astype(np.uint8), (gt.shape[1], gt.shape[0])) > 0
    recall = (m & gt).sum() / gt.sum()
    precision = (m & gt).sum() / m.sum()
    assert recall > 0.6, recall
    assert precision > 0.3, precision   # the mask may include a margin of skin around the line


def test_darker_skin_tone_is_handled():
    img, gt = incision(skin_image(tone=(60, 85, 125)))
    r, mask = mask_of(jpg(img))
    m = cv2.resize(mask.astype(np.uint8), (gt.shape[1], gt.shape[0])) > 0
    assert r["segmentation"]["found"] and (m & gt).sum() / gt.sum() > 0.5


def test_purple_marker_ink_is_not_taken_for_the_wound():
    img, gt = incision(skin_image(), staples=False)
    cv2.line(img, (100, 60), (560, 90), (150, 40, 140), 4)              # surgical marker (purple) across the top
    r, mask = mask_of(jpg(img))
    m = cv2.resize(mask.astype(np.uint8), (gt.shape[1], gt.shape[0])) > 0
    assert (m & gt).sum() / max(m.sum(), 1) > 0.3


def test_bad_photos_ask_for_a_retake_instead_of_measuring():
    img, _ = incision(skin_image())
    dark = (img * 0.12).astype(np.uint8)
    blurry = cv2.GaussianBlur(img, (0, 0), 9)
    for bad in (dark, blurry):
        r = analyze(jpg(bad))
        assert r["quality"]["status"] in ("unusable", "questionable") and r["quality"]["problems"]
    assert analyze(b"not an image")["quality"]["status"] == "unusable"


def test_no_skin_no_measurement():
    r = analyze(jpg(np.full((400, 400, 3), (200, 120, 40), np.uint8)))   # a blue wall
    assert r["measurements"] is None


def test_comparison_same_site_redder_and_spreading():
    base = skin_image(seed=3)
    ref, _ = incision(base, redness=0)
    cur, _ = incision(base, redness=180)
    m = np.float32([[1, 0, 12], [0, 1, -8]])                             # phone moved a little
    cur = cv2.warpAffine(cur, m, (cur.shape[1], cur.shape[0]), borderMode=cv2.BORDER_REFLECT)
    r = analyze(jpg(cur), reference=jpg(ref))
    c = r["comparison"]
    assert c["available"] and c["registration"]["comparable"], c
    assert c["trend"] == "more_red", c


def test_comparison_same_photo_is_stable():
    img, _ = incision(skin_image(seed=4))
    c = analyze(jpg(img), reference=jpg(img))["comparison"]
    assert c["available"] and c["trend"] == "stable_colour" and abs(c["area_change_pct"]) < 10


def test_different_patients_are_not_compared():
    """The demo photos are three different real patients: the registration must refuse to compare them."""
    a, b = (PHOTOS / "day1.jpg").read_bytes(), (PHOTOS / "day3.jpg").read_bytes()
    c = analyze(b, reference=a)["comparison"]
    assert c["available"] is False and "same area" in c["reason"]


@pytest.mark.parametrize("name", ["day1", "day2", "day3"])
def test_real_photos_find_the_staple_line(name):
    r = analyze((PHOTOS / f"{name}.jpg").read_bytes())
    assert r["quality"]["status"] == "good" and r["segmentation"]["found"]
    assert "staple" in r["segmentation"]["method"]
    assert 0.5 < r["measurements"]["wound_area_pct_of_frame"] < 20
    assert overlay(r["_bgr"], r["_mask"], name)[:2] == b"\xff\xd8"     # a JPEG with the outline
    assert "_mask" not in strip_private(r)


def test_never_uses_diagnostic_words():
    r = strip_private(analyze((PHOTOS / "day1.jpg").read_bytes(), reference=(PHOTOS / "day2.jpg").read_bytes()))
    text = str(r).lower()
    for word in ("infect", "healed", "healthy", "safe", "sepsis", "cellulitis"):
        assert word not in text
    assert set(r["not_measured"]) >= {"swelling", "drainage", "warmth"}
    assert load((PHOTOS / "day1.jpg").read_bytes()).shape[2] == 3
