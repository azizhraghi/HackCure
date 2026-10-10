"""Periodic sweep (APScheduler, every few seconds): timeouts and escalations."""

from . import alerts, clock
from .db import Repo


def run(repo: Repo) -> dict:
    now = clock.now()
    escalated = alerts.escalate_overdue(repo, now)
    return {"at": now.isoformat(), "escalated_alerts": [a.id for a in escalated]}
