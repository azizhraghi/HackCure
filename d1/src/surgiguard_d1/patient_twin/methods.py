"""Forecasting methods, simplest first.

Each takes the patient's own recent readings as hourly values (NaN where
nothing was measured) and returns, per hour ahead, a point and an 80% band.
A more complex method is only worth enabling if a backtest shows it beats
the simpler ones (see backtest.py).
"""

from pathlib import Path
from typing import Protocol

import numpy as np

COVERAGE = 0.8
_LOW, _HIGH = 0.1, 0.9


class Forecaster(Protocol):
    version: str
    interval_note: str

    def predict(self, hourly: np.ndarray, steps: int) -> np.ndarray:
        """Return an array of shape (steps, 3): lower, point, upper."""


def _band_from_past_errors(hourly: np.ndarray, predict_one, steps: int) -> np.ndarray | None:
    """Empirical band: how wrong would this method have been, h hours ahead, earlier today?"""
    out = np.full((steps, 2), np.nan)
    for h in range(1, steps + 1):
        errors = []
        for end in range(6, len(hourly) - h + 1):
            actual = hourly[end + h - 1]
            if np.isnan(actual) or np.isnan(hourly[:end]).all():
                continue
            errors.append(actual - predict_one(hourly[:end], h))
        if len(errors) < 8:
            return None
        out[h - 1] = np.quantile(errors, [_LOW, _HIGH])
    return out


def _with_band(hourly, points, predict_one, steps):
    band = _band_from_past_errors(hourly, predict_one, steps)
    if band is None:
        return np.column_stack([np.full(steps, np.nan), points, np.full(steps, np.nan)])
    return np.column_stack([points + band[:, 0], points, points + band[:, 1]])


class PersistenceForecaster:
    """Tomorrow looks like the latest reading. The baseline everything must beat."""

    version = "persistence-0.1.0"
    interval_note = "Band from this patient's own recent hour-to-hour changes."

    @staticmethod
    def _one(history: np.ndarray, h: int) -> float:
        return float(history[~np.isnan(history)][-1])

    def predict(self, hourly: np.ndarray, steps: int) -> np.ndarray:
        points = np.full(steps, self._one(hourly, 1))
        return _with_band(hourly, points, self._one, steps)


class TrendForecaster:
    """Continue the recent robust (Theil-Sen) trend of the last 24 hours."""

    version = "theil-sen-trend-0.1.0"
    interval_note = "Band from how far this trend line missed earlier in the same series."
    window = 24

    def _one(self, history: np.ndarray, h: int) -> float:
        recent = history[-self.window:]
        t = np.flatnonzero(~np.isnan(recent)).astype(float)
        v = recent[~np.isnan(recent)]
        if len(v) < 3:
            return float(v[-1])
        i, j = np.triu_indices(len(v), k=1)
        slope = float(np.median((v[j] - v[i]) / (t[j] - t[i])))
        intercept = float(np.median(v - slope * t))
        return intercept + slope * (len(recent) - 1 + h)

    def predict(self, hourly: np.ndarray, steps: int) -> np.ndarray:
        points = np.array([self._one(hourly, h) for h in range(1, steps + 1)])
        return _with_band(hourly, points, self._one, steps)


class ChronosForecaster:
    """Pretrained time-series foundation model (Amazon Chronos-Bolt), used as-is.

    It was pretrained on a large mix of public time series from many domains,
    not on medical data, and has not been fine-tuned by us.
    """

    interval_note = ("Band is the pretrained model's own 10th-90th percentile; it has not been "
                     "checked against postoperative data.")

    def __init__(self, model_dir: str | Path) -> None:
        self.model_dir = Path(model_dir)
        self.version = f"{self.model_dir.name}-zero-shot"
        self._pipeline = None

    def predict(self, hourly: np.ndarray, steps: int) -> np.ndarray:
        import torch
        from chronos import BaseChronosPipeline

        if self._pipeline is None:
            self._pipeline = BaseChronosPipeline.from_pretrained(str(self.model_dir), device_map="cpu")
        quantiles, _ = self._pipeline.predict_quantiles(
            inputs=torch.tensor(hourly, dtype=torch.float32),
            prediction_length=steps,
            quantile_levels=[_LOW, 0.5, _HIGH],
        )
        return quantiles[0, :steps].numpy().astype(float)
