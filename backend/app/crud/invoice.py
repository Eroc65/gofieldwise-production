from datetime import timedelta
from typing import Any, List, Optional, Tuple, cast

from sqlalchemy.orm import Session

from ..models.core import Estimate, Invoice, Job, Reminder, _utcnow

VALID_INVOICE_STATUSES = {"unpaid", "paid", "void"}


def create_invoice(db: Session, data: dict, organization_id: int) -> Tuple[Optional[Invoice], Optional[str]]:
    job = (
        db.query(Job)
        .filter(Job.id == data["job_id"], Job.organization_id == organization_id)
        .first()
    )
    if not job:
        return None, "Job not found in your organization"

    due_at = data.get("due_at")
    if due_at is None:
        due_at = _utcnow() + timedelta(days=data.get("due_in_days", 7))

    invoice = Invoice(
        amount=data["amount"],
        status="unpaid",
        issued_at=_utcnow(),
        due_at=due_at,
        job_id=job.id,
        organization_id=organization_id,
    )
    db.add(invoice)
    db.flush()

    # Auto-create a collections reminder tied to this invoice's customer/job.
    reminder = Reminder(
        message=f"Collect payment for invoice #{invoice.id}",
        channel="internal",
        status="pending",
        due_at=due_at,
        job_id=job.id,
        customer_id=job.customer_id,
        organization_id=organization_id,
    )
    db.add(reminder)

    db.commit()
    db.refresh(invoice)
    return invoice, None


def get_invoice(db: Session, invoice_id: int, organization_id: int) -> Optional[Invoice]:
    return (
        db.query(Invoice)
        .filter(Invoice.id == invoice_id, Invoice.organization_id == organization_id)
        .first()
    )


def get_invoices(db: Session, organization_id: int, status: Optional[str] = None) -> List[Invoice]:
    q = db.query(Invoice).filter(Invoice.organization_id == organization_id)
    if status:
        q = q.filter(Invoice.status == status)
    return q.order_by(Invoice.id.desc()).all()


def get_overdue_invoices(db: Session, organization_id: int) -> List[Invoice]:
    now = _utcnow()
    return (
        db.query(Invoice)
        .filter(
            Invoice.organization_id == organization_id,
            Invoice.status == "unpaid",
            Invoice.due_at.isnot(None),
            Invoice.due_at < now,
        )
        .order_by(Invoice.due_at.asc())
        .all()
    )


def update_invoice_status(
    db: Session,
    invoice: Invoice,
    new_status: str,
) -> Tuple[Optional[Invoice], Optional[str]]:
    if new_status not in VALID_INVOICE_STATUSES:
        return None, "Invalid status. Must be one of: unpaid, paid, void"

    invoice_obj = cast(Any, invoice)
    was_status = str(cast(str, invoice.status))
    invoice_marker = f"invoice #{invoice.id}".lower()
    invoice_obj.status = new_status
    if new_status == "paid":
        invoice_obj.paid_at = _utcnow()
        # Stop active collection reminders once payment is received.
        reminders = (
            db.query(Reminder)
            .filter(
                Reminder.organization_id == invoice.organization_id,
                Reminder.job_id == invoice.job_id,
                Reminder.status == "pending",
            )
            .all()
        )
        for reminder in reminders:
            reminder_message = str(cast(str, reminder.message)).lower()
            if invoice_marker not in reminder_message:
                continue
            reminder_obj = cast(Any, reminder)
            reminder_obj.status = "dismissed"
            reminder_obj.updated_at = _utcnow()
    else:
        invoice_obj.paid_at = None
        # If invoice reopens from paid -> unpaid, reactivate its collection reminder.
        if new_status == "unpaid" and was_status == "paid":
            reminders = (
                db.query(Reminder)
                .filter(
                    Reminder.organization_id == invoice.organization_id,
                    Reminder.job_id == invoice.job_id,
                    Reminder.status == "dismissed",
                )
                .all()
            )
            for reminder in reminders:
                reminder_message = str(cast(str, reminder.message)).lower()
                if invoice_marker not in reminder_message:
                    continue
                reminder_obj = cast(Any, reminder)
                reminder_obj.status = "pending"
                reminder_obj.due_at = cast(Any, invoice.due_at) or _utcnow()
                reminder_obj.updated_at = _utcnow()

    db.commit()
    db.refresh(invoice)
    return invoice, None


