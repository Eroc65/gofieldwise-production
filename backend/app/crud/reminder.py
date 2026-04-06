from datetime import timedelta
from typing import Any, List, Optional, cast

from sqlalchemy.orm import Session

from ..models.core import REMINDER_STATUSES, Reminder, _utcnow


# Default follow-up window: if a new lead sits uncontacted for this long, a
# reminder becomes overdue.
DEFAULT_LEAD_FOLLOWUP_HOURS = 1


def create_reminder(
    db: Session,
    data: dict,
    organization_id: int,
) -> Reminder:
    reminder = Reminder(**data, organization_id=organization_id)
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


def create_lead_followup_reminder(
    db: Session,
    lead_id: int,
    organization_id: int,
    lead_name: Optional[str] = None,
    hours: int = DEFAULT_LEAD_FOLLOWUP_HOURS,
) -> Reminder:
    """Auto-create a follow-up reminder for a new inbound lead."""
    name = lead_name or f"lead #{lead_id}"
    due = _utcnow() + timedelta(hours=hours)
    reminder = Reminder(
        message=f"Follow up with {name}",
        channel="internal",
        status="pending",
        due_at=due,
        lead_id=lead_id,
        organization_id=organization_id,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


def create_lead_booking_reminder(
    db: Session,
    lead_id: int,
    organization_id: int,
    lead_name: Optional[str] = None,
) -> Reminder:
    """Create an immediate booking reminder after qualification."""
    name = lead_name or f"lead #{lead_id}"
    reminder = Reminder(
        message=f"Book job with {name}",
        channel="internal",
        status="pending",
        due_at=_utcnow(),
        lead_id=lead_id,
        organization_id=organization_id,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


def create_job_completion_reminder(
    db: Session,
    job_id: int,
    organization_id: int,
    job_title: Optional[str] = None,
    days_until_due: int = 3,
) -> Reminder:
    """Auto-create a completion reminder for a dispatched job."""
    title = job_title or f"job #{job_id}"
    due = _utcnow() + timedelta(days=days_until_due)
    reminder = Reminder(
        message=f"Mark {title} complete",
        channel="internal",
        status="pending",
        due_at=due,
        job_id=job_id,
        organization_id=organization_id,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


def get_reminder(
    db: Session, reminder_id: int, organization_id: int
) -> Optional[Reminder]:
    return (
        db.query(Reminder)
        .filter(
            Reminder.id == reminder_id,
            Reminder.organization_id == organization_id,
        )
        .first()
    )


def get_reminders(
    db: Session,
    organization_id: int,
    status: Optional[str] = None,
    lead_id: Optional[int] = None,
    job_id: Optional[int] = None,
    customer_id: Optional[int] = None,
) -> List[Reminder]:
    q = db.query(Reminder).filter(Reminder.organization_id == organization_id)
    if status:
        q = q.filter(Reminder.status == status)
    if lead_id is not None:
        q = q.filter(Reminder.lead_id == lead_id)
    if job_id is not None:
        q = q.filter(Reminder.job_id == job_id)
    if customer_id is not None:
        q = q.filter(Reminder.customer_id == customer_id)
    return q.order_by(Reminder.due_at.asc()).all()


def get_overdue_reminders(db: Session, organization_id: int) -> List[Reminder]:
    """Pending reminders whose due_at is in the past."""
    now = _utcnow()
    return (
        db.query(Reminder)
        .filter(
            Reminder.organization_id == organization_id,
            Reminder.status == "pending",
            Reminder.due_at <= now,
        )
        .order_by(Reminder.due_at.asc())
        .all()
    )


def update_reminder_status(
    db: Session, reminder: Reminder, new_status: str
) -> tuple[Reminder, Optional[str]]:
    """Transition reminder status. Returns (reminder, error_message)."""
    if new_status not in REMINDER_STATUSES:
        valid = ", ".join(REMINDER_STATUSES)
        return reminder, f"Invalid status '{new_status}'. Must be one of: {valid}."
    current_status = str(cast(str, reminder.status))
    if current_status == new_status:
        return reminder, None  # idempotent
    reminder_obj = cast(Any, reminder)
    reminder_obj.status = new_status
    if new_status == "sent":
        reminder_obj.sent_at = _utcnow()
    reminder_obj.updated_at = _utcnow()
    db.commit()
    db.refresh(reminder)
    return reminder, None


def _channel_contact_available(reminder: Reminder) -> bool:
    channel = str(cast(str, reminder.channel))
    if channel == "internal":
        return True

    phone = None
    email = None
    if reminder.customer:
        phone = reminder.customer.phone
        email = reminder.customer.email
    elif reminder.lead:
        phone = reminder.lead.phone
        email = reminder.lead.email

    if channel in ("sms", "call"):
        return bool(phone)
    if channel == "email":
        return bool(email)
    return False


def dispatch_due_reminders(
    db: Session,
    organization_id: int,
    limit: int = 50,
    dry_run: bool = False,
) -> dict:
    now = _utcnow()
    candidates = (
        db.query(Reminder)
        .filter(
            Reminder.organization_id == organization_id,
            Reminder.status == "pending",
            Reminder.due_at <= now,
        )
        .order_by(Reminder.due_at.asc())
        .limit(limit)
        .all()
    )

    sent_ids: list[int] = []
    failed: list[dict] = []

    if dry_run:
        return {
            "organization_id": organization_id,
            "dry_run": True,
            "candidate_count": len(candidates),
            "sent_count": 0,
            "failed_count": 0,
            "sent_ids": [],
            "failed": [],
        }

    for reminder in candidates:
        reminder_obj = cast(Any, reminder)
        reminder_obj.dispatch_attempts = int(cast(int, reminder.dispatch_attempts or 0)) + 1
        if not _channel_contact_available(reminder):
            reminder_obj.last_dispatch_error = "Missing destination contact for reminder channel"
            reminder_obj.updated_at = now
            failed.append({"id": int(cast(int, reminder.id)), "error": str(cast(str, reminder.last_dispatch_error))})
            continue

        reminder_obj.status = "sent"
        reminder_obj.sent_at = now
        reminder_obj.last_dispatch_error = None
        reminder_obj.updated_at = now
        sent_ids.append(int(cast(int, reminder.id)))

    db.commit()

    return {
        "organization_id": organization_id,
        "dry_run": False,
        "candidate_count": len(candidates),
        "sent_count": len(sent_ids),
        "failed_count": len(failed),
        "sent_ids": sent_ids,
        "failed": failed,
    }
