"""Training data for the expected-trajectory model.

One row is one measurement of one metric for one past patient, with that
patient's background. Any source (real records or simulated patients) is
converted to this shape; the model code does not care which it is.

CSV columns: patient_id, postoperative_day, metric, value, then one column
per feature named in the FeatureSpec.
"""

import csv
import json
import random
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class FeatureSpec:
    """Which patient-background columns the model uses."""

    numeric: tuple[str, ...] = ("age",)
    # Used when known, allowed to be missing (e.g. the patient's own baseline).
    optional_numeric: tuple[str, ...] = ()
    categorical: tuple[str, ...] = ("procedure",)
    optional_categorical: tuple[str, ...] = ()
    flags: tuple[str, ...] = ()  # yes/no features such as conditions or medications

    @classmethod
    def infer(
        cls, rows: list["Row"], required_numeric: tuple[str, ...] = ("age",),
        required_categorical: tuple[str, ...] = ("surgery.procedure",), min_patients: int = 20,
    ) -> "FeatureSpec":
        """Use every dossier field that enough training patients have.

        A field seen in fewer than `min_patients` patients is left out: the
        model could not learn anything reliable from it.
        """
        seen: dict[str, dict] = {}
        for r in rows:
            seen.setdefault(r.patient_id, r)
        patients = list(seen.values())
        numeric = Counter(k for p in patients for k in p.numeric)
        flags = Counter(k for p in patients for k in p.flags)
        categorical: dict[str, set] = {}
        for p in patients:
            for k, v in p.categorical.items():
                categorical.setdefault(k, set()).add(v)
        cat_count = Counter(k for p in patients for k in p.categorical)
        return cls(
            numeric=required_numeric,
            optional_numeric=tuple(sorted(
                k for k, n in numeric.items() if n >= min_patients and k not in required_numeric)),
            categorical=required_categorical,
            optional_categorical=tuple(sorted(
                k for k, n in cat_count.items()
                if n >= min_patients and k not in required_categorical and len(categorical[k]) <= 50)),
            flags=tuple(sorted(k for k, n in flags.items() if n >= min_patients)),
        )


@dataclass(frozen=True)
class Row:
    patient_id: str
    day: float  # days since surgery, fractional
    metric: str
    value: float
    numeric: dict[str, float] = field(default_factory=dict)
    categorical: dict[str, str] = field(default_factory=dict)
    flags: frozenset[str] = frozenset()


def load_csv(path: str | Path, spec: FeatureSpec) -> list[Row]:
    rows: list[Row] = []
    with open(path, newline="") as f:
        for line in csv.DictReader(f):
            rows.append(Row(
                patient_id=line["patient_id"],
                day=float(line["postoperative_day"]),
                metric=line["metric"],
                value=float(line["value"]),
                numeric={k: float(line[k]) for k in (*spec.numeric, *spec.optional_numeric)
                         if line.get(k, "") != ""},
                categorical={k: line[k] for k in spec.categorical if line.get(k, "") != ""},
                flags=frozenset(k for k in spec.flags if line.get(k, "") in {"1", "true", "True"}),
            ))
    return rows


def save_csv(rows: list[Row], path: str | Path, spec: FeatureSpec) -> None:
    columns = ["patient_id", "postoperative_day", "metric", "value",
               *spec.numeric, *spec.optional_numeric, *spec.categorical, *spec.flags]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        for r in rows:
            w.writerow({
                "patient_id": r.patient_id, "postoperative_day": r.day,
                "metric": r.metric, "value": r.value,
                **{k: r.numeric.get(k, "") for k in (*spec.numeric, *spec.optional_numeric)},
                **{k: r.categorical.get(k, "") for k in spec.categorical},
                **{k: int(k in r.flags) for k in spec.flags},
            })


def split_by_patient(
    rows: list[Row], test_fraction: float = 0.2, seed: int = 0
) -> tuple[list[Row], list[Row]]:
    """Hold out whole patients, so no patient is in both train and test."""
    patients = sorted({r.patient_id for r in rows})
    random.Random(seed).shuffle(patients)
    held_out = set(patients[: max(1, round(len(patients) * test_fraction))])
    return (
        [r for r in rows if r.patient_id not in held_out],
        [r for r in rows if r.patient_id in held_out],
    )


def rows_from_patients(patients: list[dict]) -> list[Row]:
    """Each patient is {"patient_id", "dossier": {...}, "measurements": [{"metric", "day", "value"}]}."""
    from .dossier import flatten

    rows: list[Row] = []
    for p in patients:
        profile = flatten(p["dossier"])
        for m in p["measurements"]:
            rows.append(Row(
                patient_id=p["patient_id"], day=float(m["day"]), metric=m["metric"],
                value=float(m["value"]), numeric=profile.numeric,
                categorical=profile.categorical, flags=profile.flags,
            ))
    return rows


def load_jsonl(path: str | Path) -> list[Row]:
    """One past patient per line: his dossier and his measurements after surgery."""
    with open(path) as f:
        return rows_from_patients([json.loads(line) for line in f if line.strip()])


def save_jsonl(patients: list[dict], path: str | Path) -> None:
    with open(path, "w") as f:
        for p in patients:
            f.write(json.dumps(p) + "\n")
