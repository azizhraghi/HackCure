"""Model of the normal recovery trajectory.

Given a patient's background and a postoperative day, it predicts what a
metric normally is for patients like this one: a typical value and a band
that most such patients fall inside. It is learned from past patients'
recoveries (see dataset.py), by gradient-boosted quantile regression.
"""

import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import joblib
import numpy as np
from pydantic import BaseModel
from sklearn.ensemble import HistGradientBoostingRegressor

from ..physiology.codes import CANONICAL_UNITS, OPTIONAL_UNITS
from .dataset import FeatureSpec, Row

MODEL_VERSION = "trajectory-gbq-0.1.0"
# The band runs from the 10th to the 90th percentile: about 8 in 10 similar
# patients are expected inside it.
LOWER_Q, MEDIAN_Q, UPPER_Q = 0.1, 0.5, 0.9

DataOrigin = Literal["real", "simulated", "mixed"]


@dataclass(frozen=True)
class PatientProfile:
    numeric: dict[str, float] = field(default_factory=dict)
    categorical: dict[str, str] = field(default_factory=dict)
    flags: frozenset[str] = frozenset()


class ExpectedPoint(BaseModel):
    day: float
    lower: float
    median: float
    upper: float


class ExpectedTrajectory(BaseModel):
    metric: str
    unit: str | None
    status: Literal["available", "abstained"]
    points: list[ExpectedPoint]
    reasons: list[str]  # why it abstained, or which requested days were dropped
    used_inputs: list[str] = []  # dossier fields the model took into account
    unused_inputs: list[str] = []  # dossier fields it has never learned from
    band_coverage: float = UPPER_Q - LOWER_Q
    model_version: str
    data_origin: DataOrigin
    training_patients: int


