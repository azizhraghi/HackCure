"""D1-F: wound-photo analysis with OpenCV. Classical computer vision, explainable, nothing trained.

Why not a deep model: the public wound-segmentation checkpoints we found are trained on diabetic-foot / pressure ulcers,
need a GPU or are non-commercial; none is validated on fresh surgical incisions. A transparent pipeline whose every
number can be explained and tested on synthetic ground truth is more defensible than a black box we cannot check.
(`wound/README` in d1/README.md lists what we evaluated.)

Steps
1. Acquisition quality (blur, exposure, glare, how much skin is in view). Poor photo -> "retake", never a measurement.
2. Colour is always judged against the patient's own skin in the same photo, so a warm lamp does not look like inflammation.
3. Peri-wound skin reference: the patient's OWN skin around the site (outer ring), in CIELAB. No fixed skin tone.
4. Segmentation of the incision: each channel is compared with its own local background (local redness a*, local
   darkness L*, bright metal). A row of staples, when present, outlines the incision; otherwise the strongest elongated
   structure near the centre is kept (marker ink and bruises, which are purple, are ignored).
5. Measurements: area, redness (a* excess over own skin), colour spread, boundary regularity, dark/crust-coloured and
   pale-yellow regions, closure material (staples / sutures) count.
6. Longitudinal comparison: ORB feature registration against the reference photo. If the two photos do not show the same
   site (too few consistent matches) the comparison is refused instead of being shown as a change.

It reports what is visible. It never says infected / healed / safe. Swelling, discharge, depth and warmth are NOT
measurable from one 2-D photo and are listed as not measured.
"""

import io
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, ImageOps

VERSION = "wound-cv-0.1"
MAX_SIDE = 640


@dataclass(frozen=True)
class Limits:
    min_brightness: float = 22.0       # mean L*
    max_brightness: float = 92.0
    min_sharpness: float = 25.0        # variance of the Laplacian on the centre, 640 px image
    max_glare_fraction: float = 0.08   # share of near-white pixels in the centre
    min_skin_fraction: float = 0.20    # share of the frame that looks like skin
    redness_delta_a: float = 8.0       # a* above the patient's own skin that counts as red
    min_wound_fraction: float = 0.002  # smaller than this of the frame: nothing reliable found
    max_wound_fraction: float = 0.60
    min_registration_inliers: int = 12
    min_registration_ratio: float = 0.25


# ------------------------------------------------------------------ helpers

def load(data: bytes) -> np.ndarray:
    """Bytes -> BGR uint8, EXIF-rotated, longest side <= MAX_SIDE."""
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    im.thumbnail((MAX_SIDE, MAX_SIDE))
    return cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)


def _lab(bgr: np.ndarray) -> np.ndarray:
    """OpenCV 8-bit Lab -> real CIELAB (L 0-100, a/b about -128..127)."""
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    lab[..., 0] *= 100.0 / 255.0
    lab[..., 1:] -= 128.0
    return lab


def _skin_mask(bgr: np.ndarray) -> np.ndarray:
    ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
    m = cv2.inRange(ycrcb, (30, 133, 77), (255, 180, 135))
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0


# ------------------------------------------------------------------ 1. quality

