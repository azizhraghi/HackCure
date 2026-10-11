"""The trained wound-attribute model (models/wound_heads.joblib): shipped metrics and a real prediction.

Skipped when torch / transformers are not installed or the encoder is not cached and there is no network."""

import json
from pathlib import Path

import pytest

from surgiguard_d1.wound import model as wm

ROOT = Path(__file__).resolve().parents[1]
PHOTOS = ROOT.parent / "backend" / "seed" / "photos"
ok, why = wm.available()
needs_model = pytest.mark.skipif(not ok, reason=why or "")


def test_metrics_file_documents_an_honest_held_out_evaluation():
    m = json.loads((ROOT / "models" / "wound_model_metrics.json").read_text(encoding="utf-8"))
    assert "SurgWound" in m["dataset"] and m["encoder"]
    for name, h in m["heads"].items():
        t = h["test"]
        assert name in wm.HEADS
        assert t["n"] >= 100 and 0.5 < t["auroc"] <= 1.0             # better than chance on the untouched test split
        lo, hi = t["auroc_95ci"]
        assert lo <= t["auroc"] <= hi
        assert h["cv_at_threshold"]["sensitivity"] >= 0.8              # threshold chosen for sensitivity, on CV only
    # the trained model beats the OpenCV redness measure used before it, for redness
    e = m["heads"]["erythema"]["test"]
    assert e["auroc"] > e["opencv_redness_baseline_auroc"]


@needs_model
def test_predicts_every_attribute_with_a_decision_and_an_evidence_map():
    try:
        res = wm.predict((PHOTOS / "day1.jpg").read_bytes())
    except OSError as e:  # encoder not cached and offline
        pytest.skip(str(e))
    assert set(res["attributes"]) == set(wm.HEADS)
    for a in res["attributes"].values():
        assert 0 <= a["probability"] <= 1 and a["decision"] in ("yes", "no", "uncertain") and a["text"]
    grid = res["_heatmap"]
    assert grid.ndim == 2 and grid.shape[0] == grid.shape[1]
    assert wm.heatmap_overlay((PHOTOS / "day1.jpg").read_bytes(), grid)[:2] == b"\xff\xd8"
