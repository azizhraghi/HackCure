"""D1-F learned model: surgical-wound attributes from a photo (SurgWound labels), on top of a frozen DINOv2 encoder.

Design (chosen for a small, expert-labelled dataset and a CPU):
- Encoder: facebook/dinov2-small (self-supervised ViT-S/14, Apache-2.0), frozen. Image features = [CLS token,
  mean of patch tokens], averaged over the photo and its mirror image.
- Heads: one regularised logistic regression per attribute, class-balanced, trained on the SurgWound train+val
  split (surgeon annotations, CC BY-SA 4.0), tested once on the official test split (scripts/train_wound_model.py).
- Each head has an operating threshold chosen on cross-validation for high sensitivity (missing a sign is worse
  than a false alarm), and an "uncertain" band around it: the model abstains instead of guessing.
- Explanation: occlusion sensitivity. Each cell of a 7x7 grid is greyed out and the drop in the head's score is
  measured: the heat map shows which regions of the photo the decision depended on (faithful to the whole model).

The output describes visible attributes as surgeons labelled them. It is decision support for the care team,
never a diagnosis, and it can only ADD a reason for review, never close or downgrade one.
"""

from __future__ import annotations

import io
from functools import lru_cache
from pathlib import Path

import numpy as np

ENCODER = "facebook/dinov2-small"
HEADS_FILE = Path(__file__).resolve().parents[3] / "models" / "wound_heads.joblib"
SIZE = 224

# What each head says, in plain words (positive class first).
HEADS = {
    "erythema": ("redness around the wound (erythema)", "no clear redness"),
    "edema": ("swelling around the wound (edema)", "no clear swelling"),
    "exudate": ("visible fluid or discharge (exudate)", "no visible discharge"),
    "not_healed": ("wound not yet healed", "wound looks healed"),
    "elevated_risk": ("surgeons would rate infection risk medium/high", "surgeons would rate infection risk low"),
    "needs_review": ("surgeons would want a professional review (clinic or emergency)", "surgeons would suggest routine home care"),
}


@lru_cache(maxsize=2)
def _encoder(name: str = ENCODER):
    import torch
    from transformers import AutoImageProcessor, AutoModel, CLIPVisionModel
    torch.set_num_threads(min(4, torch.get_num_threads()))  # leave CPU for the API; avoids native crashes under memory pressure
    proc = AutoImageProcessor.from_pretrained(name)
    model = (CLIPVisionModel if "clip" in name else AutoModel).from_pretrained(name).eval()
    return proc, model


def embed(images: list, with_patches: bool = False, encoder: str | None = None):
    """PIL images -> features (n, 2*d) [CLS, mean patches] averaged with the mirror image; optionally patch tokens."""
    import torch
    from PIL import ImageOps
    name = encoder or ENCODER
    proc, model = _encoder(name)
    feats, patches = [], []
    with torch.no_grad():
        for im in images:
            im = im.convert("RGB")
            kw = {} if "clip" in name else {"size": {"height": SIZE, "width": SIZE}, "do_center_crop": False}
            batch = proc(images=[im, ImageOps.mirror(im)], return_tensors="pt", **kw)
            h = model(**batch).last_hidden_state            # (2, 1 + n_patches, d)
            cls, pt = h[:, 0], h[:, 1:]
            feats.append(torch.cat([cls, pt.mean(1)], dim=1).mean(0).numpy())
            if with_patches:
                patches.append(pt[0].numpy())                # unmirrored patch tokens, for the heat map
    feats = np.stack(feats)
    return (feats, patches) if with_patches else feats


@lru_cache(maxsize=1)
def load_heads(path: str | None = None) -> dict:
    import joblib
    return joblib.load(path or HEADS_FILE)


def available() -> tuple[bool, str | None]:
    if not HEADS_FILE.exists():
        return False, f"{HEADS_FILE.name} missing: run scripts/train_wound_model.py"
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except ImportError as e:
        return False, f"{e.name} not installed (pip install torch transformers)"
    return True, None


