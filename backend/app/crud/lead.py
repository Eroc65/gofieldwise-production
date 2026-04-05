from datetime import timedelta
from typing import Any, List, Optional, Tuple, cast

from sqlalchemy.orm import Session

from ..models.core import Customer, Job, Lead, LeadActivity, LEAD_VALID_TRANSITIONS, _utcnow


def _as_opt_str(value: object) -> Optional[str]:
    if value is None:
        return None
    text = str(value)
    return text if text != "" else None


def _as_opt_int(value: object) -> Optional[int]:
    if value is None:
        return None
    return int(cast(int, value))


def _record_lead_activity(
    db: Session,
    *,
    lead: Lead,
    action: str,
    from_status: Optional[str],
    to_status: str,
    note: Optional[str] = None,
    actor_user_id: Optional[int] = None,
) -> None:
    event = LeadActivity(
        action=action,
        from_status=from_status,
        to_status=to_status,
        note=note,
        actor_user_id=actor_user_id,
        lead_id=int(cast(int, lead.id)),
        organization_id=int(cast(int, lead.organization_id)),
    )
    db.add(event)


def create_lead(db: Session, data: dict, organization_id: int) -> Lead:
    lead = Lead(**data, organization_id=organization_id)
    db.add(lead)
    db.flush()
    _record_lead_activity(
        db,
        lead=lead,
        action="created",
        from_status=None,
        to_status=str(cast(str, lead.status)),
        note="Lead created via intake.",
    )
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
        existing_obj = cast(Any, existing)
        existing_raw_message = _as_opt_str(existing.raw_message)
        existing_name = _as_opt_str(existing.name)
        if raw_message:
            prior = existing_raw_message or ""
            existing_obj.raw_message = (prior + "\n" + raw_message).strip() if prior else raw_message
        if name and not existing_name:
            existing_obj.name = name
        existing_obj.updated_at = _utcnow()
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
    db.flush()
    _record_lead_activity(
        db,
        lead=lead,
        action="created",
        from_status=None,
        to_status="new",
        note="Lead created via missed-call intake.",
    )
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
    db: Session, lead: Lead, new_status: str, actor_user_id: Optional[int] = None
) -> Tuple[Lead, Optional[str]]:
    """Apply a status transition. Returns (lead, error_message).
    error_message is None on success."""
    current_status = str(cast(str, lead.status))
    allowed = LEAD_VALID_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        valid = sorted(allowed) if allowed else []
        msg = (
            f"Cannot move lead from '{current_status}' to '{new_status}'. "
            f"Valid next statuses: {valid or 'none (terminal state)'}."
        )
        return lead, msg
    lead_obj = cast(Any, lead)
    lead_obj.status = new_status
    lead_obj.updated_at = _utcnow()
    _record_lead_activity(
        db,
        lead=lead,
        action="status_updated",
        from_status=current_status,
        to_status=new_status,
        actor_user_id=actor_user_id,
    )
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
    lead_phone = _as_opt_str(lead.phone)
    lead_email = _as_opt_str(lead.email)
    lead_source = str(cast(str, lead.source))
    if lead_phone:
        score += 20
    if lead_email:
        score += 10

    source_weights = {
        "missed_call": 30,
        "web_form": 20,
        "sms": 20,
        "manual": 10,
    }
    score += source_weights.get(lead_source, 10)

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
    actor_user_id: Optional[int] = None,
) -> Tuple[Lead, Optional[str]]:
    current_status = str(cast(str, lead.status))
    if current_status in ("converted", "dismissed"):
        return lead, f"Lead in status '{current_status}' cannot be qualified."

    score = _compute_lead_priority_score(
        lead,
        emergency=emergency,
        budget_confirmed=budget_confirmed,
        requested_within_48h=requested_within_48h,
        service_category=service_category,
    )

    lead_obj = cast(Any, lead)
    from_status = str(cast(str, lead.status))
    lead_obj.status = "qualified"
    lead_obj.priority_score = score
    lead_obj.qualified_at = _utcnow()
    summary = (
        f"Qualified lead (score={score}, emergency={emergency}, "
        f"budget_confirmed={budget_confirmed}, within_48h={requested_within_48h}, "
        f"category={service_category or 'unspecified'})"
    )
    existing_notes = _as_opt_str(lead.notes)
    lead_obj.notes = (f"{existing_notes}\n{summary}".strip() if existing_notes else summary)
    lead_obj.updated_at = _utcnow()
    _record_lead_activity(
        db,
        lead=lead,
        action="qualified",
        from_status=from_status,
        to_status="qualified",
        note=summary,
        actor_user_id=actor_user_id,
    )
    db.commit()
    db.refresh(lead)
    return lead, None


