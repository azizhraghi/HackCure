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
    from .models import Patient
    for patient in repo.all(Patient):
        medication.send_due_reminders(repo, patient.id)


@_safe
def digest_job(repo):
    for cg in repo.members(DEMO_PATIENT_ID, "caregiver"):
        digest.generate(repo, DEMO_PATIENT_ID, cg.id)


@_safe
def esp32_sync_job(repo):
    from .integrations import surgiguard_api
    if surgiguard_api.enabled():
        surgiguard_api.sync_telemetry(repo)


@_safe
def api_link_job(repo):
    from .integrations import surgiguard_api
    if surgiguard_api.enabled() and surgiguard_api.api_patient():
        surgiguard_api.sync_plan_to_api(repo)
        surgiguard_api.sync_doses_from_api(repo)


def start() -> None:
    global _scheduler
    if _scheduler or not settings.scheduler_enabled:
        return
    s = BackgroundScheduler(job_defaults={"coalesce": True, "max_instances": 1})
    s.add_job(sweep_job, "interval", seconds=settings.sweep_interval_s, id="sweep")
    s.add_job(medication_job, "interval", seconds=60, id="medication")
    s.add_job(esp32_sync_job, "interval", seconds=settings.esp32_poll_s, id="esp32_sync")
    s.add_job(api_link_job, "interval", seconds=20, id="api_link")
    s.add_job(checkin_job, "cron", hour="8,20", minute=0, id="checkin")
    s.add_job(digest_job, "cron", hour=20, minute=5, id="digest")
    s.start()
    _scheduler = s


def stop() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
