"""Compare forecasting methods on past data before enabling one."""

import numpy as np

from .methods import Forecaster


def backtest(
    forecasters: dict[str, Forecaster], hourly_series: list[np.ndarray],
    horizons: tuple[int, ...] = (6, 12, 24), min_history: int = 48, stride: int = 6,
) -> dict[str, dict[int, dict[str, float]]]:
    """Replay each series: forecast from many past moments, compare with what happened.

    Returns per method and horizon: n, mae (average miss) and band_coverage
    (share of real values inside the band; target 0.8).
    """
    steps = max(horizons)
    out: dict[str, dict[int, dict[str, float]]] = {}
    for name, f in forecasters.items():
        errors = {h: [] for h in horizons}
        inside = {h: [] for h in horizons}
        for series in hourly_series:
            for end in range(min_history, len(series) - steps + 1, stride):
                history = series[:end]
                if np.isnan(history[-24:]).mean() > 0.5:
                    continue
                pred = f.predict(history, steps)
                for h in horizons:
                    actual = series[end + h - 1]
                    if np.isnan(actual):
                        continue
                    lower, point, upper = pred[h - 1]
                    errors[h].append(abs(actual - point))
                    if not np.isnan(lower):
                        inside[h].append(float(lower <= actual <= upper))
        out[name] = {
            h: {"n": len(errors[h]),
                "mae": float(np.mean(errors[h])) if errors[h] else float("nan"),
                "band_coverage": float(np.mean(inside[h])) if inside[h] else float("nan")}
            for h in horizons
        }
    return out
