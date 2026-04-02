from datetime import timedelta
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from ..models.core import Customer, Job, Lead, LEAD_VALID_TRANSITIONS, _utcnow


def create_lead(db: Session, data: dict, organization_id: int) -> Lead:
    lead = Lead(**data, organization_id=organization_id)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def upsert_missed_call_lead(
    db: Session,
    organization_id: int,
    phone: str,
    name: Optional[str] = None,
    raw_message: Optional[str] = None,
    dedupe_window_minutes: int = 30,
) -> Tuple[Lead, bool]:
    """Create a missed-call lead or reuse a very recent open one.
    Returns (lead, created_new)."""
    window_start = _utcnow() - timedelta(minutes=dedupe_window_minutes)
    existing = (
        db.query(Lead)
        .filter(
            Lead.organization_id == organization_id,
            Lead.phone == phone,
            Lead.status.in_(["new", "contacted", "qualified"]),
            Lead.created_at >= window_start,
        )
        .order_by(Lead.created_at.desc())
        .first()
    )
    if existing:
        if raw_message:
            prior = existing.raw_message or ""
            existing.raw_message = (prior + "\n" + raw_message).strip() if prior else raw_message
        if name and not existing.name:
            existing.name = name
        existing.updated_at = _utcnow()
        db.commit()
        db.refresh(existing)
        return existing, False

    lead = Lead(
        name=name,
        phone=phone,
        source="missed_call",
        raw_message=raw_message,
        status="new",
        organization_id=organization_id,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead, True


def get_lead(db: Session, lead_id: int, organization_id: int) -> Optional[Lead]:
    return (
        db.query(Lead)
        .filter(Lead.id == lead_id, Lead.organization_id == organization_id)
        .first()
    )


def get_leads(db: Session, organization_id: int) -> List[Lead]:
    return (
        db.query(Lead)
        .filter(Lead.organization_id == organization_id)
        .order_by(Lead.created_at.desc())
        .all()
    )


def transition_lead_status(
    db: Session, lead: Lead, new_status: str
) -> Tuple[Lead, Optional[str]]:
    """Apply a status transition. Returns (lead, error_message).
    error_message is None on success."""
    allowed = LEAD_VALID_TRANSITIONS.get(lead.status, set())
    if new_status not in allowed:
        valid = sorted(allowed) if allowed else []
        msg = (
            f"Cannot move lead from '{lead.status}' to '{new_status}'. "
            f"Valid next statuses: {valid or 'none (terminal state)'}."
        )
        return lead, msg
    lead.status = new_status
    lead.updated_at = _utcnow()
    db.commit()
    db.refresh(lead)
    return lead, None


def _compute_lead_priority_score(
    lead: Lead,
    emergency: bool,
    budget_confirmed: bool,
    requested_within_48h: bool,
    service_category: Optional[str],
) -> int:
    score = 0
    if lead.phone:
        score += 20
    if lead.email:
        score += 10

    source_weights = {
        "missed_call": 30,
        "web_form": 20,
        "sms": 20,
        "manual": 10,
    }
    score += source_weights.get(lead.source, 10)

    if emergency:
        score += 25
    if requested_within_48h:
        score += 10
    if budget_confirmed:
        score += 10
    if service_category:
        score += 5

    return max(0, min(100, score))


def qualify_lead(
    db: Session,
    lead: Lead,
    emergency: bool = False,
    budget_confirmed: bool = False,
    requested_within_48h: bool = False,
    service_category: Optional[str] = None,
) -> Tuple[Lead, Optional[str]]:
    if lead.status in ("converted", "dismissed"):
        return lead, f"Lead in status '{lead.status}' cannot be qualified."

    score = _compute_lead_priority_score(
        lead,
        emergency=emergency,
        budget_confirmed=budget_confirmed,
        requested_within_48h=requested_within_48h,
        service_category=service_category,
    )

    lead.status = "qualified"
    lead.priority_score = score
    lead.qualified_at = _utcnow()
    summary = (
        f"Qualified lead (score={score}, emergency={emergency}, "
        f"budget_confirmed={budget_confirmed}, within_48h={requested_within_48h}, "
        f"category={service_category or 'unspecified'})"
    )
    lead.notes = (f"{lead.notes}\n{summary}".strip() if lead.notes else summary)
    lead.updated_at = _utcnow()
    db.commit()
    db.refresh(lead)
    return lead, None


def convert_lead(
    db: Session, lead: Lead, organization_id: int
) -> Tuple[Lead, Customer, Job]:
    """Promote a qualified lead to a Customer + Job.
    Raises ValueError on bad state or missing contact info.
    Finds existing customer by phone within org to avoid duplicates."""
    if lead.status == "converted":
        raise ValueError("Lead is already converted.")
    if lead.status not in ("new", "contacted", "qualified"):
        raise ValueError(f"Lead in status '{lead.status}' cannot be converted.")
    if not lead.name and not lead.phone:
        raise ValueError("Lead must have at least a name or phone number to convert.")

    # Find or create customer
    customer: Optional[Customer] = None
    if lead.phone:
        customer = (
            db.query(Customer)
            .filter(
                Customer.phone == lead.phone,
                Customer.organization_id == organization_id,
            )
            .first()
        )
    if customer is None:
        customer = Customer(
            name=lead.name or "Unknown",
            phone=lead.phone,
            email=lead.email,
            organization_id=organization_id,
        )
        db.add(customer)
        db.flush()

    # Derive job title from raw_message or name
    job_title = f"New request from {customer.name}"
    if lead.raw_message:
        job_title = (lead.raw_message[:72].strip().split("\n")[0]) or job_title

    job = Job(
        title=job_title,
        description=lead.raw_message,
        status="pending",
        organization_id=organization_id,
        customer_id=customer.id,
    )
    db.add(job)
    db.flush()

    lead.status = "converted"
    lead.customer_id = customer.id
    lead.job_id = job.id
    lead.updated_at = _utcnow()
    db.commit()
    db.refresh(lead)
    return lead, customer, job


def book_lead(
    db: Session,
    lead: Lead,
    organization_id: int,
    technician_id: int,
    scheduled_time,
) -> Tuple[Optional[Lead], Optional[Customer], Optional[Job], int, Optional[str]]:
    """Book a qualified lead into a dispatched job and clear booking reminders."""
    if lead.status not in ("qualified", "converted"):
        return None, None, None, 0, f"Lead in status '{lead.status}' cannot be booked."

    if lead.status == "converted":
        if not lead.customer_id or not lead.job_id:
            return None, None, None, 0, "Converted lead is missing customer/job references."
        customer = (
            db.query(Customer)
            .filter(
                Customer.id == lead.customer_id,
                Customer.organization_id == organization_id,
            )
            .first()
        )
        job = (
            db.query(Job)
            .filter(Job.id == lead.job_id, Job.organization_id == organization_id)
            .first()
        )
        if not customer or not job:
            return None, None, None, 0, "Converted lead references missing records."
    else:
        try:
            lead, customer, job = convert_lead(db, lead, organization_id)
        except ValueError as exc:
            return None, None, None, 0, str(exc)

    from .job import dispatch_job

    dispatched, dispatch_error = dispatch_job(
        db,
        job,
        organization_id,
        technician_id,
        scheduled_time,
    )
    if dispatch_error:
        return None, None, None, 0, dispatch_error

    from ..models.core import Reminder
    booking_reminders = (
        db.query(Reminder)
        .filter(
            Reminder.organization_id == organization_id,
            Reminder.lead_id == lead.id,
            Reminder.status == "pending",
            Reminder.message.like("Book job with%"),
        )
        .all()
    )
    dismissed = 0
    for reminder in booking_reminders:
        reminder.status = "dismissed"
        reminder.updated_at = _utcnow()
        dismissed += 1
    if dismissed > 0:
        db.commit()

    db.refresh(lead)
    db.refresh(dispatched)
    return lead, customer, dispatched, dismissed, None
