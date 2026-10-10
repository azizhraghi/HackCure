"""Developer 2's JSON  ->  the patient's normal recovery plan.

Developer 2 has already read the medical dossier. This takes their result,
removes what identifies the patient, and asks an LLM what an uncomplicated
recovery looks like for this person: vital signs, pain, what is normal to
notice, and how he should feel, for each day.

The plan is estimated once and saved. It is built in two steps so that the
days stay faithful to the operation and the person:
  1. the usual course of this operation, how this patient's own factors
     change it, and the normal ranges on a few checkpoint days;
  2. our code fills in the ranges for every day between the checkpoints,
     and the LLM writes each day's text against step 1 and those numbers.
Every answer must fit a fixed structure and pass plausibility checks.
"""

import hashlib
import json
import os
import time
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, TypeAdapter

from .schema import (
    COURSE_SCHEMA,
    COURSE_SHAPE,
    DAYS_SCHEMA,
    DAYS_SHAPE,
    MEASURES,
    Checkpoint,
    DayExpectation,
    Event,
    Expected,
    PersonalFactor,
    RecoveryTrajectory,
    TypicalCourse,
    interpolate,
    widen,
)

PROMPT_VERSION = "recovery-v10"
DEFAULT_CACHE = Path(".cache/recovery")
GROQ_MODEL = "openai/gpt-oss-120b"  # override with the GROQ_MODEL environment variable
ANTHROPIC_MODEL = "claude-opus-5-5"
DAYS_PER_BLOCK = 14

# An "ask" function sends instructions and a request to an LLM and returns the
# raw JSON text of its answer. `part` is "course" or "days" and tells it which
# structure the answer must have.
Ask = Callable[[str, str, str], str]

# Never sent to the LLM. Date of birth is replaced by age.
_IDENTIFYING = {"patient_lastname", "patient_firstname", "patient_dob", "prescriber",
                "prescription_date"}
# Extraction bookkeeping that says nothing about the patient.
_BOOKKEEPING = {"document_type", "confidence", "confidence_notes", "global_confidence",
                "extraction_warnings"}

_INTRO = """\
You describe what a normal, uncomplicated recovery looks like after surgery for one specific \
patient. Your work drives a home-monitoring app: the plan is produced once, after the \
operation, and split into days. Each day the patient sees that day's part and their real \
readings and symptoms are compared with it. If the picture is too rosy, a patient recovering \
normally will look as if something is wrong. If it is generic, it is useless. Be accurate for \
this operation and this person."""

SYSTEM_COURSE = _INTRO + """

In this step you set the foundations the daily plan will be built from. You receive the \
patient's data as JSON. Fill the fields in this order; each constrains the next.

`surgery`: the operation as you understood it.

The usual course: how recovery from this operation goes for adults, before considering this \
patient. Give the weeks until full recovery is typical (`full_recovery_typically_weeks`), the \
last day on which pain is still typically noticeable (`noticeable_pain_until_day`), the \
`phases` with day ranges, and the `lasting_symptoms` with how many days each typically lasts. Operations differ enormously: a \
keyhole procedure may be largely over in two weeks, while a joint replacement or open \
abdominal, chest or heart surgery takes many months, with swelling, stiffness, tiredness and \
real pain lasting well past the first weeks. Give honest durations; they are used to check \
the rest of the plan, and to tell the patient each day what is still normal.

`personal_factors`: one entry for each thing known about this patient, with its concrete \
effect on the usual course: age, every medication (class, dose, duration: pain relief shapes \
expected pain and when it may rise as a course ends, a drug that slows the heart lowers \
expected heart rate, an anticoagulant makes bruising normal), allergies, restrictions, the \
follow-up plan, the instructions.

`assumptions`: what you needed and did not get (sex, weight, history, usual blood pressure) \
and what you assumed.

`events`: every dated item in the patient's data, placed on its day number counted from the \
day of surgery (day 0): each appointment and the end of each restriction. Work the day out \
carefully: "J+14" is day 14, "6 weeks after the operation" is day 42. Describe each in a few \
words. Leave out anything that falls after the last day of the plan.

`checkpoints`: for each checkpoint day you are asked for, the normal range of heart rate \
(beats/min), SpO2 (%), systolic and diastolic pressure (mmHg), temperature (Celsius) and pain \
(0-10), each as a [low, high] pair. The days in between will be filled in by straight lines, so these numbers are the \
whole shape of the plan. They must follow from the fields above: if you said a painful \
symptom lasts 60 days, pain on day 28 cannot be near zero. Each range is where most patients \
like this one fall when recovery goes well, so it must hold ordinary variation between people: \
about 20 beats/min for heart rate, 25 mmHg systolic, 15 diastolic, 1 degree, 4 points of SpO2, \
and 2 to 3 points of pain, since people differ a lot in pain. Ranges shift as the body settles \
but do not shrink towards one value, and late on they sit at what is ordinary for this age, \
not below. Heart rate and blood pressure are highest early, from pain and stress, and settle \
towards the patient's usual level; they do not climb as recovery goes on unless one of the \
personal factors explains it. Until `noticeable_pain_until_day`, the top of the pain range \
stays at 3 or more.

`summary`: the overall course for this patient in two or three sentences, addressed to them.

Write all text in the language requested."""

