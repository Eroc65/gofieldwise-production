from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from ..models.core import Customer, Estimate, Job, JobActivity, JOB_VALID_TRANSITIONS, Reminder, Technician
from .reminder import create_review_request_reminder
from ..services.notifications import send_job_lifecycle_notification

CENTRAL_TZ = ZoneInfo("America/Chicago")

def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _normalize_schedule_time(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _parse_weekdays(value: str) -> set[int]:
    days: set[int] = set()
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            day = int(part)
        except ValueError:
            continue
        if 0 <= day <= 6:
            days.add(day)
    return days


def technician_is_available_at(technician: Technician, scheduled_time: datetime) -> bool:
    ts = scheduled_time
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    local_ts = ts.astimezone(CENTRAL_TZ)
    weekdays = _parse_weekdays(technician.availability_weekdays or "")
    if weekdays and local_ts.weekday() not in weekdays:
        return False
    start_hour = int(technician.availability_start_hour_utc)
    end_hour = int(technician.availability_end_hour_utc)
    hour = local_ts.hour
    return start_hour <= hour < end_hour

def get_jobs(db: Session, organization_id: int) -> List[Job]:
    return db.query(Job).filter(Job.organization_id == organization_id).all()

def get_job(db: Session, job_id: int, organization_id: int) -> Optional[Job]:
    return db.query(Job).filter(Job.id == job_id, Job.organization_id == organization_id).first()


def get_job_timeline(db: Session, job_id: int, organization_id: int) -> list[JobActivity]:
    return (
        db.query(JobActivity)
        .filter(
            JobActivity.job_id == job_id,
            JobActivity.organization_id == organization_id,
        )
        .order_by(JobActivity.created_at.desc(), JobActivity.id.desc())
        .all()
    )


def _can_transition(from_status: str, to_status: str) -> bool:
    return to_status in JOB_VALID_TRANSITIONS.get(from_status, set())


def _record_job_activity(
    db: Session,
    *,
    organization_id: int,
    job_id: int,
    action: str,
    from_status: Optional[str],
    to_status: str,
    actor_user_id: Optional[int] = None,
    note: Optional[str] = None,
) -> None:
    db.add(
        JobActivity(
            action=action,
            from_status=from_status,
            to_status=to_status,
            actor_user_id=actor_user_id,
            note=note,
            job_id=job_id,
            organization_id=organization_id,
        )
    )

def create_job(db: Session, job: dict, organization_id: int) -> Job:
    customer_id = job.get("customer_id")
    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id, Customer.organization_id == organization_id)
        .first()
    )
    if not customer:
        raise ValueError("Customer not found in your organization")

    technician_id = job.get("technician_id")
    if technician_id is not None:
        technician = (
            db.query(Technician)
            .filter(Technician.id == technician_id, Technician.organization_id == organization_id)
            .first()
        )
        if not technician:
            raise ValueError("Technician not found in your organization")

    db_job = Job(**job, organization_id=organization_id)
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

def update_job(db: Session, db_job: Job, updates: dict) -> Job:
    for key, value in updates.items():
        setattr(db_job, key, value)
    db.commit()
    db.refresh(db_job)
    return db_job


