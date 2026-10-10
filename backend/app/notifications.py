"""Delivered notifications (polled by the app / dashboard). Delivery and reading are NOT acknowledgement."""

from . import audit, clock
from . import models as m
from .db import Repo


def caregiver_allowed(plan: dict, caregiver_id: str, category: str) -> bool:
    perms = plan.get("caregiver_permissions", {}).get(caregiver_id, {}).get("categories", {})
    return bool(perms.get(category, False))


def notify(repo: Repo, patient_id: str, member_id: str, kind: str, title: str, body: str = "",
           ref_type: str | None = None, ref_id: str | None = None, dedupe_key: str | None = None,
           category: str | None = None) -> m.Notification | None:
    """Create a notification. Caregivers only receive categories the patient allowed."""
    member = repo.member(member_id)
    if member is None:
        return None
    if member.role == "caregiver" and category and not caregiver_allowed(repo.plan(patient_id), member_id, category):
        audit.log(repo, patient_id, "system", "notification.suppressed",
                  {"member": member_id, "category": category, "kind": kind}, ref_type, ref_id)
        return None
    if dedupe_key and repo.first(m.Notification, m.Notification.dedupe_key == dedupe_key,
                                 m.Notification.member_id == member_id):
        return None
    n = repo.add(m.Notification(patient_id=patient_id, member_id=member_id, kind=kind, title=title, body=body,
                                ref_type=ref_type, ref_id=ref_id, dedupe_key=dedupe_key))
    audit.log(repo, patient_id, "system", "notification.delivered",
              {"notification_id": n.id, "member": member_id, "kind": kind, "title": title}, ref_type, ref_id)
    return n


def mark_read(repo: Repo, notification_id: str, member_id: str) -> m.Notification | None:
    n = repo.get(m.Notification, notification_id)
    if n is None or n.member_id != member_id:
        return None
    if n.read_at is None:
        n.read_at = clock.now()
        repo.add(n)
        audit.log(repo, n.patient_id, member_id, "notification.read", {"notification_id": n.id}, n.ref_type, n.ref_id)
    return n