def assess_quality(bgr: np.ndarray, limits: Limits = Limits()) -> dict:
    h, w = bgr.shape[:2]
    lab = _lab(bgr)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    cy0, cy1, cx0, cx1 = int(h * .2), int(h * .8), int(w * .2), int(w * .8)
    centre = gray[cy0:cy1, cx0:cx1]
    brightness = float(lab[..., 0].mean())
    sharpness = float(cv2.Laplacian(centre, cv2.CV_64F).var())
    glare = float((centre > 245).mean())
    skin = _skin_mask(bgr)
    skin_fraction = float(skin[cy0:cy1, cx0:cx1].mean())
    problems = []
    if brightness < limits.min_brightness:
        problems.append("too dark: add light")
    elif brightness > limits.max_brightness:
        problems.append("overexposed: move away from direct light")
    if sharpness < limits.min_sharpness:
        problems.append("blurry: hold the phone still and let it focus")
    if glare > limits.max_glare_fraction:
        problems.append("glare or reflection on the skin: tilt the phone")
    if skin_fraction < limits.min_skin_fraction:
        problems.append("not enough skin in the frame: centre the wound")
    hard = brightness < limits.min_brightness or skin_fraction < limits.min_skin_fraction or sharpness < limits.min_sharpness / 3
    return {"status": "unusable" if hard else "questionable" if problems else "good", "problems": problems,
            "brightness": round(brightness, 1), "sharpness": round(sharpness, 1), "glare_pct": round(glare * 100, 1),
            "skin_fraction": round(skin_fraction, 2)}


# ------------------------------------------------------------------ 2-4. segmentation

def _z(x: np.ndarray, where: np.ndarray) -> np.ndarray:
    v = x[where]
    med = float(np.median(v)) if v.size else 0.0
    mad = float(np.median(np.abs(v - med))) * 1.4826 + 1e-3 if v.size else 1.0
    return (x - med) / mad


def _staple_chain(bgr: np.ndarray, near_skin: np.ndarray) -> np.ndarray | None:
    """Metal staples: small bright, grey, LOCALLY brighter marks that come in a row. Returns the strip they outline."""
    h, w = near_skin.shape
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    v = hsv[..., 2]
    tophat = cv2.morphologyEx(v, cv2.MORPH_TOPHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)))
    bright = ((tophat > 35) & (hsv[..., 1] < 90) & near_skin).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(bright, 8)
    blobs = [i for i in range(1, n) if 3 <= st[i, cv2.CC_STAT_AREA] <= 250]
    if len(blobs) < 5:
        return None
    pts = cen[blobs]
    d = np.hypot(pts[:, None, 0] - pts[None, :, 0], pts[:, None, 1] - pts[None, :, 1])
    np.fill_diagonal(d, np.inf)
    spacing = max(h, w) * 0.09
    chained = [k for k in range(len(blobs)) if (d[k] < spacing).sum() >= 1]
    if len(chained) < 5:
        return None
    # largest connected chain of staples
    adj = d[np.ix_(chained, chained)] < spacing
    seen, best = set(), []
    for s0 in range(len(chained)):
        if s0 in seen:
            continue
        stack, group = [s0], []
        while stack:
            u = stack.pop()
            if u in seen:
                continue
            seen.add(u)
            group.append(u)
            stack.extend(np.nonzero(adj[u])[0].tolist())
        if len(group) > len(best):
            best = group
    if len(best) < 5:
        return None
    strip = np.zeros((h, w), np.uint8)
    members = [chained[k] for k in best]
    chain_pts = pts[members]
    horizontal = np.ptp(chain_pts[:, 0]) > np.ptp(chain_pts[:, 1])
    u, v = (chain_pts[:, 0], chain_pts[:, 1]) if horizontal else (chain_pts[:, 1], chain_pts[:, 0])
    # an incision is a smooth curve: drop bright spots that sit off it (highlights, hair glints)
    keep = np.ones(len(u), bool)
    for _ in range(3):
        coef = np.polyfit(u[keep], v[keep], 2)
        res = np.abs(np.polyval(coef, u) - v)
        keep = res <= max(2.5 * np.median(res[keep]), max(h, w) * 0.015)
        if keep.sum() < 5:
            return None
    order = np.argsort(u[keep])
    poly = chain_pts[keep][order].astype(np.int32)
    cv2.polylines(strip, [poly], False, 1, thickness=max(9, int(max(h, w) * 0.025)))
    for k, ok in zip(members, keep):
        if ok:
            strip[lab == blobs[k]] = 1
    _staple_chain.last_count = int(keep.sum())
    return strip > 0


