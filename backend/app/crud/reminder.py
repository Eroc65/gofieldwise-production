from datetime import timedelta
from typing import Any, List, Optional, cast

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models.core import Customer, Job, REMINDER_STATUSES, Reminder, SmsOptOut, _utcnow
from ..services.twilio_gateway import send_sms_message


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


def create_review_request_reminder(
    db: Session,
    job_id: int,
    customer_id: int,
    organization_id: int,
    days_until_due: int = 1,
) -> Reminder:
    """Create a post-completion review request reminder for SMS dispatch."""
    due = _utcnow() + timedelta(days=days_until_due)
    reminder = Reminder(
        message=f"Review request: Thanks for your service visit on job #{job_id}. We'd love your feedback.",
        channel="sms",
        status="pending",
        due_at=due,
        job_id=job_id,
        customer_id=customer_id,
        organization_id=organization_id,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


def run_reactivation_engine(
    db: Session,
    organization_id: int,
    lookback_days: int = 180,
    limit: int = 250,
    dry_run: bool = False,
) -> dict:
    """Queue SMS reminders for customers with no completed jobs in the lookback window."""
    lookback_days = max(30, lookback_days)
    limit = min(max(limit, 1), 1000)
    cutoff = _utcnow() - timedelta(days=lookback_days)

    latest_completed = (
        db.query(
            Job.customer_id.label("customer_id"),
            func.max(Job.completed_at).label("last_completed_at"),
        )
        .filter(
            Job.organization_id == organization_id,
            Job.completed_at.isnot(None),
        )
        .group_by(Job.customer_id)
        .subquery()
    )

    stale_customers = (
        db.query(Customer)
        .outerjoin(latest_completed, latest_completed.c.customer_id == Customer.id)
        .filter(Customer.organization_id == organization_id)
        .filter(
            (latest_completed.c.last_completed_at.is_(None))
            | (latest_completed.c.last_completed_at < cutoff)
        )
        .limit(limit)
        .all()
    )

    if dry_run:
        return {
            "organization_id": organization_id,
            "lookback_days": lookback_days,
            "dry_run": True,
            "candidate_count": len(stale_customers),
            "queued_count": 0,
            "queued_customer_ids": [],
        }

    queued_ids: list[int] = []
    for customer in stale_customers:
        customer_id = int(cast(int, customer.id))

        existing_pending = (
            db.query(Reminder)
            .filter(
                Reminder.organization_id == organization_id,
                Reminder.customer_id == customer_id,
                Reminder.status == "pending",
                Reminder.message.like("Reactivation:%"),
            )
            .first()
        )
        if existing_pending:
            continue

        message = (
            "Reactivation: It has been a while since your last service. "
            "Reply to book a visit this week."
        )
        db.add(
            Reminder(
                message=message,
                channel="sms",
                status="pending",
                due_at=_utcnow(),
                customer_id=customer_id,
                organization_id=organization_id,
            )
        )
        queued_ids.append(customer_id)

    db.commit()
    return {
        "organization_id": organization_id,
        "lookback_days": lookback_days,
        "dry_run": False,
        "candidate_count": len(stale_customers),
        "queued_count": len(queued_ids),
        "queued_customer_ids": queued_ids,
    }


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


def _normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    chars = [ch for ch in str(phone).strip() if ch.isdigit() or ch == "+"]
    normalized = "".join(chars)
    return normalized or None


def _reminder_destination(reminder: Reminder) -> tuple[str | None, str | None]:
    phone = None
    email = None
    if reminder.customer:
        phone = reminder.customer.phone
        email = reminder.customer.email
    elif reminder.lead:
        phone = reminder.lead.phone
        email = reminder.lead.email
    return _normalize_phone(phone), email


def _is_sms_opted_out(db: Session, organization_id: int, phone: str | None) -> bool:
    if not phone:
        return False
    row = (
        db.query(SmsOptOut)
        .filter(
            SmsOptOut.organization_id == organization_id,
            SmsOptOut.phone == phone,
        )
        .first()
    )
    return row is not None


def _create_internal_alert(db: Session, organization_id: int, message: str) -> None:
    db.add(
        Reminder(
            message=f"ALERT: {message}",
            channel="internal",
            status="pending",
            due_at=_utcnow(),
            organization_id=organization_id,
        )
    )


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

        channel = str(cast(str, reminder.channel))
        phone, _email = _reminder_destination(reminder)
        if channel == "sms" and _is_sms_opted_out(db, organization_id, phone):
            reminder_obj.status = "dismissed"
            reminder_obj.last_dispatch_error = "Suppressed due to SMS opt-out"
            reminder_obj.updated_at = now
            _create_internal_alert(
                db,
                organization_id,
                f"SMS reminder #{int(cast(int, reminder.id))} suppressed because destination is opted out",
            )
            failed.append({"id": int(cast(int, reminder.id)), "error": str(cast(str, reminder_obj.last_dispatch_error))})
            continue

        if channel == "sms" and phone:
            ok, external_message_id, sms_error = send_sms_message(
                db,
                organization_id=organization_id,
                to_phone=phone,
                body=str(cast(str, reminder.message)),
            )
            if not ok:
                reminder_obj.last_dispatch_error = sms_error or "SMS dispatch failed"
                reminder_obj.updated_at = now
                _create_internal_alert(
                    db,
                    organization_id,
                    f"SMS reminder #{int(cast(int, reminder.id))} failed to send: {reminder_obj.last_dispatch_error}",
                )
                failed.append({"id": int(cast(int, reminder.id)), "error": str(cast(str, reminder_obj.last_dispatch_error))})
                continue
            reminder_obj.external_message_id = external_message_id

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