SYSTEM_DAYS = _INTRO + """

The foundations are already set: you receive the patient's data, the usual course of the \
operation, how this patient's own factors change it, and for each day the normal ranges \
already fixed together with the facts that hold that day: which lingering symptoms are still \
expected, which medication courses are running or have finished, and which appointments or \
other events fall today or in the next few days. In this step you write the text for a block of consecutive days (day 0 is the day \
of surgery). For each day give two to four short phrases for what is normal to notice, and a \
one or two sentence message telling the patient how they should expect to feel.

The text must agree with that day's numbers and facts. A symptom listed as still expected \
is never described as gone, absent or "none": it is normal for it to be there, even if \
lighter. A medication whose course has finished is not credited with anything on that day. A \
day whose pain range reaches 5 is not described as nearly painless. Mention an event on the day the facts place it, and as \
coming up only with the number of days the facts give; do not work out dates yourself. Recovery has plateaus and days when more activity or the \
end of a medication course makes things temporarily harder; say so where it applies.

Messages are read at home by someone possibly anxious. Write plainly and warmly, in the second \
person, without jargon, specific to this operation, and varied from day to day. Use words, \
not figures: no ranges or scores in the phrases or the message. Do not diagnose, and do not tell the patient to start, stop or change a \
medication; that is for their care team.

Write all text in the language requested."""


class _Course(BaseModel):
    surgery: str
    typical_course: TypicalCourse
    personal_factors: list[PersonalFactor]
    assumptions: list[str]
    events: list[Event] = []
    checkpoints: list[Checkpoint]
    summary: str
    adjustments: list[str] = []


class _DayText(BaseModel):
    day: int
    expected_signs: list[str]
    patient_message: str


_TEXTS = TypeAdapter(dict[str, list[_DayText]])


def checkpoint_days(last_day: int) -> list[int]:
    """Dense early, when things change fast, then every two weeks; always ends on the last day."""
    early = [d for d in (0, 1, 3, 7, 14, 21, 28) if d < last_day]
    return early + list(range(42, last_day, 14)) + [last_day]

# ------------------------------------------------------------ the input


def deidentify(document: dict[str, Any], on: date | None = None) -> dict[str, Any]:
    """Developer 2's extraction without names, prescriber or dates; age instead of birth date.

    Every medical fact is passed through as Developer 2 wrote it. Only empty
    values and extraction bookkeeping (confidence scores) are dropped.
    """
    x = document.get("extraction", document)
    out = _prune({k: v for k, v in x.items() if k not in _IDENTIFYING})
    born, ref = _date(x.get("patient_dob")), on or _date(x.get("prescription_date"))
    if born and ref:
        out["age"] = ref.year - born.year - ((ref.month, ref.day) < (born.month, born.day))
    return out


