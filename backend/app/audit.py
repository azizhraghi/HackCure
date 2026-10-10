"""Append-only audit log of every agent step, tool call, rule decision and human action."""

from typing import Any

from . import models as m
from .db import Repo


def log(repo: Repo, patient_id: str, actor: str, kind: str, data: dict[str, Any] | None = None,
        ref_type: str | None = None, ref_id: str | None = None) -> m.AuditEvent:
    return repo.add(m.AuditEvent(patient_id=patient_id, actor=actor, kind=kind, data=_jsonable(data or {}),
                                 ref_type=ref_type, ref_id=ref_id))


def trail(repo: Repo, ref_type: str | None = None, ref_id: str | None = None,
          patient_id: str | None = None, limit: int = 500) -> list[m.AuditEvent]:
    where = []
    if ref_type:
        where.append(m.AuditEvent.ref_type == ref_type)
    if ref_id:
        where.append(m.AuditEvent.ref_id == ref_id)
    if patient_id:
        where.append(m.AuditEvent.patient_id == patient_id)
    return repo.all(m.AuditEvent, *where, order=m.AuditEvent.id, limit=limit)


def _jsonable(v):
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    if hasattr(v, "isoformat"):
        return v.isoformat()
    if hasattr(v, "model_dump"):
        return _jsonable(v.model_dump())
    return str(v)
