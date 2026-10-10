"""Turn a patient's medical dossier (JSON from Developer 2) into model inputs.

The whole dossier is read, whatever its fields:
  numbers          -> numeric features          {"age": 68}            -> age
  text             -> categories                {"sex": "male"}        -> sex
  true/false       -> yes/no flags              {"smoker": true}       -> smoker
  lists of names   -> one flag per entry        {"conditions": [...]}  -> conditions.diabetes
  lists of objects -> one flag per named entry  {"medications": [{"name": ...}]}
  nested objects   -> dotted names              {"surgery": {"procedure": ...}} -> surgery.procedure

Identifiers, names and dates are skipped: they identify the patient, they
do not describe him. Which of these features the model actually uses depends
on what it saw in training; the rest are reported back as unused.
"""

from typing import Any

from .model import PatientProfile

_SKIP = {"id", "name", "first_name", "last_name", "full_name", "date", "notes"}
_SKIP_SUFFIXES = ("_id", "_at", "_date", "_name")
_NAME_KEYS = ("name", "code", "label", "class", "type")


def _slug(text: Any) -> str:
    return "_".join(str(text).strip().lower().split())


def flatten(dossier: dict[str, Any]) -> PatientProfile:
    numeric: dict[str, float] = {}
    categorical: dict[str, str] = {}
    flags: set[str] = set()

    def walk(prefix: str, value: Any) -> None:
        if value is None:
            return
        if isinstance(value, bool):
            if value:
                flags.add(prefix)
        elif isinstance(value, (int, float)):
            numeric[prefix] = float(value)
        elif isinstance(value, str):
            if value.strip():
                categorical[prefix] = _slug(value)
        elif isinstance(value, dict):
            for k, v in value.items():
                key = _slug(k)
                if key in _SKIP or key.endswith(_SKIP_SUFFIXES):
                    continue
                walk(f"{prefix}.{key}" if prefix else key, v)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    name = next((item[k] for k in _NAME_KEYS if item.get(k)), None)
                    if name is not None:
                        flags.add(f"{prefix}.{_slug(name)}")
                elif isinstance(item, (str, int)) and not isinstance(item, bool):
                    flags.add(f"{prefix}.{_slug(item)}")

    walk("", dossier)
    return PatientProfile(numeric=numeric, categorical=categorical, flags=frozenset(flags))
