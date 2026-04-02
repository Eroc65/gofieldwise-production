from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..core.db import get_db
from ..crud.lead import (
    book_lead,
    convert_lead,
    create_lead,
    get_lead,
    get_leads,
    qualify_lead,
    transition_lead_status,
    upsert_missed_call_lead,
)
from ..crud.reminder import create_lead_booking_reminder, create_lead_followup_reminder
from ..models.core import Organization, User
from ..schemas.lead import (
    LeadBookInput,
    LeadBookOut,
    LeadConvertOut,
    LeadIntake,
    LeadOut,
    LeadQualificationInput,
    LeadQualificationOut,
    LeadStatusUpdate,
    MissedCallIntake,
    MissedCallRecoveryOut,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Public intake — no auth required.
# org_id routes the lead to the correct organization (e.g. from a web form
# embed or missed-call webhook). In production, harden with a per-org
# webhook token; for now org_id is the routing key.
# ---------------------------------------------------------------------------

@router.post(
    "/leads/intake/{org_id}",
    response_model=LeadOut,
    status_code=status.HTTP_201_CREATED,
    tags=["intake"],
)
def intake(org_id: int, payload: LeadIntake, db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    data = payload.model_dump()
    lead = create_lead(db, data, org_id)
    # Auto-schedule a follow-up reminder so the lead doesn't slip through the cracks.
    create_lead_followup_reminder(db, lead.id, org_id, lead_name=lead.name)
    return lead


@router.post(
    "/leads/intake/missed-call/{org_id}",
    response_model=MissedCallRecoveryOut,
    status_code=status.HTTP_200_OK,
    tags=["intake"],
)
def intake_missed_call(
    org_id: int,
    payload: MissedCallIntake,
    db: Session = Depends(get_db),
):
    """Recover missed calls quickly with dedupe to avoid duplicate lead spam."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    raw_message = payload.raw_message
    if payload.call_sid:
        sid_line = f"Call SID: {payload.call_sid}"
        raw_message = f"{sid_line}\n{raw_message}" if raw_message else sid_line

    lead, created_new = upsert_missed_call_lead(
        db=db,
        organization_id=org_id,
        phone=payload.phone,
        name=payload.name,
        raw_message=raw_message,
    )
    reminder_created = False
    if created_new:
        # Missed calls are high urgency; nudge team immediately.
        create_lead_followup_reminder(db, lead.id, org_id, lead_name=lead.name, hours=0)
        reminder_created = True

    return MissedCallRecoveryOut(
        lead=lead,
        deduplicated=not created_new,
        reminder_created=reminder_created,
    )


# ---------------------------------------------------------------------------
# Authenticated lead management
# ---------------------------------------------------------------------------

@router.get("/leads", response_model=List[LeadOut])
def list_leads(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_leads(db, current_user.organization_id)


@router.get("/leads/{lead_id}", response_model=LeadOut)
def get_lead_api(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lead = get_lead(db, lead_id, current_user.organization_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.patch("/leads/{lead_id}/status", response_model=LeadOut)
def update_lead_status(
    lead_id: int,
    update: LeadStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lead = get_lead(db, lead_id, current_user.organization_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead, error = transition_lead_status(db, lead, update.status)
    if error:
        raise HTTPException(status_code=422, detail=error)
    return lead


@router.post("/leads/{lead_id}/convert", response_model=LeadConvertOut)
def convert_lead_api(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lead = get_lead(db, lead_id, current_user.organization_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    try:
        lead, customer, job = convert_lead(db, lead, current_user.organization_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return LeadConvertOut(lead_id=lead.id, customer_id=customer.id, job_id=job.id)


@router.post("/leads/{lead_id}/qualify", response_model=LeadQualificationOut)
def qualify_lead_api(
    lead_id: int,
    payload: LeadQualificationInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lead = get_lead(db, lead_id, current_user.organization_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead, error = qualify_lead(
        db,
        lead,
        emergency=payload.emergency,
        budget_confirmed=payload.budget_confirmed,
        requested_within_48h=payload.requested_within_48h,
        service_category=payload.service_category,
    )
    if error:
        raise HTTPException(status_code=422, detail=error)

    create_lead_booking_reminder(
        db,
        lead_id=lead.id,
        organization_id=current_user.organization_id,
        lead_name=lead.name,
    )
    return LeadQualificationOut(lead=lead, booking_reminder_created=True)


@router.post("/leads/{lead_id}/book", response_model=LeadBookOut)
def book_lead_api(
    lead_id: int,
    payload: LeadBookInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lead = get_lead(db, lead_id, current_user.organization_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    booked_lead, customer, job, dismissed_count, error = book_lead(
        db,
        lead,
        current_user.organization_id,
        payload.technician_id,
        payload.scheduled_time,
    )
    if error:
        raise HTTPException(status_code=422, detail=error)
    if not booked_lead or not customer or not job:
        raise HTTPException(status_code=500, detail="Lead booking failed unexpectedly")

    return LeadBookOut(
        lead_id=booked_lead.id,
        customer_id=customer.id,
        job_id=job.id,
        job_status=job.status,
        scheduled_time=job.scheduled_time,
        technician_id=job.technician_id,
        booking_reminders_dismissed=dismissed_count,
    )
