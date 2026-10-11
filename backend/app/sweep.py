"""Periodic sweep (APScheduler, every few seconds): timeouts and escalations."""

from . import alerts, clock, wound_photos
from .agents import investigation
from .db import Repo


def run(repo: Repo) -> dict:
    now = clock.now()
    inv = investigation.sweep(repo)
    escalated = alerts.escalate_overdue(repo, now)
    return {"at": now.isoformat(), **inv, "escalated_alerts": [a.id for a in escalated],
            "scheduled_photo_requests": wound_photos.sweep(repo),
            "recovered_investigations": investigation.recover(repo)}