def create_invoice_from_estimate(
    db: Session,
    estimate_id: int,
    organization_id: int,
    due_in_days: int = 7,
) -> Tuple[Optional[Invoice], Optional[str]]:
    """Auto-create an invoice from an approved estimate."""
    estimate = (
        db.query(Estimate)
        .filter(Estimate.id == estimate_id, Estimate.organization_id == organization_id)
        .first()
    )
    if not estimate:
        return None, "Estimate not found in your organization"
    
    estimate_status = str(cast(str, estimate.status))
    if estimate_status != "approved":
        return None, f"Cannot create invoice from estimate with status '{estimate_status}'. Must be 'approved'."
    
    # Check if an invoice already exists for this estimate's job
    existing_invoice = (
        db.query(Invoice)
        .filter(Invoice.job_id == estimate.job_id, Invoice.organization_id == organization_id)
        .first()
    )
    if existing_invoice:
        return None, "An invoice already exists for this job"
    
    # Create invoice from estimate
    due_at = _utcnow() + timedelta(days=due_in_days)
    invoice = Invoice(
        amount=estimate.amount,
        status="unpaid",
        issued_at=_utcnow(),
        due_at=due_at,
        job_id=estimate.job_id,
        organization_id=organization_id,
    )
    db.add(invoice)
    db.flush()
    
    # Auto-create collection reminder
    job = db.query(Job).filter(Job.id == estimate.job_id).first()
    if job is None:
        return None, "Job not found for estimate"
    reminder = Reminder(
        message=f"Collect payment for invoice #{invoice.id}",
        channel="internal",
        status="pending",
        due_at=due_at,
        job_id=estimate.job_id,
        customer_id=job.customer_id,
        organization_id=organization_id,
    )
    db.add(reminder)
    db.commit()
    db.refresh(invoice)
    return invoice, None


def escalate_payment_reminders(
    db: Session,
    organization_id: int,
) -> Tuple[int, int, int, int]:
    """
    Check all unpaid invoices and escalate payment reminders based on days overdue.
    
    Escalation tiers:
    - initial: send on due date (stage: none → initial)
    - first_overdue: 3 days past due (stage: any → first_overdue)
    - second_overdue: 7 days past due (stage: any → second_overdue)
    - final: 14 days past due (stage: any → final)
    
    Returns: (initial_count, first_overdue_count, second_overdue_count, final_count)
    """
    now = _utcnow()
    
    initial_count = 0
    first_overdue_count = 0
    second_overdue_count = 0
    final_count = 0
    
    # Get unpaid invoices that haven't reached terminal stage
    unpaid_invoices = (
        db.query(Invoice)
        .filter(
            Invoice.organization_id == organization_id,
            Invoice.status == "unpaid",
        )
        .all()
    )
    
    for invoice in unpaid_invoices:
        due_at = cast(Any, invoice.due_at)
        if not due_at:
            continue
        
        days_overdue = (now - cast(Any, due_at)).days
        
        # Skip if not yet due (future dates)
        if days_overdue < 0:
            continue
        
        # Determine target stage based on days overdue (jump to the appropriate stage)
        if days_overdue >= 14:
            target_stage = "final"
            count_ref = "final"
        elif days_overdue >= 7:
            target_stage = "second_overdue"
            count_ref = "second_overdue"
        elif days_overdue >= 3:
            target_stage = "first_overdue"
            count_ref = "first_overdue"
        elif days_overdue >= 0:
            target_stage = "initial"
            count_ref = "initial"
        else:
            continue
        
        # Only escalate if we haven't already created a reminder for this stage
        if str(cast(str, invoice.payment_reminder_stage)) == target_stage:
            # Already at this stage, skip
            continue
        
        # Create escalation reminder
        if target_stage == "initial":
            message = f"Invoice #{invoice.id} is due today – payment needed"
            initial_count += 1
        elif target_stage == "first_overdue":
            message = f"Invoice #{invoice.id} is now 3+ days overdue – please collect payment"
            first_overdue_count += 1
        elif target_stage == "second_overdue":
            message = f"Invoice #{invoice.id} is 7+ days overdue – URGENT: collect payment immediately"
            second_overdue_count += 1
        else:  # final
            message = f"Invoice #{invoice.id} is 14+ days overdue – FINAL NOTICE: immediate payment required"
            final_count += 1
        
        # Create the escalation reminder
        escalation_reminder = Reminder(
            message=message,
            channel="internal",
            status="pending",
            due_at=now,
            job_id=invoice.job_id,
            customer_id=invoice.job.customer_id,
            organization_id=organization_id,
        )
        db.add(escalation_reminder)
        
        # Update invoice stage
        cast(Any, invoice).payment_reminder_stage = target_stage
    
    db.commit()
    return initial_count, first_overdue_count, second_overdue_count, final_count
