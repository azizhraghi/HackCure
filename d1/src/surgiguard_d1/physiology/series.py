"""Turn raw observation records into per-metric time series.

Nothing is deleted or interpolated here. Every point keeps its native
timestamp and gets flags describing why it may be doubtful; only a few flags
exclude a point from trend statistics, and those points stay in the series.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from .models import PhysiologyConfig, RecordedObservation

# Flags that keep a point out of the trend statistics (it is still displayed).
EXCLUDING_FLAGS = frozenset({"duplicate", "zero_value", "device_reported_unusable"})


@dataclass(frozen=True)
class Point:
    code: str
    value: float
    unit: str
    occurred_at: datetime
    received_at: datetime
    observation_id: str
    event_id: str
    method: str
    device_id: str | None
    reporter_id: str | None
    flags: tuple[str, ...] = ()

    @property
    def usable(self) -> bool:
        return not (EXCLUDING_FLAGS & set(self.flags))


@dataclass(frozen=True)
class Gap:
    start: datetime
    end: datetime

    @property
    def seconds(self) -> float:
        return (self.end - self.start).total_seconds()


@dataclass(frozen=True)
class Correction:
    superseded_id: str
    superseding_id: str
    received_at: datetime


@dataclass(frozen=True)
class Series:
    code: str
    unit: str
    points: tuple[Point, ...]  # sorted by occurred_at, includes flagged points
    gaps: tuple[Gap, ...]


@dataclass(frozen=True)
class EpisodeSeries:
    by_code: dict[str, Series]
    corrections: tuple[Correction, ...]
    input_watermark: datetime | None  # latest received_at that was considered


def find_gaps(times: list[datetime], max_gap: timedelta | None) -> tuple[Gap, ...]:
    if max_gap is None:
        return ()
    return tuple(Gap(a, b) for a, b in zip(times, times[1:]) if b - a > max_gap)


def build_series(
    records: list[RecordedObservation], config: PhysiologyConfig
) -> EpisodeSeries:
    # At-least-once delivery: the same event may arrive several times.
    unique: dict[str, RecordedObservation] = {}
    for r in records:
        if r.payload.kind == "physiology":
            unique.setdefault(r.event_id, r)
    recs = sorted(unique.values(), key=lambda r: (r.received_at, r.event_id))
    known_ids = {r.payload.observation_id for r in recs}

    # Corrections: the superseded record stays stored, but only the newest
    # version feeds the series. If two records correct the same one, the
    # later-received wins.
    corrections = tuple(
        Correction(r.payload.supersedes_id, r.payload.observation_id, r.received_at)
        for r in recs
        if r.payload.supersedes_id in known_ids
    )
    superseded = {c.superseded_id for c in corrections}
    winner: dict[str, str] = {c.superseded_id: c.superseding_id for c in corrections}
    superseded |= {
        c.superseding_id for c in corrections if winner[c.superseded_id] != c.superseding_id
    }

    raw: dict[str, list[Point]] = {}
    for r in recs:
        p = r.payload
        if p.observation_id in superseded:
            continue
        base: list[str] = []
        if p.supersedes_id is not None:
            base.append("correction" if p.supersedes_id in known_ids else "supersedes_unknown")
        if r.occurred_at - r.received_at > config.clock_skew_tolerance:
            base.append("clock_skew_future")
        if p.quality.status == "unusable":
            base.append("device_reported_unusable")
        elif p.quality.status == "limited":
            base.append("device_reported_limited")
        if "detached" in p.quality.reasons:
            base.append("device_detached")
        if p.source.method == "manual":
            base.append("manual_entry")
        codes = {m.code: m.value for m in p.metrics}
        if "sbp" in codes and "dbp" in codes and codes["sbp"] <= codes["dbp"]:
            base.append("sbp_not_above_dbp")

        for m in p.metrics:
            flags = list(base)
            cc = config.for_code(m.code)
            if m.value == 0:
                # Contract: a missing reading is an absent record, never zero.
                flags.append("zero_value")
            elif (cc.plausible_low is not None and m.value < cc.plausible_low) or (
                cc.plausible_high is not None and m.value > cc.plausible_high
            ):
                flags.append("outside_plausibility_config")
            raw.setdefault(m.code, []).append(
                Point(
                    code=m.code,
                    value=m.value,
                    unit=m.unit,
                    occurred_at=r.occurred_at,
                    received_at=r.received_at,
                    observation_id=p.observation_id,
                    event_id=r.event_id,
                    method=p.source.method,
                    device_id=p.source.device_id,
                    reporter_id=p.source.reporter_id,
                    flags=tuple(flags),
                )
            )

    by_code: dict[str, Series] = {}
    for code, pts in raw.items():
        pts.sort(key=lambda p: (p.occurred_at, p.received_at, p.observation_id))
        out: list[Point] = []
        seen: set[tuple] = set()
        earliest_later_receipt = _suffix_min([p.received_at for p in pts])
        prev: Point | None = None
        for i, p in enumerate(pts):
            flags = list(p.flags)
            key = (p.occurred_at, p.value, p.device_id, p.reporter_id)
            if key in seen:
                flags.append("duplicate")
            seen.add(key)
            if i + 1 < len(pts) and p.received_at > earliest_later_receipt[i + 1]:
                flags.append("late_arrival")
            if prev is not None and (prev.method, prev.device_id) != (p.method, p.device_id):
                flags.append("source_changed")
            p = Point(**{**p.__dict__, "flags": tuple(flags)})
            out.append(p)
            if "duplicate" not in flags:
                prev = p
        # A zero or unusable reading does not end a gap in real observation.
        times = [p.occurred_at for p in out if p.usable]
        by_code[code] = Series(
            code=code,
            unit=out[0].unit,
            points=tuple(out),
            gaps=find_gaps(times, config.for_code(code).max_gap),
        )

    return EpisodeSeries(
        by_code=by_code,
        corrections=corrections,
        input_watermark=max((r.received_at for r in recs), default=None),
    )


def _suffix_min(values: list[datetime]) -> list[datetime]:
    out = list(values)
    for i in range(len(out) - 2, -1, -1):
        out[i] = min(out[i], out[i + 1])
    return out