def _prune(value: Any) -> Any:
    if isinstance(value, dict):
        kept = {k: _prune(v) for k, v in value.items() if k not in _BOOKKEEPING}
        return {k: v for k, v in kept.items() if v not in (None, "", [], {})}
    if isinstance(value, list):
        return [_prune(v) for v in value]
    return value


def _date(text: str | None) -> date | None:
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text or "", fmt).date()
        except ValueError:
            continue
    return None


# ------------------------------------------------------------- the LLMs


def ask_groq(model: str, max_waits: int = 10) -> Ask:
    shapes = {"course": COURSE_SHAPE, "days": DAYS_SHAPE}
    schemas = {"course": COURSE_SCHEMA, "days": DAYS_SCHEMA}

    def ask(system: str, request: str, part: str) -> str:
        import groq

        client = groq.Groq(max_retries=0)
        for _ in range(max_waits):
            try:
                response = client.chat.completions.create(
                    model=model,
                    temperature=0,
                    max_completion_tokens=5000,
                    # The provider enforces the structure; the shape in the prompt is a reminder.
                    response_format={"type": "json_schema", "json_schema": {
                        "name": part, "strict": True, "schema": schemas[part]}},
                    messages=[
                        {"role": "system", "content": (
                            f"{system}\n\nAnswer with a single JSON object, starting with "
                            "`{` and never wrapped in a list, of exactly this shape:\n"
                            f"{shapes[part]}")},
                        {"role": "user", "content": f"{request}\n\nRespond with the JSON "
                                                    "object only, beginning with `{`."},
                    ],
                )
            except groq.RateLimitError as limited:
                # The free tier allows a few thousand tokens a minute; wait for the window.
                time.sleep(min(90.0, float(limited.response.headers.get("retry-after", 20)) + 1))
                continue
            except groq.BadRequestError as bad:
                body = getattr(bad, "body", None)
                error = body.get("error", body) if isinstance(body, dict) else {}
                rescued = _unwrap(error.get("failed_generation"))
                if rescued is not None:
                    return rescued
                reason = str(body or bad)
                if "json_validate_failed" in reason or "does not match the expected schema" in reason:
                    detail = reason.split("Error:")[-1].split("'failed_generation'")[0][:300]
                    raise ValueError(
                        f"the answer was not a valid JSON object of the required shape ({detail.strip()})"
                    ) from bad
                raise
            choice = response.choices[0]
            if choice.finish_reason == "length":
                raise ValueError("the answer was cut off; write more concisely")
            return choice.message.content
        raise RuntimeError("still rate-limited after waiting; try again in a few minutes")

    return ask


def _unwrap(text: Any) -> str | None:
    """Some models wrap the right object in a one-item list. Take it out; leave anything else."""
    try:
        value = json.loads(text)
    except (TypeError, ValueError):
        return None
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], dict):
        return json.dumps(value[0], ensure_ascii=False)
    return None


def ask_anthropic(model: str) -> Ask:
    schemas = {"course": COURSE_SCHEMA, "days": DAYS_SCHEMA}

    def ask(system: str, request: str, part: str) -> str:
        import anthropic

        # Streamed because answers are long; a refused request is retried on a fallback model.
        with anthropic.Anthropic().beta.messages.stream(
            model=model,
            max_tokens=32000,
            system=system,
            messages=[{"role": "user", "content": request}],
            output_config={"effort": "medium",
                           "format": {"type": "json_schema", "schema": schemas[part]}},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        ) as stream:
            message = stream.get_final_message()
        if message.stop_reason == "refusal":
            raise RuntimeError("the model declined to produce a plan for this input")
        if message.stop_reason == "max_tokens":
            raise ValueError("the answer was cut off; write more concisely")
        return next(b.text for b in message.content if b.type == "text")

    return ask


