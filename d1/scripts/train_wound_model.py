"""Train and evaluate the D1-F wound-attribute model on SurgWound (see src/surgiguard_d1/wound/model.py).

    python scripts/prepare_surgwound.py <hf files> <prep>      # once
    python scripts/train_wound_model.py <prep>                  # ~10 min on a laptop CPU

Protocol (no test-set peeking):
1. Frozen DINOv2-small features for every image (cached in <prep>/features.npz).
2. Per attribute, on the official train+val split only: 5-fold stratified cross-validation picks the
   regularisation C (by AUROC), then out-of-fold probabilities pick the operating threshold for a target
   sensitivity of 0.85 and an "uncertain" band.
3. The final head is fitted on train+val and evaluated ONCE on the official test split: AUROC with a
   bootstrap 95% CI, sensitivity, specificity, balanced accuracy, abstention rate, and baselines
   (majority class; for erythema also the OpenCV redness measure used before this model).
Writes models/wound_heads.joblib, models/wound_model_metrics.json.
"""

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from surgiguard_d1.wound import model as wm  # noqa: E402

POS = {
    "erythema": ("erythema", {"Existent"}, {"Non-existent"}),
    "edema": ("edema", {"Existent"}, {"Non-existent"}),
    "exudate": ("exudate", {"Serous", "Sanguineous", "Purulent", "Seropurulent"}, {"Non-existent"}),
    "not_healed": ("healing", {"Not Healed"}, {"Healed"}),
    "elevated_risk": ("infection_risk", {"Medium", "High"}, {"Low"}),
    "needs_review": ("urgency", {"Clinic Visit (Yellow): Requires professional evaluation within 48 hours",
                                 "Emergency Care (Red): Seek immediate medical attention"},
                     {"Home Care (Green): Manage with routine care"}),
}
TARGET_SENSITIVITY = 0.85
CS = [0.0003, 0.001, 0.003, 0.01, 0.03, 0.1]
RNG = np.random.default_rng(0)


def features(prep: Path, rows: list[dict], encoder: str = wm.ENCODER) -> np.ndarray:
    cache = prep / ("features.npz" if encoder == wm.ENCODER else f"features_{encoder.replace('/', '_')}.npz")
    if cache.exists():
        z = np.load(cache, allow_pickle=True)
        if list(z["images"]) == [r["image"] for r in rows]:
            return z["x"]
    from PIL import Image
    xs = []
    for i, r in enumerate(rows):
        xs.append(wm.embed([Image.open(prep / r["image"])], encoder=encoder)[0])
        if i % 50 == 0:
            print(f"  features {i}/{len(rows)}", flush=True)
    x = np.stack(xs)
    np.savez(cache, x=x, images=np.array([r["image"] for r in rows]))
    return x


def bootstrap_auc(y, p, n=1000):
    vals = []
    for _ in range(n):
        idx = RNG.integers(0, len(y), len(y))
        if len(set(y[idx])) == 2:
            vals.append(roc_auc_score(y[idx], p[idx]))
    return [round(float(np.percentile(vals, 2.5)), 3), round(float(np.percentile(vals, 97.5)), 3)]


def at_threshold(y, p, thr, band):
    keep = np.abs(p - thr) >= band
    pred = (p >= thr).astype(int)
    tp = int(((pred == 1) & (y == 1) & keep).sum()); fn = int(((pred == 0) & (y == 1) & keep).sum())
    tn = int(((pred == 0) & (y == 0) & keep).sum()); fp = int(((pred == 1) & (y == 0) & keep).sum())
    sens = tp / max(tp + fn, 1); spec = tn / max(tn + fp, 1)
    return {"sensitivity": round(sens, 3), "specificity": round(spec, 3), "balanced_accuracy": round((sens + spec) / 2, 3),
            "abstained_pct": round(float((~keep).mean() * 100), 1), "tp": tp, "fn": fn, "tn": tn, "fp": fp}


def opencv_redness(prep: Path, rows: list[dict]) -> np.ndarray:
    from surgiguard_d1.wound import analyze
    out = []
    for r in rows:
        m = analyze((prep / r["image"]).read_bytes()).get("measurements") or {}
        out.append(m.get("redness_mean_delta_a", np.nan))
    return np.array(out, dtype=float)


ENCODER_CANDIDATES = ["facebook/dinov2-small", "openai/clip-vit-base-patch16"]


