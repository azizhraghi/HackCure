"""Demo clock: wall-clock time plus an offset that the demo (and tests) can advance.

All timestamps are naive local datetimes so plan schedules ("08:00") map directly.
"""

from datetime import datetime, timedelta

_offset = timedelta(0)
_frozen: datetime | None = None


def now() -> datetime:
    base = _frozen if _frozen is not None else datetime.now()
    return (base + _offset).replace(microsecond=(base + _offset).microsecond // 1000 * 1000)


def advance(seconds: float) -> datetime:
    global _offset
    _offset += timedelta(seconds=seconds)
    return now()


def freeze(at: datetime | None = None) -> None:
    """Stop the clock (tests). `advance` still moves it."""
    global _frozen, _offset
    _frozen = at or datetime.now()
    _offset = timedelta(0)


def reset() -> None:
    global _frozen, _offset
    _frozen = None
    _offset = timedelta(0)