def default_llm() -> tuple[str, Ask]:
    """Pick the LLM from whichever API key is set. Returns (name, ask function)."""
    if os.environ.get("GROQ_API_KEY"):
        model = os.environ.get("GROQ_MODEL", GROQ_MODEL)
        return f"groq/{model}", ask_groq(model)
    if os.environ.get("ANTHROPIC_API_KEY"):
        return f"anthropic/{ANTHROPIC_MODEL}", ask_anthropic(ANTHROPIC_MODEL)
    raise RuntimeError("no LLM key found: set GROQ_API_KEY (or ANTHROPIC_API_KEY)")


# ------------------------------------------------------------- the plan


def predict_normal_trajectory(
    document: dict[str, Any],
    days: int = 42,
    language: str = "French",
    llm: tuple[str, Ask] | None = None,
    cache_dir: str | Path | None = DEFAULT_CACHE,
    progress: Callable[[str], None] = lambda _: None,
) -> RecoveryTrajectory:
    """The normal recovery plan for the patient in Developer 2's JSON.

    Estimated once for the whole recovery and split into days; `days` is the
    last postoperative day to cover. The first call for a patient asks the
    LLM; later calls with the same input read the saved plan.
    """
    name, ask = llm or default_llm()
    patient = deidentify(document)
    key = hashlib.sha256(json.dumps(
        [patient, days, language, name, PROMPT_VERSION], sort_keys=True, ensure_ascii=False
    ).encode()).hexdigest()

    cached = Path(cache_dir) / f"{key[:32]}.json" if cache_dir else None
    if cached and cached.exists():
        return RecoveryTrajectory.model_validate_json(cached.read_text())

    data = f"Patient data:\n{json.dumps(patient, ensure_ascii=False)}"
    tail = f"Language: {language}."
    wanted = checkpoint_days(days)

    progress("usual course, personal factors and checkpoints")
    course = _ask_checked(
        ask, SYSTEM_COURSE,
        f"{data}\n\nThe plan covers day 0 to day {days}. "
        f"Checkpoint days: {', '.join(map(str, wanted))}. {tail}",
        "course", lambda text: _course(text, wanted))
    numbers = interpolate(course.checkpoints, days)
    foundations = (
        f"{data}\n\nFoundations:\n"
        + course.model_dump_json(include={"surgery", "typical_course", "personal_factors"})
    )

    plan: list[DayExpectation] = []
    for first in range(0, days + 1, DAYS_PER_BLOCK):
        block = numbers[first:first + DAYS_PER_BLOCK]
        last = block[-1].day
        progress(f"days {first}-{last}")
        previous = f"\n\nPrevious day's message: {plan[-1].patient_message}" if plan else ""
        ranges = "\n".join(
            f"{_line(e)} | {day_facts(e.day, course.typical_course, patient, course.events)}"
            for e in block)
        plan += _ask_checked(
            ask, SYSTEM_DAYS,
            f"{foundations}\n\nRanges and facts for each day:\n{ranges}{previous}"
            f"\n\nWrite days {first} to {last} inclusive. {tail}",
            "days", lambda text, b=block: _block(text, b))

    trajectory = RecoveryTrajectory(
        **course.model_dump(), days=plan, language=language, generated_by=name,
        prompt_version=PROMPT_VERSION, input_hash=key,
    )
    if cached:
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_text(trajectory.model_dump_json(indent=2))
    return trajectory


