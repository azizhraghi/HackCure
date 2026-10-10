"""Forecast output, matching RecoveryForecastV1 in the Developer 1 spec."""

from typing import Literal

from pydantic import AwareDatetime, BaseModel, Field, model_validator


class Interval(BaseModel):
    lower: float
    upper: float
    coverage: float = Field(gt=0, lt=1)


class Forecast(BaseModel):
    forecast_id: str
    target_code: str
    unit: str
    issued_at: AwareDatetime
    horizon_hours: float = Field(gt=0)
    status: Literal["available", "abstained"]
    point: float | None
    interval: Interval | None
    method_version: str | None
    evidence_ids: list[str]
    limitations: list[str]

    @model_validator(mode="after")
    def _check(self) -> "Forecast":
        if self.status == "abstained":
            if self.point is not None or self.interval is not None:
                raise ValueError("an abstained forecast carries no numbers")
            if not self.limitations:
                raise ValueError("an abstained forecast must say why")
        else:
            if self.point is None or self.method_version is None:
                raise ValueError("an available forecast needs a point and a method")
            if self.interval and not self.interval.lower <= self.interval.upper:
                raise ValueError("interval bounds are out of order")
        return self