def dispatch_job(
    db: Session,
    db_job: Job,
    organization_id: int,
    technician_id: int,
    scheduled_time,
    buffer_minutes: int = 0,
    actor_user_id: Optional[int] = None,
) -> Tuple[Optional[Job], Optional[str]]:
    normalized_time = _normalize_schedule_time(scheduled_time)

    technician = (
        db.query(Technician)
        .filter(Technician.id == technician_id, Technician.organization_id == organization_id)
        .first()
    )
    if not technician:
        return None, "Technician not found in your organization"

    if not technician_is_available_at(technician, normalized_time):
        return None, "Technician is outside configured availability window"

    conflict = get_dispatch_conflict(
        db,
        organization_id,
        technician_id,
        normalized_time,
        exclude_job_id=int(db_job.id) if db_job.id is not None else None,
        buffer_minutes=buffer_minutes,
    )
    if conflict:
        return None, "Technician already has a job scheduled at that time"

    from_status = db_job.status
    if not _can_transition(from_status, "dispatched"):
        return None, f"Cannot dispatch job with status '{from_status}'."

    db_job.technician_id = technician_id
    db_job.scheduled_time = normalized_time
    db_job.status = "dispatched"
    _record_job_activity(
        db,
        organization_id=organization_id,
        job_id=int(db_job.id),
        action="dispatched",
        from_status=from_status,
        to_status="dispatched",
        actor_user_id=actor_user_id,
        note=f"Scheduled for {normalized_time.isoformat()}",
    )
    db.commit()
    db.refresh(db_job)
    
    # Auto-create completion reminder for technician
    from .reminder import create_job_completion_reminder
    create_job_completion_reminder(db, db_job.id, organization_id, db_job.title)
    
    return db_job, None


def get_dispatch_conflict(
    db: Session,
    organization_id: int,
    technician_id: int,
    scheduled_time: datetime,
    exclude_job_id: Optional[int] = None,
    buffer_minutes: int = 0,
) -> Optional[Job]:
    normalized_time = _normalize_schedule_time(scheduled_time)
    window_start = normalized_time - timedelta(minutes=max(0, buffer_minutes))
    window_end = normalized_time + timedelta(minutes=max(0, buffer_minutes))

    query = db.query(Job).filter(
        Job.organization_id == organization_id,
        Job.technician_id == technician_id,
        Job.scheduled_time >= window_start,
        Job.scheduled_time <= window_end,
    )
    if exclude_job_id is not None:
        query = query.filter(Job.id != exclude_job_id)
    return query.first()


def find_next_available_slot(
    db: Session,
    organization_id: int,
    technician_id: int,
    requested_time: datetime,
    search_hours: int = 24,
    step_minutes: int = 30,
    exclude_job_id: Optional[int] = None,
    buffer_minutes: int = 0,
) -> Tuple[Optional[datetime], list[int]]:
    technician = (
        db.query(Technician)
        .filter(Technician.id == technician_id, Technician.organization_id == organization_id)
        .first()
    )
    if technician is None:
        return None, []

    candidate = _normalize_schedule_time(requested_time)
    horizon = candidate + timedelta(hours=search_hours)
    seen_conflicts: list[int] = []

    while candidate <= horizon:
        if not technician_is_available_at(technician, candidate):
            candidate = candidate + timedelta(minutes=step_minutes)
            continue

        conflict = get_dispatch_conflict(
            db,
            organization_id,
            technician_id,
            candidate,
            exclude_job_id=exclude_job_id,
            buffer_minutes=buffer_minutes,
        )
        if conflict is None:
            return candidate, seen_conflicts
        if conflict.id is not None and conflict.id not in seen_conflicts:
            seen_conflicts.append(int(conflict.id))
        candidate = candidate + timedelta(minutes=step_minutes)

    return None, seen_conflicts