def choose_encoder(prep: Path, rows: list[dict]) -> str:
    """Pick the encoder by mean cross-validated AUROC on train+val only (the test split is never looked at)."""
    split = np.array([r["split"] for r in rows])
    scores = {}
    for enc in ENCODER_CANDIDATES:
        x = features(prep, rows, enc)
        aucs = []
        for name, (col, pos, neg) in POS.items():
            lab = np.array([1 if r[col] in pos else 0 if r[col] in neg else -1 for r in rows])
            tr = (split != "test") & (lab >= 0)
            best = 0
            for c in CS:
                pipe = make_pipeline(StandardScaler(), LogisticRegression(C=c, class_weight="balanced", max_iter=4000))
                oof = cross_val_predict(pipe, x[tr], lab[tr], cv=StratifiedKFold(5, shuffle=True, random_state=0),
                                        method="predict_proba")[:, 1]
                best = max(best, roc_auc_score(lab[tr], oof))
            aucs.append(best)
        scores[enc] = round(float(np.mean(aucs)), 3)
        print(f"encoder {enc}: mean CV AUROC {scores[enc]} {[round(a, 3) for a in aucs]}", flush=True)
    return max(scores, key=scores.get), scores


def main(prep: Path) -> None:
    rows = list(csv.DictReader(open(prep / "labels.csv", encoding="utf-8")))
    encoder, encoder_scores = choose_encoder(prep, rows)
    print("chosen encoder:", encoder, flush=True)
    x = features(prep, rows, encoder)
    split = np.array([r["split"] for r in rows])
    heads, metrics = {}, {}
    for name, (col, pos, neg) in POS.items():
        lab = np.array([1 if r[col] in pos else 0 if r[col] in neg else -1 for r in rows])
        tr = (split != "test") & (lab >= 0)
        te = (split == "test") & (lab >= 0)
        y_tr, y_te = lab[tr], lab[te]
        cv = StratifiedKFold(5, shuffle=True, random_state=0)
        best_c, best_auc = None, -1
        for c in CS:
            pipe = make_pipeline(StandardScaler(), LogisticRegression(C=c, class_weight="balanced", max_iter=4000))
            oof = cross_val_predict(pipe, x[tr], y_tr, cv=cv, method="predict_proba")[:, 1]
            auc = roc_auc_score(y_tr, oof)
            if auc > best_auc:
                best_c, best_auc, best_oof = c, auc, oof
        # threshold: highest one that still reaches the target sensitivity on out-of-fold predictions
        cands = np.sort(np.unique(best_oof))[::-1]
        thr = next((t for t in cands if (best_oof[y_tr == 1] >= t).mean() >= TARGET_SENSITIVITY), 0.5)
        band = 0.05
        scaler = StandardScaler().fit(x[tr])
        clf = LogisticRegression(C=best_c, class_weight="balanced", max_iter=4000).fit(scaler.transform(x[tr]), y_tr)
        p_te = clf.predict_proba(scaler.transform(x[te]))[:, 1]
        test = {"n": int(te.sum()), "positives": int(y_te.sum()), "auroc": round(float(roc_auc_score(y_te, p_te)), 3),
                "auroc_95ci": bootstrap_auc(y_te, p_te), **at_threshold(y_te, p_te, thr, band),
                "no_abstention": at_threshold(y_te, p_te, thr, 0.0),
                "majority_baseline_balanced_accuracy": 0.5,
                "majority_baseline_accuracy": round(float(max(y_te.mean(), 1 - y_te.mean())), 3)}
        m = {"label_column": col, "positive": sorted(pos), "negative": sorted(neg), "train_n": int(tr.sum()),
             "train_positives": int(y_tr.sum()), "C": best_c, "cv_auroc": round(float(best_auc), 3),
             "threshold": round(float(thr), 4), "band": band,
             "cv_at_threshold": at_threshold(y_tr, best_oof, thr, band), "test": test}
        if name == "erythema":
            red = opencv_redness(prep, [r for r, k in zip(rows, te) if k])
            ok = ~np.isnan(red)
            m["test"]["opencv_redness_baseline_auroc"] = round(float(roc_auc_score(y_te[ok], red[ok])), 3)
            m["test"]["opencv_redness_baseline_coverage_pct"] = round(float(ok.mean() * 100), 1)
        heads[name] = {"model": clf, "scaler": scaler, "threshold": float(thr), "band": band, "metrics": m}
        metrics[name] = m
        print(f"{name:14s} CV AUROC {best_auc:.3f} | TEST AUROC {test['auroc']} {test['auroc_95ci']} "
              f"sens {test['sensitivity']} spec {test['specificity']} abstain {test['abstained_pct']}% (n={test['n']}, +{test['positives']})",
              flush=True)
    bundle = {"version": "wound-attr-0.2", "encoder": encoder, "encoder_cv_auroc": encoder_scores, "trained_at": datetime.now(timezone.utc).isoformat(),
              "dataset": "SurgWound (Hugging Face Sonulee/SurgWound, CC BY-SA 4.0; surgeon labels, OSU Wexner)",
              "heads": heads}
    out = ROOT / "models"
    out.mkdir(exist_ok=True)
    import joblib
    joblib.dump(bundle, out / "wound_heads.joblib", compress=3)
    (out / "wound_model_metrics.json").write_text(json.dumps({k: v for k, v in bundle.items() if k != "heads"} | {"heads": metrics},
                                                             indent=1), encoding="utf-8")
    print("saved", out / "wound_heads.joblib")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
