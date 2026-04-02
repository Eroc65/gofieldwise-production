from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from ..models.core import Customer, Estimate, Job, JOB_VALID_TRANSITIONS, Reminder, Technician

def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

def get_jobs(db: Session, organization_id: int) -> List[Job]:
    return db.query(Job).filter(Job.organization_id == organization_id).all()

def get_job(db: Session, job_id: int, organization_id: int) -> Optional[Job]:
    return db.query(Job).filter(Job.id == job_id, Job.organization_id == organization_id).first()

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
) -> Tuple[Optional[Job], Optional[str]]:
    technician = (
        db.query(Technician)
        .filter(Technician.id == technician_id, Technician.organization_id == organization_id)
        .first()
    )
    if not technician:
        return None, "Technician not found in your organization"

    conflict = (
        db.query(Job)
        .filter(
            Job.organization_id == organization_id,
            Job.technician_id == technician_id,
            Job.scheduled_time == scheduled_time,
            Job.id != db_job.id,
        )
        .first()
    )
    if conflict:
        return None, "Technician already has a job scheduled at that time"

    db_job.technician_id = technician_id
    db_job.scheduled_time = scheduled_time
    db_job.status = "dispatched"
    db.commit()
    db.refresh(db_job)
    
    # Auto-create completion reminder for technician
    from .reminder import create_job_completion_reminder
    create_job_completion_reminder(db, db_job.id, organization_id, db_job.title)
    
    return db_job, None


def complete_job(
    db: Session,
    db_job: Job,
    organization_id: int,
    completion_notes: Optional[str] = None,
) -> Tuple[Optional[Job], Optional[str]]:
    """Mark a job as completed. Only valid from 'dispatched' status. Auto-creates follow-up reminder and invoice."""
    
    # Check state machine validity
    if db_job.status not in JOB_VALID_TRANSITIONS or "completed" not in JOB_VALID_TRANSITIONS[db_job.status]:
        return None, f"Cannot complete job with status '{db_job.status}'. Must be 'dispatched'."
    
    db_job.status = "completed"
    db_job.completed_at = _utcnow()
    db_job.completion_notes = completion_notes
    db.commit()
    db.refresh(db_job)
    
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
