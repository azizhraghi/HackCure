"""What a guided test reports: measurements and observations, never a diagnosis."""

from typing import Literal

from pydantic import BaseModel

from ..physiology.models import Quality

Side = Literal["left", "right", "both"]


class Measurement(BaseModel):
    code: str
    value: float | None
    unit: str
    side: Side | None = None


class MotorResult(BaseModel):
    test: str
    version: str
    # complete: measured as intended; limited: measured, with reservations;
    # not_interpretable: nothing reliable could be measured.
    status: Literal["complete", "limited", "not_interpretable"]
    measurements: list[Measurement]
    observations: list[str]  # plain statements of what was seen
    # True when a left/right difference or an unusual pattern is large enough that a
    # clinician should look. It is a prompt to review, not a finding of illness.
    review_suggested: bool
    quality: Quality
    limitations: list[str]

    def value(self, code: str, side: Side | None = None) -> float | None:
        return next((m.value for m in self.measurements if m.code == code and m.side == side), None)


class Change(BaseModel):
    code: str
    side: Side | None
    previous: float
    current: float
    change: float


def compare_with_previous(current: MotorResult, previous: MotorResult) -> list[Change]:
    """Change in each measurement since the patient's earlier session of the same test.

    Only sessions of the same test and version that were both fully measured
    are comparable; otherwise there is nothing to compare and the list is empty.
    """
    if (current.test, current.version) != (previous.test, previous.version):
        return []
    if "complete" not in (current.status, previous.status) or "not_interpretable" in (
            current.status, previous.status):
        return []
    out = []
    for m in current.measurements:
        before = previous.value(m.code, m.side)
        if m.value is not None and before is not None:
            out.append(Change(code=m.code, side=m.side, previous=before, current=m.value,
                              change=round(m.value - before, 3)))
    return out
