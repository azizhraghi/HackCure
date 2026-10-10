"""Transparent, time-aware trend statistics. No learned models."""

from datetime import datetime, timedelta

import numpy as np

# Theil-Sen looks at every pair of points; above this we thin the series evenly.
MAX_SLOPE_POINTS = 1000


def median_and_mad(values: list[float]) -> tuple[float, float]:
    """Median and (unscaled) median absolute deviation."""
    v = np.asarray(values, dtype=float)
    med = float(np.median(v))
    return med, float(np.median(np.abs(v - med)))


def theil_sen_slope_per_hour(
    times: list[datetime], values: list[float]
) -> tuple[float | None, bool]:
    """Median of all pairwise slopes, in units per hour.

    Uses real elapsed time, so irregular sampling is handled without
    resampling. Returns (slope, subsampled). Slope is None when all samples
    share one timestamp.
    """
    t = np.array([(x - times[0]).total_seconds() / 3600.0 for x in times])
    v = np.asarray(values, dtype=float)
    subsampled = len(v) > MAX_SLOPE_POINTS
    if subsampled:
        idx = np.unique(np.linspace(0, len(v) - 1, MAX_SLOPE_POINTS).round().astype(int))
        t, v = t[idx], v[idx]
    i, j = np.triu_indices(len(v), k=1)
    dt = t[j] - t[i]
    ok = dt > 0
    if not ok.any():
        return None, subsampled
    return float(np.median((v[j] - v[i])[ok] / dt[ok])), subsampled


def observed_coverage(
    times: list[datetime], start: datetime, end: datetime, max_gap: timedelta | None
) -> float | None:
    """Fraction of the window spanned by samples no further apart than max_gap.

    None when no cadence is configured: without one, "covered" is undefined.
    """
    if max_gap is None or end <= start:
        return None
    covered = sum(
        (b - a).total_seconds() for a, b in zip(times, times[1:]) if b - a <= max_gap
    )
    return covered / (end - start).total_seconds()


def rolling_median(
    times: list[datetime], values: list[float], window: timedelta
) -> list[tuple[datetime, float, int]]:
    """Trailing-window median at each native timestamp: (time, median, n).

    A display aid. The result is a summary, never shown as a measurement.
    """
    out = []
    lo = 0
    for hi, t in enumerate(times):
        while times[lo] <= t - window:
            lo += 1
        out.append((t, float(np.median(values[lo : hi + 1])), hi + 1 - lo))
    return out