def complete_job(
    db: Session,
    db_job: Job,
    organization_id: int,
    completion_notes: Optional[str] = None,
    actor_user_id: Optional[int] = None,
) -> Tuple[Optional[Job], Optional[str]]:
    """Mark a job as completed. Auto-creates follow-up reminder and invoice."""
    
    # Check state machine validity
    if db_job.status not in JOB_VALID_TRANSITIONS or "completed" not in JOB_VALID_TRANSITIONS[db_job.status]:
        return None, f"Cannot complete job with status '{db_job.status}'."
    
    from_status = db_job.status
    db_job.status = "completed"
    db_job.completed_at = _utcnow()
    db_job.completion_notes = completion_notes
    _record_job_activity(
        db,
        organization_id=organization_id,
        job_id=int(db_job.id),
        action="completed",
        from_status=from_status,
        to_status="completed",
        actor_user_id=actor_user_id,
        note=completion_notes,
    )
    db.commit()
    db.refresh(db_job)

    send_job_lifecycle_notification(
        db,
        organization_id=organization_id,
        customer_id=db_job.customer_id,
        job_id=int(db_job.id),
        to_status="completed",
    )
    
    # Dismiss any pending completion reminders for this job (marked_complete reminders)
    completion_reminders = (
        db.query(Reminder)
        .filter(
            Reminder.job_id == db_job.id,
            Reminder.organization_id == organization_id,
            Reminder.status == "pending",
            Reminder.message.like("%Mark%complete%"),
        )
        .all()
    )
    for reminder in completion_reminders:
        reminder.status = "dismissed"
        reminder.updated_at = _utcnow()
    db.commit()
    
    # Auto-create follow-up reminder for feedback/follow-up (due in 2 days)
    follow_up_due = _utcnow() + timedelta(days=2)
    follow_up_reminder = Reminder(
        message=f"Follow up with customer on job #{db_job.id} completion",
        channel="internal",
        status="pending",
        due_at=follow_up_due,
        job_id=db_job.id,
        customer_id=db_job.customer_id,
        organization_id=organization_id,
    )
    db.add(follow_up_reminder)
    db.commit()

    # Auto-create review request reminder (Review Harvester baseline automation).
    create_review_request_reminder(
        db,
        job_id=int(db_job.id),
        customer_id=int(db_job.customer_id),
        organization_id=organization_id,
        days_until_due=1,
    )
    
    # Auto-create invoice from approved estimate if one exists and no invoice yet
    from .invoice import create_invoice_from_estimate
    approved_estimates = (
        db.query(Estimate)
        .filter(
            Estimate.job_id == db_job.id,
            Estimate.organization_id == organization_id,
            Estimate.status == "approved",
        )
        .all()
    )
    if approved_estimates:
        # Use the first approved estimate to create invoice
        invoice, error = create_invoice_from_estimate(db, approved_estimates[0].id, organization_id)
        # Auto-invoice creation failed silently; job completion is not blocked
    
    return db_job, None


def mark_job_on_my_way(
    db: Session,
    db_job: Job,
    organization_id: int,
    actor_user_id: Optional[int] = None,
) -> Tuple[Optional[Job], Optional[str]]:
    from_status = db_job.status
    if not _can_transition(from_status, "on_my_way"):
        return None, f"Cannot mark on_my_way from status '{from_status}'."

    db_job.status = "on_my_way"
    db_job.on_my_way_at = _utcnow()
    _record_job_activity(
        db,
        organization_id=organization_id,
        job_id=int(db_job.id),
        action="on_my_way",
        from_status=from_status,
        to_status="on_my_way",
        actor_user_id=actor_user_id,
    )
    db.commit()
    db.refresh(db_job)

    send_job_lifecycle_notification(
        db,
        organization_id=organization_id,
        customer_id=db_job.customer_id,
        job_id=int(db_job.id),
        to_status="on_my_way",
    )
    return db_job, None


def start_job(
    db: Session,
    db_job: Job,
    organization_id: int,
    actor_user_id: Optional[int] = None,
) -> Tuple[Optional[Job], Optional[str]]:
    from_status = db_job.status
    if not _can_transition(from_status, "in_progress"):
        return None, f"Cannot mark in_progress from status '{from_status}'."

    db_job.status = "in_progress"
    db_job.started_at = _utcnow()
    _record_job_activity(
        db,
        organization_id=organization_id,
        job_id=int(db_job.id),
        action="started",
        from_status=from_status,
        to_status="in_progress",
        actor_user_id=actor_user_id,
    )
    db.commit()
    db.refresh(db_job)

    send_job_lifecycle_notification(
        db,
        organization_id=organization_id,
        customer_id=db_job.customer_id,
        job_id=int(db_job.id),
        to_status="in_progress",
    )
    return db_job, None