def segment(bgr: np.ndarray, limits: Limits = Limits()) -> dict:
    """Find the incision / wound: pixels that stand out LOCALLY from the surrounding skin.

    A surgical wound is a thin, elongated structure (incision line, scab, staples, sutures) often with redness along it.
    Global colour thresholds fail under uneven light, so every channel is compared with its own large-scale blur
    (local background): local redness (a*), local darkness (L*) and bright metal (staples). The strongest elongated
    cluster near the centre is kept; broken pieces lying on the same line are merged.
    """
    # No global white balance: when skin fills the frame, grey-world would turn the skin grey. Every measure below is
    # relative to the surrounding skin of the same photo, which already cancels the colour of the light.
    balanced = bgr
    lab = _lab(balanced)
    h, w = lab.shape[:2]
    skin = _skin_mask(balanced)
    if skin.mean() < limits.min_skin_fraction * 0.5:
        return {"mask": None, "reason": "no skin found around the site", "lab": lab}
    near_skin = cv2.dilate(skin.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
    sigma = max(h, w) / 18.0
    L, a = lab[..., 0], lab[..., 1]
    a_loc = a - cv2.GaussianBlur(a, (0, 0), sigma)
    dark_loc = cv2.GaussianBlur(L, (0, 0), sigma) - L
    hsv = cv2.cvtColor(balanced, cv2.COLOR_BGR2HSV)
    metal = ((hsv[..., 2] > 200) & (hsv[..., 1] < 50)).astype(np.float32)
    b = lab[..., 2]
    b_loc = b - cv2.GaussianBlur(b, (0, 0), sigma)
    # Surgical-marker ink and bruises are purple/blue (b* drops); wound redness is red-orange. Do not count ink as wound.
    not_ink = (b_loc > -6).astype(np.float32)
    score = (np.maximum(_z(a_loc, skin), 0) + 0.7 * np.maximum(_z(dark_loc, skin), 0)) * not_ink + 3.0 * metal
    score = cv2.GaussianBlur(score.astype(np.float32), (0, 0), 1.5)
    score[~near_skin] = 0
    border = np.zeros((h, w), bool)
    border[int(h * .04):int(h * .96), int(w * .04):int(w * .96)] = True
    score[~border] = 0
    thr = max(float(np.percentile(score[near_skin], 96)), 3.0)
    staples = _staple_chain(balanced, near_skin)
    if staples is not None:
        # A row of staples marks the incision: keep the strip they outline (plus the abnormal pixels right along it).
        along = cv2.dilate(staples.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))) > 0
        mask = staples | ((score > thr * 0.7) & along)
        mask = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))) > 0
        out = _finish(mask, lab, skin, balanced, limits, "staple row + local redness/darkness along it")
        out["staples"] = getattr(_staple_chain, "last_count", None)
        return out
    cand = (score > thr).astype(np.uint8)
    cand = cv2.morphologyEx(cand, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13)))
    n, labels, stats, cent = cv2.connectedComponentsWithStats(cand, 8)
    comps = []
    for i in range(1, n):
        area = stats[i, cv2.CC_STAT_AREA]
        if area < 30:
            continue
        pts = np.column_stack(np.nonzero(labels == i))[:, ::-1].astype(np.float32)
        (cx, cy), (rw, rh), _ = cv2.minAreaRect(pts)
        elong = max(rw, rh) / max(min(rw, rh), 1.0)
        dist = np.hypot(cx - w / 2, cy - h / 2) / np.hypot(w / 2, h / 2)
        strength = float(score[labels == i].mean())
        comps.append((area * min(elong, 8.0) * strength * (1.0 - 0.7 * dist), i, pts))
    if not comps:
        return {"mask": None, "reason": "nothing stands out from the surrounding skin", "lab": lab}
    comps.sort(key=lambda c: -c[0])
    _, best, pts = comps[0]
    keep = labels == best
    # merge other pieces lying on the same line (a broken incision line), refitting the line as it grows
    merged, rest = [pts], [c for c in comps[1:] if c[0] >= comps[0][0] * 0.02]
    changed = True
    while changed and rest:
        changed = False
        vx, vy, x0, y0 = cv2.fitLine(np.vstack(merged), cv2.DIST_L2, 0, 0.01, 0.01).ravel()
        for c in list(rest):
            d = np.abs((c[2][:, 0] - x0) * vy - (c[2][:, 1] - y0) * vx).mean()
            if d < max(h, w) * 0.05:
                keep |= labels == c[1]
                merged.append(c[2])
                rest.remove(c)
                changed = True
    mask = cv2.dilate(keep.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))) > 0
    return _finish(mask, lab, skin, balanced, limits, "local redness/darkness, strongest elongated structure")