class TrajectoryModel:
    def __init__(self, spec: FeatureSpec, data_origin: DataOrigin) -> None:
        self.spec = spec
        self.data_origin: DataOrigin = data_origin
        self._models: dict[str, dict[float, HistGradientBoostingRegressor]] = {}
        self._support: dict[str, dict] = {}  # what each metric was trained on
        self._data_hash = ""

    # -------------------------------------------------------------- training

    def fit(self, rows: list[Row], min_patients: int = 30) -> "TrajectoryModel":
        """Train one set of quantile models per metric.

        A metric with fewer than `min_patients` patients is skipped; asking
        for it later gives an abstention, not a guess.
        """
        self._category_codes = {
            c: {v: i for i, v in enumerate(sorted({r.categorical[c] for r in rows if c in r.categorical}))}
            for c in (*self.spec.categorical, *self.spec.optional_categorical)
        }
        self._data_hash = _hash_rows(rows)
        for metric in sorted({r.metric for r in rows}):
            mrows = [r for r in rows if r.metric == metric and self._complete(r)]
            patients = {r.patient_id for r in mrows}
            if len(patients) < min_patients:
                continue
            X = np.array([self._encode(_profile(r), r.day) for r in mrows])
            y = np.array([r.value for r in mrows])
            first_cat = 1 + len(self.spec.numeric) + len(self.spec.optional_numeric)
            n_cat = len(self.spec.categorical) + len(self.spec.optional_categorical)
            cat_idx = [first_cat + i for i in range(n_cat)]
            self._models[metric] = {
                q: HistGradientBoostingRegressor(
                    loss="quantile", quantile=q, max_iter=200, learning_rate=0.05,
                    max_depth=4, categorical_features=cat_idx or None,
                    early_stopping=False, random_state=0,
                ).fit(X, y)
                for q in (LOWER_Q, MEDIAN_Q, UPPER_Q)
            }
            self._support[metric] = {
                "patients": len(patients),
                "rows": len(mrows),
                # whole days, so "day 0" is covered when the first sample was at day 0.1
                "day_min": float(math.floor(min(r.day for r in mrows))),
                "day_max": float(math.ceil(max(r.day for r in mrows))),
                "numeric": {
                    k: [float(min(v)), float(max(v))]
                    for k in (*self.spec.numeric, *self.spec.optional_numeric)
                    if (v := [r.numeric[k] for r in mrows if k in r.numeric])
                },
                "categorical": {
                    k: sorted({r.categorical[k] for r in mrows if k in r.categorical})
                    for k in (*self.spec.categorical, *self.spec.optional_categorical)
                },
            }
        return self

    def _complete(self, r: Row) -> bool:
        return all(k in r.numeric for k in self.spec.numeric) and all(
            k in r.categorical for k in self.spec.categorical
        )

    def _encode(self, p: PatientProfile, day: float) -> list[float]:
        return [
            day,
            *(p.numeric[k] for k in self.spec.numeric),
            *(p.numeric.get(k, math.nan) for k in self.spec.optional_numeric),
            *(self._category_codes[k][p.categorical[k]] for k in self.spec.categorical),
            # an unknown or missing optional category is treated as "not known"
            *(self._category_codes[k].get(p.categorical.get(k), math.nan)
              for k in self.spec.optional_categorical),
            *(float(k in p.flags) for k in self.spec.flags),
        ]

    # ------------------------------------------------------------ prediction

    def predict(self, profile: PatientProfile, metric: str, days: list[float]) -> ExpectedTrajectory:
        """Expected curve for this patient, or an abstention with the reason.

        Abstains whenever the patient is unlike the training patients:
        untrained metric, unseen procedure, or age etc. outside the trained range.
        """
        support = self._support.get(metric)
        reasons: list[str] = []
        if support is None:
            reasons.append(f"no model trained for '{metric}'")
        else:
            for k in (*self.spec.numeric, *self.spec.optional_numeric):
                if k not in profile.numeric:
                    if k in self.spec.numeric:
                        reasons.append(f"patient {k} not provided")
                    continue
                lo, hi = support["numeric"].get(k, (math.inf, -math.inf))
                if not lo <= profile.numeric[k] <= hi:
                    reasons.append(f"{k} {profile.numeric[k]:g} outside trained range {lo:g}-{hi:g}")
            for k in self.spec.categorical:
                if k not in profile.categorical:
                    reasons.append(f"patient {k} not provided")
                elif profile.categorical[k] not in support["categorical"][k]:
                    reasons.append(f"{k} '{profile.categorical[k]}' not in training data")

        spec = self.spec
        known = {*spec.numeric, *spec.optional_numeric, *spec.categorical,
                 *spec.optional_categorical, *spec.flags}
        given = {*profile.numeric, *profile.categorical, *profile.flags}
        unused = sorted(given - known)
        if support:
            unused += sorted(
                f"{k}={profile.categorical[k]}" for k in spec.optional_categorical
                if k in profile.categorical and profile.categorical[k] not in support["categorical"][k])

        usable = []
        if support and not reasons:
            usable = [d for d in days if support["day_min"] <= d <= support["day_max"]]
            if len(usable) < len(days):
                reasons.append(
                    f"days outside trained range {support['day_min']:g}-{support['day_max']:g} omitted")
            if not usable:
                reasons.append("no requested day is inside the trained range")

        points: list[ExpectedPoint] = []
        if usable:
            X = np.array([self._encode(profile, d) for d in usable])
            preds = np.sort(
                np.column_stack([self._models[metric][q].predict(X) for q in (LOWER_Q, MEDIAN_Q, UPPER_Q)]),
                axis=1,  # quantile models are fitted separately; keep lower <= median <= upper
            )
            points = [
                ExpectedPoint(day=d, lower=float(lo), median=float(md), upper=float(hi))
                for d, (lo, md, hi) in zip(usable, preds)
            ]
        return ExpectedTrajectory(
            metric=metric,
            unit=CANONICAL_UNITS.get(metric) or OPTIONAL_UNITS.get(metric),
            status="available" if points else "abstained",
            points=points,
            reasons=reasons,
            used_inputs=sorted(given & known),
            unused_inputs=unused,
            model_version=MODEL_VERSION,
            data_origin=self.data_origin,
            training_patients=support["patients"] if support else 0,
        )

    # ----------------------------------------------------------- persistence

    def manifest(self) -> dict:
        return {
            "model_version": MODEL_VERSION,
            "method": "gradient-boosted quantile regression (scikit-learn)",
            "quantiles": [LOWER_Q, MEDIAN_Q, UPPER_Q],
            "data_origin": self.data_origin,
            "training_data_sha256": self._data_hash,
            "features": {"numeric": list(self.spec.numeric),
                         "optional_numeric": list(self.spec.optional_numeric),
                         "optional_categorical": list(self.spec.optional_categorical),
                         "categorical": list(self.spec.categorical),
                         "flags": list(self.spec.flags)},
            "metrics": self._support,
        }

    def save(self, directory: str | Path) -> None:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, directory / "model.joblib")
        manifest = self.manifest() | {
            "model_file_sha256": hashlib.sha256((directory / "model.joblib").read_bytes()).hexdigest()
        }
        (directory / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))

    @staticmethod
    def load(directory: str | Path) -> "TrajectoryModel":
        """Load a model we saved ourselves; refuses a file that does not match its manifest."""
        directory = Path(directory)
        manifest = json.loads((directory / "manifest.json").read_text())
        blob = (directory / "model.joblib").read_bytes()
        if hashlib.sha256(blob).hexdigest() != manifest["model_file_sha256"]:
            raise ValueError("model file does not match its manifest")
        return joblib.load(directory / "model.joblib")


def _profile(r: Row) -> PatientProfile:
    return PatientProfile(numeric=r.numeric, categorical=r.categorical, flags=r.flags)


def _hash_rows(rows: list[Row]) -> str:
    h = hashlib.sha256()
    for r in sorted(rows, key=lambda r: (r.patient_id, r.metric, r.day, r.value)):
        h.update(repr((r.patient_id, r.metric, r.day, r.value, sorted(r.numeric.items()),
                       sorted(r.categorical.items()), sorted(r.flags))).encode())
    return h.hexdigest()
