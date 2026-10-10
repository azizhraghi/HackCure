"""The normal recovery plan: what a healthy recovery looks like, day by day."""

from datetime import date

from pydantic import BaseModel, Field, model_validator

MEASURES = ("heart_rate", "spo2", "systolic_bp", "diastolic_bp", "temperature", "pain")
# Hard physical limits, and the smallest spread a "normal range" can have: it
# has to hold most normally recovering patients, so it cannot be a sliver.
LIMITS = {"heart_rate": (25, 220), "spo2": (70, 100), "systolic_bp": (60, 250),
          "diastolic_bp": (30, 150), "temperature": (33, 42), "pain": (0, 10)}
MIN_WIDTH = {"heart_rate": 15, "systolic_bp": 20, "diastolic_bp": 12, "temperature": 0.6,
             "spo2": 3, "pain": 1.5}


class Range(BaseModel):
    low: float
    high: float

    @model_validator(mode="after")
    def _ordered(self) -> "Range":
        if self.low > self.high:
            raise ValueError("range is upside down")
        return self


class Expected(BaseModel):
    """Normal ranges on one day."""

    day: int = Field(ge=0)  # days since surgery
    heart_rate: Range  # beats/min
    spo2: Range  # %
    systolic_bp: Range  # mmHg
    diastolic_bp: Range  # mmHg
    temperature: Range  # Cel
    pain: Range  # 0-10

    @model_validator(mode="after")
    def _plausible(self) -> "Expected":
        for name in MEASURES:
            r: Range = getattr(self, name)
            lo, hi = LIMITS[name]
            if r.low < lo or r.high > hi:
                raise ValueError(
                    f"day {self.day}: {name} {r.low:g}-{r.high:g} is outside what is physically plausible")
            if r.high - r.low < MIN_WIDTH[name] - 1e-6:  # 36.8 - 36.2 is 0.5999... in floats
                raise ValueError(
                    f"day {self.day}: {name} range {r.low:g}-{r.high:g} is too narrow to be a "
                    f"normal range (needs a spread of at least {MIN_WIDTH[name]:g})")
        return self


class Checkpoint(Expected):
    """Ranges the model sets on a key day; the days in between are filled in from these."""


class DayExpectation(Expected):
    expected_signs: list[str]  # what is normal to notice that day
    patient_message: str  # how he should feel, in words for the patient


class Phase(BaseModel):
    from_day: int
    to_day: int
    description: str


class LastingSymptom(BaseModel):
    symptom: str
    typically_lasts_days: float


class TypicalCourse(BaseModel):
    """How recovery from this operation usually goes, before personalising."""

    full_recovery_typically_weeks: float
    # First day on which pain is typically no more than minimal. Before it,
    # the plan is not allowed to show pain near zero.
    noticeable_pain_until_day: int
    phases: list[Phase]
    lasting_symptoms: list[LastingSymptom]


class PersonalFactor(BaseModel):
    """One thing about this patient and how it changes the usual course."""

    factor: str
    effect: str


class Event(BaseModel):
    """A dated item from the patient's data, placed on its day: an appointment, a restriction ending."""

    day: int
    description: str


class RecoveryTrajectory(BaseModel):
    surgery: str
    typical_course: TypicalCourse
    personal_factors: list[PersonalFactor]
    assumptions: list[str]  # what was missing from the input and had to be assumed
    events: list[Event] = []
    checkpoints: list[Checkpoint]
    days: list[DayExpectation]
    summary: str
    # Corrections our code made to the model's numbers, for transparency.
    adjustments: list[str] = []
    # filled in by our code, not by the model
    language: str = ""
    generated_by: str = ""
    prompt_version: str = ""
    input_hash: str = ""

    @model_validator(mode="after")
    def _consecutive(self) -> "RecoveryTrajectory":
        if [d.day for d in self.days] != list(range(len(self.days))):
            raise ValueError("days must run 0, 1, 2, ... with none missing")
        return self

    def day(self, n: int) -> DayExpectation:
        return self.days[n]

    def today(self, surgery_date: date, on: date) -> DayExpectation | None:
        """The part of the plan for the current day; None before surgery or after the plan ends."""
        n = (on - surgery_date).days
        return self.days[n] if 0 <= n < len(self.days) else None

    def home_screen(self, surgery_date: date, on: date) -> dict | None:
        """What the patient app shows on its home screen today.

        The message telling the patient how it is normal to feel, what is
        normal to notice, and anything scheduled today. None outside the plan.
        """
        d = self.today(surgery_date, on)
        if d is None:
            return None
        return {
            "day": d.day,
            "surgery": self.surgery,
            "message": d.patient_message,
            "normal_today": d.expected_signs,
            "normal_pain": {"low": d.pain.low, "high": d.pain.high, "scale": "0-10"},
            "today": [e.description for e in self.events if e.day == d.day],
        }


