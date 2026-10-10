"""Episode timeline: where the patient is relative to surgery and discharge."""

from datetime import datetime
from zoneinfo import ZoneInfo

from .models import ApprovedMilestone

POD_CONVENTION = "calendar days in the patient's timezone; day of surgery = 0"


def calendar_days_between(start: datetime, end: datetime, tz: str) -> int:
    zone = ZoneInfo(tz)
    return (end.astimezone(zone).date() - start.astimezone(zone).date()).days


def milestone_timing(m: ApprovedMilestone, pod: int) -> str:
    """Calendar position only. Says nothing about whether it was reached."""
    if m.expected_from_day is None and m.expected_to_day is None:
        return "no_timing"
    if m.expected_from_day is not None and pod < m.expected_from_day:
        return "before_window"
    if m.expected_to_day is not None and pod > m.expected_to_day:
        return "after_window"
    return "in_window"