def _finish(mask, lab, skin, balanced, limits: Limits, how: str) -> dict:
    frac = float(mask.mean())
    if frac < limits.min_wound_fraction:
        return {"mask": None, "reason": "abnormal region too small to measure reliably", "lab": lab}
    # The patient's own skin right around the wound (a band 25-60 px away) is the colour reference.
    k1 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (51, 51))
    k2 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (121, 121))
    band = (cv2.dilate(mask.astype(np.uint8), k2) > 0) & ~(cv2.dilate(mask.astype(np.uint8), k1) > 0) & skin
    if band.sum() < 100:
        band = skin & ~mask
    ref_lab = np.median(lab[band], axis=0)
    return {"mask": mask, "reason": None, "lab": lab, "ref": ref_lab, "ref_std": lab[band].std(axis=0), "skin": skin,
            "too_large": frac > limits.max_wound_fraction, "balanced": balanced, "how": how}


# ------------------------------------------------------------------ 5. measurements

def measure(seg: dict, bgr: np.ndarray, limits: Limits = Limits()) -> dict:
    mask, lab, ref = seg["mask"], seg["lab"], seg["ref"]
    h, w = mask.shape
    pix = lab[mask]
    d_a = pix[:, 1] - ref[1]
    cnts, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnt = max(cnts, key=cv2.contourArea)
    area, perim = float(cv2.contourArea(cnt)), float(cv2.arcLength(cnt, True))
    hull = cv2.convexHull(cnt)
    solidity = area / max(cv2.contourArea(hull), 1.0)
    circularity = 4 * np.pi * area / max(perim * perim, 1.0)
    x, y, bw, bh = cv2.boundingRect(cnt)
    # redness in a 25 px ring just outside the mask: does the redness spread beyond the visible wound?
    ring = cv2.dilate(mask.astype(np.uint8), np.ones((25, 25), np.uint8)).astype(bool) & ~mask
    ring_a = float(np.median(lab[ring][:, 1] - ref[1])) if ring.any() else 0.0
    L, a, b = pix[:, 0], pix[:, 1], pix[:, 2]
    dark = float(((L < ref[0] - 28) ).mean() * 100)                       # dark / crust-coloured
    pale = float(((L > ref[0] + 8) & (b > ref[2] + 12) & (a < ref[1] + 6)).mean() * 100)  # pale-yellow regions
    return {
        "wound_area_pct_of_frame": round(area / (h * w) * 100, 2),
        "bbox_aspect": round(bw / max(bh, 1), 2),
        "redness_mean_delta_a": round(float(d_a.mean()), 1),
        "redness_area_pct": round(float((d_a > limits.redness_delta_a).mean() * 100), 1),
        "redness_spread_ring_delta_a": round(ring_a, 1),
        "colour_variability": round(float(pix.std(axis=0).mean()), 1),
        "boundary_solidity": round(float(solidity), 2),
        "boundary_circularity": round(float(circularity), 2),
        "dark_crust_coloured_pct": round(dark, 1),
        "pale_yellow_pct": round(pale, 1),
        "skin_reference_lab": [round(float(v), 1) for v in ref],
        "closure_material": ({"staple_like_blobs": seg["staples"], "note": "bright metal-like marks along the incision; one staple can show as several marks"}
                             if seg.get("staples") else _closure_material(seg.get("balanced", bgr), mask)),
    }