def widen(name: str, low: float, high: float) -> tuple[float, float]:
    """Stretch a too-narrow range to the minimum spread, around its middle, within limits."""
    need = MIN_WIDTH[name]
    if high - low >= need - 1e-6:
        return low, high
    lo_limit, hi_limit = LIMITS[name]
    middle = (low + high) / 2
    low, high = middle - need / 2, middle + need / 2
    if low < lo_limit:
        low, high = lo_limit, lo_limit + need
    if high > hi_limit:
        low, high = hi_limit - need, hi_limit
    return round(low, 1), round(high, 1)


def interpolate(checkpoints: list[Checkpoint], last_day: int) -> list[Expected]:
    """Fill in every day between the checkpoints with a straight line."""
    step = {"temperature": 0.1, "pain": 0.5}
    out = []
    for day in range(last_day + 1):
        before = max((c for c in checkpoints if c.day <= day), key=lambda c: c.day)
        after = min((c for c in checkpoints if c.day >= day), key=lambda c: c.day)
        t = 0.0 if after.day == before.day else (day - before.day) / (after.day - before.day)
        values = {}
        for name in MEASURES:
            a, b, unit = getattr(before, name), getattr(after, name), step.get(name, 1)
            values[name] = Range(
                low=round((a.low + t * (b.low - a.low)) / unit) * unit,
                high=round((a.high + t * (b.high - a.high)) / unit) * unit,
            )
        out.append(Expected(day=day, **values))
    return out


# ------------------------------------------- structures the LLM must return

def _obj(**properties):
    return {"type": "object", "additionalProperties": False,
            "required": list(properties), "properties": properties}


_STR, _NUM, _INT = {"type": "string"}, {"type": "number"}, {"type": "integer"}
_RANGE = _obj(low=_NUM, high=_NUM)


def _list(item):
    return {"type": "array", "items": item}


# Step 1. Kept flat, with ranges as [low, high] pairs: models make bracket
# mistakes in deeply nested answers. Order matters: the model writes the usual
# course and the personal factors first, and the checkpoint numbers afterwards
# have to agree with them.
_PAIR = _list(_NUM)
COURSE_SCHEMA = _obj(
    surgery=_STR,
    full_recovery_typically_weeks=_NUM,
    noticeable_pain_until_day=_INT,
    phases=_list(_obj(from_day=_INT, to_day=_INT, description=_STR)),
    lasting_symptoms=_list(_obj(symptom=_STR, typically_lasts_days=_NUM)),
    personal_factors=_list(_obj(factor=_STR, effect=_STR)),
    assumptions=_list(_STR),
    events=_list(_obj(day=_INT, description=_STR)),
    checkpoints=_list(_obj(day=_INT, **{m: _PAIR for m in MEASURES})),
    summary=_STR,
)
# Step 2: the text for a block of days.
DAYS_SCHEMA = _obj(days=_list(_obj(day=_INT, expected_signs=_list(_STR), patient_message=_STR)))

# The same structures in compact form, as a reminder inside the prompt.
COURSE_SHAPE = (
    '{"surgery": str, "full_recovery_typically_weeks": num, "noticeable_pain_until_day": int, '
    '"phases": [{"from_day": int, "to_day": int, "description": str}], '
    '"lasting_symptoms": [{"symptom": str, "typically_lasts_days": num}], '
    '"personal_factors": [{"factor": str, "effect": str}], "assumptions": [str], '
    '"events": [{"day": int, "description": str}], "checkpoints": [{"day": int, "heart_rate": [low, high], "spo2": [low, high], '
    '"systolic_bp": [low, high], "diastolic_bp": [low, high], "temperature": [low, high], '
    '"pain": [low, high]}], "summary": str}'
)
DAYS_SHAPE = '{"days": [{"day": int, "expected_signs": [str], "patient_message": str}]}'