def predict(data: bytes, heatmap_for: str | None = "erythema") -> dict:
    """Photo bytes -> per-attribute probability, decision (yes / no / uncertain) and an optional evidence heat map."""
    from PIL import Image, ImageOps
    bundle = load_heads()
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    x, patches = embed([im], with_patches=True, encoder=bundle.get("encoder"))
    out = {}
    for name, h in bundle["heads"].items():
        p = float(h["model"].predict_proba(h["scaler"].transform(x))[0, 1])
        thr, band = h["threshold"], h["band"]
        decision = "uncertain" if abs(p - thr) < band else ("yes" if p >= thr else "no")
        pos, neg = HEADS[name]
        out[name] = {"probability": round(p, 3), "threshold": round(thr, 3), "decision": decision,
                     "text": pos if decision == "yes" else neg if decision == "no" else f"uncertain: {pos}?",
                     "test_auroc": h["metrics"]["test"]["auroc"], "test_sensitivity": h["metrics"]["test"]["sensitivity"],
                     "test_specificity": h["metrics"]["test"]["specificity"]}
    result = {"version": bundle["version"], "encoder": bundle.get("encoder", ENCODER), "trained_on": bundle["dataset"], "attributes": out}
    if heatmap_for and heatmap_for in bundle["heads"]:
        result["_heatmap"] = _heatmap(bundle["heads"][heatmap_for], im, bundle.get("encoder"))
    return result


def _heatmap(head: dict, im, encoder: str | None, grid: int = 7) -> np.ndarray:
    """Occlusion sensitivity: grey out each cell of a grid and measure how much the head's score DROPS.
    Model-agnostic and faithful to the full head (CLS + patches), unlike raw patch-token attributions."""
    import torch
    from PIL import ImageDraw
    proc, model = _encoder(encoder or ENCODER)
    base = im.convert("RGB").resize((SIZE, SIZE))
    cell = SIZE / grid
    variants = [base]
    for i in range(grid):
        for j in range(grid):
            v = base.copy()
            ImageDraw.Draw(v).rectangle([j * cell, i * cell, (j + 1) * cell, (i + 1) * cell], fill=(128, 128, 128))
            variants.append(v)
    kw = {} if "clip" in (encoder or ENCODER) else {"size": {"height": SIZE, "width": SIZE}, "do_center_crop": False}
    feats = []
    with torch.no_grad():
        for k in range(0, len(variants), 2):  # small batches: bounded memory on a laptop
            h = model(**proc(images=variants[k:k + 2], return_tensors="pt", **kw)).last_hidden_state
            feats.append(torch.cat([h[:, 0], h[:, 1:].mean(1)], dim=1).numpy())
    feats = np.concatenate(feats)
    p = head["model"].predict_proba(head["scaler"].transform(feats))[:, 1]
    return (p[0] - p[1:]).reshape(grid, grid)         # > 0: this region supported the attribute


def heatmap_overlay(data: bytes, grid: np.ndarray) -> bytes:
    """JPEG: the photo with the positive-evidence map on top (red = where the evidence came from)."""
    import cv2
    from PIL import Image, ImageOps
    im = np.asarray(ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB"))
    im = cv2.resize(im, (int(im.shape[1] * 512 / max(im.shape[:2])), int(im.shape[0] * 512 / max(im.shape[:2]))))
    g = np.clip(grid, 0, None)
    g = g / (g.max() + 1e-9)
    g = cv2.resize(g.astype(np.float32), (im.shape[1], im.shape[0]), interpolation=cv2.INTER_CUBIC)
    g = np.clip((g - 0.35) / 0.65, 0, 1)   # colour only the regions that mattered most
    color = cv2.applyColorMap((g * 255).astype(np.uint8), cv2.COLORMAP_JET)[..., ::-1]
    out = (im * (1 - 0.45 * g[..., None]) + color * 0.45 * g[..., None]).astype(np.uint8)
    ok, buf = cv2.imencode(".jpg", out[..., ::-1], [cv2.IMWRITE_JPEG_QUALITY, 85])
    return buf.tobytes()
