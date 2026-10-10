"""Physiology analysis: series -> `analysis.completed` payload.

Reports what was observed and how it compares with an approved reference.
It does not pick thresholds, categorise alerts or diagnose: D3 owns that.
"""

import hashlib
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta

from .models import (
    AnalysisPayload,
    ApprovedReference,
    Evidence,
    GapOut,
    LatestValue,
    MetricFinding,
    PhysiologyConfig,
    Quality,
    RecordedObservation,
    ReferenceComparison,
    Slope,
)
from .series import EXCLUDING_FLAGS, EpisodeSeries, Gap, Point, build_series
from .trends import median_and_mad, observed_coverage, theil_sen_slope_per_hour

PIPELINE_VERSION = "physiology-baseline-0.1.0"


@dataclass(frozen=True)
class AnalysisRun:
    payload: AnalysisPayload
    series: EpisodeSeries
    input_watermark: datetime | None


def analyze_physiology(
    records: list[RecordedObservation],
    config: PhysiologyConfig,
    as_of: datetime,
    window: timedelta,
) -> AnalysisRun:
    """Summarise each metric over (as_of - window, as_of].

    Deterministic: the same records, config, as_of and window always give the
    same result and the same analysis_id.
    """
    series = build_series(records, config)
    start = as_of - window

    findings: list[MetricFinding] = []
    evidence: list[Evidence] = []
    # Report every metric the protocol expects, even with no data at all, so
    # "nothing measured" is stated instead of being silently absent.
    for code in sorted(set(config.codes) | set(series.by_code)):
        s = series.by_code.get(code)
        in_window = [p for p in (s.points if s else ()) if start < p.occurred_at <= as_of]
        gaps = [g for g in (s.gaps if s else ()) if g.end > start and g.start <= as_of]
        finding, ev = _summarise(code, s.unit if s else None, in_window, gaps, config, start, as_of)
        findings.append(finding)
        evidence.extend(ev)

    summarized = [f for f in findings if f.state == "summarized"]
    if findings and len(summarized) == len(findings):
        status = "complete"
    elif summarized:
        status = "limited"
    else:
        status = "abstained"

    reasons = sorted({f"{f.code}:{f.state}" for f in findings if f.state != "summarized"})
    limitations = ["Descriptive trend summary only; not a clinical assessment."]
    if not findings:
        limitations.append("No physiological observations and no expected metrics configured.")
    if config.protocol_version is None:
        limitations.append("No active protocol version bound; no approved references applied.")

    payload = AnalysisPayload(
        analysis_id=_analysis_id(series, config, as_of, window),
        status=status,
        observations=findings,
        quality=Quality(
            status={"complete": "usable", "limited": "limited", "abstained": "unusable"}[status],
            reasons=reasons,
            usable_for=["clinician_review"] if evidence else [],
        ),
        evidence=evidence,
        limitations=limitations,
        model_version=PIPELINE_VERSION,
        created_at=as_of,
    )
    return AnalysisRun(payload=payload, series=series, input_watermark=series.input_watermark)


def _summarise(
    code: str,
    unit: str | None,
    points: list[Point],
    gaps: list[Gap],
    config: PhysiologyConfig,
    start: datetime,
    end: datetime,
) -> tuple[MetricFinding, list[Evidence]]:
    cc = config.for_code(code)
    usable = [p for p in points if p.usable]
    times = [p.occurred_at for p in usable]
    values = [p.value for p in usable]
    limitations: list[str] = []

    excluded = Counter(
        f for p in points if not p.usable for f in p.flags if f in EXCLUDING_FLAGS
    )
    flag_counts = Counter(f for p in points for f in p.flags)

    latest = usable[-1] if usable else None
    since_latest = (end - latest.occurred_at).total_seconds() if latest else None
    all_gaps = list(gaps)
    if latest and cc.max_gap is not None and end - latest.occurred_at > cc.max_gap:
        all_gaps.append(Gap(latest.occurred_at, end))
        limitations.append("Latest measurement is older than the expected interval.")

    median = mad = None
    slope = None
    if not usable:
        state = "no_recent_measurement"
        limitations.append("No usable measurement in the window; this is not a normal result.")
    elif len(usable) < cc.min_samples:
        state = "insufficient_samples"
        limitations.append(
            f"{len(usable)} usable sample(s); {cc.min_samples} needed for a trend."
        )
    else:
        state = "summarized"
        median, mad = median_and_mad(values)
        value, subsampled = theil_sen_slope_per_hour(times, values)
        if value is None:
            limitations.append("All samples share one timestamp; no slope.")
        else:
            slope = Slope(value=value, unit=f"{unit}/h", subsampled=subsampled)

    if cc.max_gap is None:
        limitations.append("No expected interval configured; gaps and coverage not assessed.")
    if code == "hr":
        limitations.append("Activity context is not recorded; values may not be comparable.")
    if flag_counts.get("source_changed"):
        limitations.append("Measurement device or method changed within the window.")

    evidence = [
        Evidence(
            evidence_id=f"evref_{p.observation_id}_{code}",
            resource_id=p.observation_id,
            resource_version="1",
            observed_at=p.occurred_at,
            locator=f"metrics[code={code}]",
        )
        for p in points
    ]

    finding = MetricFinding(
        code=code,
        unit=unit,
        state=state,
        window_start=start,
        window_end=end,
        sample_count=len(points),
        usable_count=len(usable),
        excluded=dict(excluded),
        flag_counts=dict(flag_counts),
        latest=LatestValue(
            value=latest.value,
            observed_at=latest.occurred_at,
            observation_id=latest.observation_id,
        )
        if latest
        else None,
        seconds_since_latest=since_latest,
        median=median,
        mad=mad,
        slope=slope,
        min_samples=cc.min_samples,
        span_seconds=(times[-1] - times[0]).total_seconds() if usable else None,
        coverage=observed_coverage(times, start, end, cc.max_gap),
        gaps=[GapOut(start=g.start, end=g.end, seconds=g.seconds) for g in all_gaps],
        reference=_compare(cc.reference, latest.value if latest else None, median),
        evidence_ids=[e.evidence_id for e in evidence],
        limitations=limitations,
    )
    return finding, evidence


def _compare(
    ref: ApprovedReference | None, latest: float | None, median: float | None
) -> ReferenceComparison | None:
    if ref is None:
        return None

    def side(v: float | None):
        if v is None or (ref.lower is None and ref.upper is None):
            return None
        if ref.lower is not None and v < ref.lower:
            return "below"
        if ref.upper is not None and v > ref.upper:
            return "above"
        return "within"

    return ReferenceComparison(
        reference_id=ref.reference_id,
        reference_version=ref.version,
        latest=side(latest),
        window_median=side(median),
        change_from_baseline=(
            median - ref.baseline if median is not None and ref.baseline is not None else None
        ),
    )


def _analysis_id(
    series: EpisodeSeries, config: PhysiologyConfig, as_of: datetime, window: timedelta
) -> str:
    h = hashlib.sha256()
    h.update(PIPELINE_VERSION.encode())
    h.update(repr((config, as_of.isoformat(), window.total_seconds())).encode())
    for code in sorted(series.by_code):
        for p in series.by_code[code].points:
            h.update(f"{p.event_id}|{code}|{p.value}|{p.flags}".encode())
    return f"an_{h.hexdigest()[:16]}"
