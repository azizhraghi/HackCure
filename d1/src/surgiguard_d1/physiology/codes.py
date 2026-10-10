"""Canonical physiological codes and units from the shared integration contract."""

CANONICAL_UNITS: dict[str, str] = {
    "spo2": "%",
    "hr": "beats/min",
    "sbp": "mmHg",
    "dbp": "mmHg",
    "temperature": "Cel",
}

# Accepted only when the protocol declares a reliable approved measurement method.
OPTIONAL_UNITS: dict[str, str] = {"rr": "breaths/min"}

BP_CODES = frozenset({"sbp", "dbp"})

# (code, incoming unit) -> conversion to the canonical unit. The original
# value/unit is kept in ingestion provenance, never overwritten silently.
CONVERSIONS = {
    ("temperature", "[degF]"): lambda v: (v - 32.0) * 5.0 / 9.0,
}


def canonical_unit(code: str, rr_enabled: bool = False) -> str | None:
    if code in CANONICAL_UNITS:
        return CANONICAL_UNITS[code]
    if rr_enabled and code in OPTIONAL_UNITS:
        return OPTIONAL_UNITS[code]
    return None
