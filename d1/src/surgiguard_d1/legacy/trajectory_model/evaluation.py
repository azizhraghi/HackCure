"""Check a trained model on patients it has never seen."""

from collections import defaultdict

import numpy as np

from .dataset import Row
from .model import PatientProfile, TrajectoryModel


def evaluate(model: TrajectoryModel, train: list[Row], test: list[Row]) -> dict[str, dict]:
    """Per metric: error of the predicted typical value, how often real values
    fall inside the predicted band, and the error of a naive baseline that
    ignores the patient's background (the average patient on that day).

    The model is only worth using where its error beats the baseline.
    """
    by_day: dict[tuple[str, int], list[float]] = defaultdict(list)
    overall: dict[str, list[float]] = defaultdict(list)
    for r in train:
        by_day[(r.metric, round(r.day))].append(r.value)
        overall[r.metric].append(r.value)

    grouped: dict[tuple[str, str], list[Row]] = defaultdict(list)
    for r in test:
        grouped[(r.patient_id, r.metric)].append(r)

    stats: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    abstained: dict[str, int] = defaultdict(int)
    for (_, metric), rows in grouped.items():
        first = rows[0]
        t = model.predict(
            PatientProfile(first.numeric, first.categorical, first.flags), metric, [r.day for r in rows])
        predicted = {p.day: p for p in t.points}
        for r in rows:
            p = predicted.get(r.day)
            if p is None:
                abstained[metric] += 1
                continue
            naive = by_day.get((metric, round(r.day))) or overall[metric]
            s = stats[metric]
            s["error"].append(abs(r.value - p.median))
            s["baseline_error"].append(abs(r.value - float(np.median(naive))))
            s["inside"].append(float(p.lower <= r.value <= p.upper))
            s["width"].append(p.upper - p.lower)

    return {
        metric: {
            "n": len(s["error"]),
            "abstained": abstained[metric],
            "mae": float(np.mean(s["error"])),
            "baseline_mae": float(np.mean(s["baseline_error"])),
            "band_coverage": float(np.mean(s["inside"])),
            "band_width": float(np.mean(s["width"])),
        }
        for metric, s in sorted(stats.items())
    } | {m: {"n": 0, "abstained": n} for m, n in abstained.items() if m not in stats}