def convert_lead(
    db: Session, lead: Lead, organization_id: int, actor_user_id: Optional[int] = None
) -> Tuple[Lead, Customer, Job]:
    """Promote a qualified lead to a Customer + Job.
    Raises ValueError on bad state or missing contact info.
    Finds existing customer by phone within org to avoid duplicates."""
    current_status = str(cast(str, lead.status))
    lead_name = _as_opt_str(lead.name)
    lead_phone = _as_opt_str(lead.phone)
    lead_email = _as_opt_str(lead.email)
    lead_raw_message = _as_opt_str(lead.raw_message)

    if current_status == "converted":
        raise ValueError("Lead is already converted.")
    if current_status not in ("new", "contacted", "qualified"):
        raise ValueError(f"Lead in status '{current_status}' cannot be converted.")
    if not lead_name and not lead_phone:
        raise ValueError("Lead must have at least a name or phone number to convert.")

    # Find or create customer
    customer: Optional[Customer] = None
    if lead_phone:
        customer = (
            db.query(Customer)
            .filter(
                Customer.phone == lead_phone,
                Customer.organization_id == organization_id,
            )
            .first()
        )
    if customer is None:
        customer = Customer(
            name=lead_name or "Unknown",
            phone=lead_phone,
            email=lead_email,
            organization_id=organization_id,
        )
        db.add(customer)
        db.flush()

    # Derive job title from raw_message or name
    job_title = f"New request from {customer.name}"
    if lead_raw_message:
        job_title = (lead_raw_message[:72].strip().split("\n")[0]) or job_title

    job = Job(
        title=job_title,
        description=lead_raw_message,
        status="pending",
        organization_id=organization_id,
        customer_id=customer.id,
    )
    db.add(job)
    db.flush()

    lead_obj = cast(Any, lead)
    from_status = str(cast(str, lead.status))
    lead_obj.status = "converted"
    lead_obj.customer_id = customer.id
    lead_obj.job_id = job.id
    lead_obj.updated_at = _utcnow()
    _record_lead_activity(
        db,
        lead=lead,
        action="converted",
        from_status=from_status,
        to_status="converted",
        note=f"Created customer #{customer.id} and job #{job.id}.",
        actor_user_id=actor_user_id,
    )
    db.commit()
    db.refresh(lead)
    return lead, customer, job


def book_lead(
    db: Session,
    lead: Lead,
    organization_id: int,
    technician_id: int,
    scheduled_time,
    actor_user_id: Optional[int] = None,
) -> Tuple[Optional[Lead], Optional[Customer], Optional[Job], int, Optional[str]]:
    """Book a qualified lead into a dispatched job and clear booking reminders."""
    current_status = str(cast(str, lead.status))
    if current_status not in ("qualified", "converted"):
        return None, None, None, 0, f"Lead in status '{current_status}' cannot be booked."

    if current_status == "converted":
        lead_customer_id = _as_opt_int(lead.customer_id)
        lead_job_id = _as_opt_int(lead.job_id)
        if lead_customer_id is None or lead_job_id is None:
            return None, None, None, 0, "Converted lead is missing customer/job references."
        customer = (
            db.query(Customer)
            .filter(
                Customer.id == lead_customer_id,
                Customer.organization_id == organization_id,
            )
            .first()
        )
        job = (
            db.query(Job)
            .filter(Job.id == lead_job_id, Job.organization_id == organization_id)
            .first()
        )
        if not customer or not job:
            return None, None, None, 0, "Converted lead references missing records."
    else:
        try:
            lead, customer, job = convert_lead(db, lead, organization_id, actor_user_id=actor_user_id)
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
        reminder_obj = cast(Any, reminder)
        reminder_obj.status = "dismissed"
        reminder_obj.updated_at = _utcnow()
        dismissed += 1
    if dismissed > 0:
        db.commit()

    if dispatched is None:
        return None, None, None, dismissed, "Lead booking failed unexpectedly."

    dispatched_id = int(cast(int, dispatched.id))
    _record_lead_activity(
        db,
        lead=lead,
        action="booked",
        from_status="converted",
        to_status="converted",
        note=f"Booked as job #{dispatched_id} with technician #{technician_id}.",
        actor_user_id=actor_user_id,
    )
    db.commit()

    db.refresh(lead)
    db.refresh(dispatched)
    return lead, customer, dispatched, dismissed, None


def list_lead_activities(db: Session, lead_id: int, organization_id: int) -> List[LeadActivity]:
    return (
        db.query(LeadActivity)
        .filter(
            LeadActivity.lead_id == lead_id,
            LeadActivity.organization_id == organization_id,
        )
        .order_by(LeadActivity.created_at.desc(), LeadActivity.id.desc())
        .all()
    )
