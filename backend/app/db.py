"""Thin repository layer. The only module that talks to SQLAlchemy sessions.

Swap the engine URL (or this module) to move from SQLite to Supabase Postgres.
"""

from contextlib import contextmanager
from datetime import datetime
from typing import Iterator, TypeVar

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, delete, select

from . import models as m
from .config import settings

T = TypeVar("T", bound=SQLModel)

_engine = None


def configure(url: str | None = None):
    """(Re)create the engine. `sqlite://` gives a shared in-memory DB (tests)."""
    global _engine
    url = url or settings.db_url
    kwargs: dict = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False, "timeout": 15}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool
    _engine = create_engine(url, **kwargs)
    SQLModel.metadata.create_all(_engine)
    return _engine


def engine():
    return _engine or configure()


def drop_all():
    SQLModel.metadata.drop_all(engine())
    SQLModel.metadata.create_all(engine())


class Repo:
    def __init__(self, session: Session):
        self.s = session

    # -- generic
    def add(self, obj: T) -> T:
        self.s.add(obj)
        self.s.commit()
        self.s.refresh(obj)
        return obj

    def get(self, model: type[T], id_) -> T | None:
        return self.s.get(model, id_)

    def all(self, model: type[T], *where, order=None, limit: int | None = None) -> list[T]:
        q = select(model)
        for w in where:
            q = q.where(w)
        if order is not None:
            q = q.order_by(order)
        if limit:
            q = q.limit(limit)
        return list(self.s.exec(q))

    def first(self, model: type[T], *where, order=None) -> T | None:
        rows = self.all(model, *where, order=order, limit=1)
        return rows[0] if rows else None

    def delete_where(self, model, *where):
        q = delete(model)
        for w in where:
            q = q.where(w)
        self.s.exec(q)
        self.s.commit()

    def refresh(self, obj):
        self.s.refresh(obj)
        return obj

    # -- domain helpers
    def patient(self, patient_id: str) -> m.Patient | None:
        return self.get(m.Patient, patient_id)

    def plan(self, patient_id: str) -> dict:
        row = self.first(m.SurveillancePlan, m.SurveillancePlan.patient_id == patient_id,
                         order=m.SurveillancePlan.created_at.desc())
        return row.plan if row else {}

    def member(self, member_id: str) -> m.CareTeamMember | None:
        return self.get(m.CareTeamMember, member_id)

    def members(self, patient_id: str, role: str | None = None) -> list[m.CareTeamMember]:
        where = [m.CareTeamMember.patient_id == patient_id]
        if role:
            where.append(m.CareTeamMember.role == role)
        return self.all(m.CareTeamMember, *where)

    def observations(self, patient_id: str, type_: str | None = None, since: datetime | None = None,
                     until: datetime | None = None, source: str | None = None, newest_first=False,
                     limit: int | None = None) -> list[m.Observation]:
        where = [m.Observation.patient_id == patient_id]
        if type_:
            where.append(m.Observation.type == type_)
        if since:
            where.append(m.Observation.measured_at >= since)
        if until:
            where.append(m.Observation.measured_at <= until)
        if source:
            where.append(m.Observation.source == source)
        order = m.Observation.measured_at.desc() if newest_first else m.Observation.measured_at
        return self.all(m.Observation, *where, order=order, limit=limit)

    def latest(self, patient_id: str, type_: str, good_only=False) -> m.Observation | None:
        where = [m.Observation.patient_id == patient_id, m.Observation.type == type_]
        if good_only:
            where.append(m.Observation.quality == "good")
        return self.first(m.Observation, *where, order=m.Observation.measured_at.desc())

    def open_alerts(self, patient_id: str | None = None) -> list[m.Alert]:
        where = [m.Alert.state != "resolved"]
        if patient_id:
            where.append(m.Alert.patient_id == patient_id)
        return self.all(m.Alert, *where, order=m.Alert.created_at)

    def active_investigation(self, patient_id: str) -> m.Investigation | None:
        return self.first(m.Investigation, m.Investigation.patient_id == patient_id,
                          m.Investigation.status.in_(["running", "waiting_patient"]))

    def pending_requests(self, patient_id: str) -> list[m.PatientRequest]:
        return self.all(m.PatientRequest, m.PatientRequest.patient_id == patient_id,
                        m.PatientRequest.status == "pending", order=m.PatientRequest.created_at)


@contextmanager
def session_scope() -> Iterator[Repo]:
    with Session(engine(), expire_on_commit=False) as s:
        yield Repo(s)


def get_repo() -> Iterator[Repo]:
    """FastAPI dependency."""
    with session_scope() as repo:
        yield repo
