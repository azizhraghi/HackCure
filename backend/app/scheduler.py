"""APScheduler jobs (wall-clock). Every job can also be fired instantly via POST /demo/run/{job}."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from . import sweep
from .agents import checkin, digest, medication
from .config import DEMO_PATIENT_ID, settings
from .db import session_scope

log = logging.getLogger("surgiguard.scheduler")
_scheduler: BackgroundScheduler | None = None


def _safe(fn):
    def wrapper():
        try:
            with session_scope() as repo:
                fn(repo)
        except Exception:  # keep the scheduler alive
            log.exception("scheduled job %s failed", fn.__name__)
    wrapper.__name__ = fn.__name__
    return wrapper


@_safe
def sweep_job(repo):
    sweep.run(repo)


@_safe
def checkin_job(repo):
    checkin.send_reminder(repo, DEMO_PATIENT_ID)


@_safe
def medication_job(repo):
    medication.send_due_reminders(repo, DEMO_PATIENT_ID)


@_safe
def digest_job(repo):
    for cg in repo.members(DEMO_PATIENT_ID, "caregiver"):
        digest.generate(repo, DEMO_PATIENT_ID, cg.id)


def start() -> None:
    global _scheduler
    if _scheduler or not settings.scheduler_enabled:
        return
    s = BackgroundScheduler(job_defaults={"coalesce": True, "max_instances": 1})
    s.add_job(sweep_job, "interval", seconds=settings.sweep_interval_s, id="sweep")
    s.add_job(medication_job, "interval", seconds=60, id="medication")
    s.add_job(checkin_job, "cron", hour="8,20", minute=0, id="checkin")
    s.add_job(digest_job, "cron", hour=20, minute=5, id="digest")
    s.start()
    _scheduler = s


def stop() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