def _closure_material(bgr: np.ndarray, mask: np.ndarray) -> dict:
    """Metal staples = small bright, low-saturation blobs inside/near the wound; sutures = thin dark lines (rough count)."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    near = cv2.dilate(mask.astype(np.uint8), np.ones((31, 31), np.uint8)) > 0
    bright = ((hsv[..., 2] > 190) & (hsv[..., 1] < 60) & near).astype(np.uint8)
    n, _, stats, _ = cv2.connectedComponentsWithStats(cv2.morphologyEx(bright, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8)), 8)
    staples = sum(1 for i in range(1, n) if 6 <= stats[i, cv2.CC_STAT_AREA] <= 400)
    return {"staple_like_blobs": int(staples), "note": "count of staple-like bright spots, indicative only"}


# ------------------------------------------------------------------ 6. registration + comparison

def register(ref_bgr: np.ndarray, cur_bgr: np.ndarray, limits: Limits = Limits()) -> dict:
    """Do the two photos show the same site? ORB + RANSAC homography of the current photo onto the reference."""
    orb = cv2.ORB_create(1500)
    g1, g2 = (cv2.cvtColor(x, cv2.COLOR_BGR2GRAY) for x in (ref_bgr, cur_bgr))
    k1, d1 = orb.detectAndCompute(g1, None)
    k2, d2 = orb.detectAndCompute(g2, None)
    if d1 is None or d2 is None or len(k1) < 20 or len(k2) < 20:
        return {"comparable": False, "reason": "too little texture to match the two photos", "homography": None}
    matches = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(d2, d1)
    matches = sorted(matches, key=lambda m: m.distance)[:300]
    if len(matches) < limits.min_registration_inliers:
        return {"comparable": False, "reason": "the two photos do not seem to show the same area", "homography": None}
    src = np.float32([k2[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
    dst = np.float32([k1[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
    H, inl = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
    n_in = int(inl.sum()) if inl is not None else 0
    ratio = n_in / max(len(matches), 1)
    if H is None or n_in < limits.min_registration_inliers or ratio < limits.min_registration_ratio:
        return {"comparable": False, "reason": "the two photos do not seem to show the same area "
                f"({n_in} consistent points)", "homography": None, "inliers": n_in}
    # reject absurd warps (wrong site that matched on texture)
    scale = float(np.sqrt(abs(np.linalg.det(H[:2, :2]))))
    if not 0.4 < scale < 2.5:
        return {"comparable": False, "reason": "the photos were taken from very different distances", "homography": None,
                "inliers": n_in, "scale": round(scale, 2)}
    return {"comparable": True, "inliers": n_in, "inlier_ratio": round(ratio, 2), "scale": round(scale, 2), "homography": H}


def compare(ref: dict, cur: dict, reg: dict, limits: Limits = Limits()) -> dict:
    """ref/cur: results of analyze(). Unknown stays unknown; a different site is never reported as a change."""
    if not ref.get("measurements") or not cur.get("measurements"):
        return {"available": False, "reason": "one of the photos could not be measured: unknown"}
    if "unusable" in (ref["quality"]["status"], cur["quality"]["status"]):
        return {"available": False, "reason": "photo quality too low to compare: unknown"}
    if not reg.get("comparable"):
        return {"available": False, "reason": reg.get("reason", "not the same site"), "registration": _public_reg(reg)}
    r, c = ref["measurements"], cur["measurements"]
    area_ratio = c["wound_area_pct_of_frame"] / max(r["wound_area_pct_of_frame"], 1e-6) / reg["scale"] ** 2
    d_area = round((area_ratio - 1) * 100)
    d_red = round(c["redness_mean_delta_a"] - r["redness_mean_delta_a"], 1)
    d_spread = round(c["redness_spread_ring_delta_a"] - r["redness_spread_ring_delta_a"], 1)
    notes = []
    if d_red >= 4 or d_spread >= 4:
        trend = "more_red"
        notes.append("redder than the reference photo" + (", and the redness extends beyond the wound edge" if d_spread >= 4 else ""))
    elif d_red <= -4:
        trend = "less_red"
        notes.append("less red than the reference photo")
    else:
        trend = "stable_colour"
        notes.append("no clear change in redness")
    if d_area >= 30:
        notes.append(f"the marked area is about {d_area}% larger (after correcting for distance)")
    elif d_area <= -30:
        notes.append(f"the marked area is about {-d_area}% smaller (after correcting for distance)")
    return {"available": True, "trend": trend, "summary": "; ".join(notes), "redness_change_delta_a": d_red,
            "redness_spread_change": d_spread, "area_change_pct": d_area, "registration": _public_reg(reg),
            "quality": "questionable" if "questionable" in (ref["quality"]["status"], cur["quality"]["status"]) else "good",
            "caution": "Computed from two photos: light, angle and distance change the numbers. Not a diagnosis."}


def _public_reg(reg: dict) -> dict:
    return {k: v for k, v in reg.items() if k != "homography"}


# ------------------------------------------------------------------ 7. overlay

def overlay(bgr: np.ndarray, mask: np.ndarray | None, caption: str = "") -> bytes:
    """JPEG of the photo with the analysed region outlined (so a person can check what the code looked at)."""
    out = bgr.copy()
    if mask is not None:
        tint = out.copy()
        tint[mask] = (0.55 * tint[mask] + 0.45 * np.array([60, 200, 90])).astype(np.uint8)
        out = tint
        cnts, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(out, cnts, -1, (40, 220, 255), 2)
    if caption:
        cv2.rectangle(out, (0, 0), (out.shape[1], 22), (30, 30, 30), -1)
        cv2.putText(out, caption[:70], (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    ok, buf = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return buf.tobytes()


# ------------------------------------------------------------------ public entry point

NOT_MEASURED = ["swelling", "drainage", "depth", "warmth", "pain"]


def analyze(data: bytes, reference: bytes | None = None, limits: Limits = Limits()) -> dict:
    """Full analysis of one wound photo (optionally compared with the patient's reference photo)."""
    try:
        bgr = load(data)
    except Exception as e:  # not an image / corrupt
        return {"version": VERSION, "quality": {"status": "unusable", "problems": [f"not a readable image ({type(e).__name__})"]},
                "measurements": None, "segmentation": {"found": False, "reason": "unreadable image"}, "not_measured": NOT_MEASURED}
    quality = assess_quality(bgr, limits)
    out = {"version": VERSION, "method": "OpenCV: local colour contrast in CIELAB + staple detection + ORB registration (classical vision, no learning)",
           "quality": quality, "not_measured": NOT_MEASURED, "measurements": None, "comparison": None,
           "segmentation": {"found": False, "reason": "photo quality too low"}, "_mask": None, "_bgr": bgr}
    if quality["status"] == "unusable":
        return out
    seg = segment(bgr, limits)
    if seg["mask"] is None:
        out["segmentation"] = {"found": False, "reason": seg["reason"]}
        return out
    out["_mask"] = seg["mask"]
    m = measure(seg, bgr, limits)
    out["measurements"] = m
    out["segmentation"] = {"found": True, "method": seg.get("how"),
                           "area_pct_of_frame": m["wound_area_pct_of_frame"],
                           "caution": "region may include normal tissue around the wound" if seg.get("too_large") else None}
    if reference is not None:
        ref = analyze(reference)
        try:
            reg = register(ref["_bgr"], bgr, limits) if ref.get("_bgr") is not None else {"comparable": False, "reason": "no reference"}
        except cv2.error:
            reg = {"comparable": False, "reason": "registration failed"}
        out["comparison"] = compare(ref, out, reg, limits)
    return out


def strip_private(result: dict) -> dict:
    """JSON-safe copy (drops the numpy arrays used for rendering)."""
    return {k: v for k, v in result.items() if not k.startswith("_")}