def _course(text: str, wanted: list[int]) -> _Course:
    raw = json.loads(text)
    if not isinstance(raw, dict):
        raise ValueError("the answer must be a single JSON object")
    # Rebuild our nested structure from the flat answer. Where the model's numbers break one
    # of our rules but are otherwise usable, correct them here and say so, rather than
    # failing the whole plan.
    adjustments: list[str] = []
    until = raw.get("noticeable_pain_until_day", 0)
    for c in raw.get("checkpoints") or []:
        day = c.get("day")
        for name in MEASURES:
            pair = c.get(name)
            if not (isinstance(pair, list) and len(pair) == 2
                    and all(isinstance(v, (int, float)) for v in pair)):
                raise ValueError(f"day {day}: {name} must be a [low, high] pair of numbers")
            low, high = pair
            if low > high:
                raise ValueError(f"day {day}: {name} range is upside down")
            if name == "pain" and isinstance(day, int) and day < until and high < 3:
                adjustments.append(
                    f"day {day}: top of pain range raised from {high:g} to 3, because pain was "
                    f"stated as typically noticeable until day {until}")
                high = 3
            wide = widen(name, low, high)
            if wide != (low, high):
                adjustments.append(
                    f"day {day}: {name} range {low:g}-{high:g} widened to {wide[0]:g}-{wide[1]:g} "
                    "to hold normal variation between patients")
            c[name] = {"low": wide[0], "high": wide[1]}
    keys = ("full_recovery_typically_weeks", "noticeable_pain_until_day", "phases", "lasting_symptoms")
    raw["typical_course"] = {k: raw.pop(k) for k in keys if k in raw}
    course = _Course.model_validate(raw | {"adjustments": adjustments})
    got = [c.day for c in course.checkpoints]
    if got != wanted:
        raise ValueError(f"checkpoints must be exactly days {wanted}, in order; got {got}")
    return course


def day_facts(
    day: int, course: TypicalCourse, patient: dict[str, Any], events: list[Event] = ()
) -> str:
    """What holds on this day, worked out by our code so the text cannot drift from it."""
    still = [f"{s.symptom} (usually until about day {s.typically_lasts_days:g})"
             for s in course.lasting_symptoms if s.typically_lasts_days > day]
    running, finished = [], []
    for m in patient.get("medications") or []:
        name, length = m.get("dci") or m.get("commercial_name") or "medication", m.get("duration_days")
        if length is None:
            running.append(name)
        elif day < length:
            running.append(f"{name} (course ends day {length:g})")
        else:
            finished.append(f"{name} (ended day {length:g})")
    today = [e.description for e in events if e.day == day]
    soon = [f"{e.description} in {e.day - day} day{'s' if e.day - day > 1 else ''}"
            for e in events if 0 < e.day - day <= 3]
    return (f"still expected: {'; '.join(still) or 'none listed'} | "
            f"medication running: {'; '.join(running) or 'none'} | "
            f"medication finished: {'; '.join(finished) or 'none'} | "
            f"today: {'; '.join(today) or 'nothing scheduled'} | "
            f"coming up: {'; '.join(soon) or 'nothing in the next 3 days'}")


def _line(e: Expected) -> str:
    def r(name):
        x = getattr(e, name)
        return f"{x.low:g}-{x.high:g}"

    return (f"day {e.day}: heart rate {r('heart_rate')}, SpO2 {r('spo2')}, blood pressure "
            f"{r('systolic_bp')}/{r('diastolic_bp')}, temperature {r('temperature')}, pain {r('pain')}/10")


def _block(text: str, numbers: list[Expected]) -> list[DayExpectation]:
    texts = _TEXTS.validate_json(text).get("days", [])
    want = [e.day for e in numbers]
    if [t.day for t in texts] != want:
        raise ValueError(
            f"expected days {want[0]} to {want[-1]} in order, got {[t.day for t in texts]}")
    for t in texts:
        if not t.patient_message.strip() or not t.expected_signs:
            raise ValueError(f"day {t.day}: the message and the expected signs cannot be empty")
    return [
        DayExpectation(**e.model_dump(), expected_signs=t.expected_signs, patient_message=t.patient_message)
        for e, t in zip(numbers, texts)
    ]


def _ask_checked(ask: Ask, system: str, request: str, part: str, check: Callable[[str], Any]) -> Any:
    try:
        return check(ask(system, request, part))
    except ValueError as problem:  # includes pydantic's ValidationError
        # One second chance, telling the model exactly what was wrong.
        return check(ask(system, (
            f"{request}\n\nYour previous answer was rejected by an automatic check:\n"
            f"{_brief(problem)}\nAnswer again in full, correcting this."
        ), part))


def _brief(problem: Exception) -> str:
    errors = getattr(problem, "errors", None)
    if errors is None:
        return str(problem)
    return "\n".join(sorted({e["msg"] for e in errors()})[:12])
