from typing import List, Optional, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..core.db import get_db
from ..crud.reminder import (
    create_reminder,
    dispatch_due_reminders,
    get_overdue_reminders,
    get_reminder,
    get_reminders,
    update_reminder_status,
)
from ..models.core import REMINDER_CHANNELS, REMINDER_STATUSES, User
from ..schemas.reminder import (
    ReminderCreate,
    ReminderOut,
    ReminderRunRequest,
    ReminderRunResult,
    ReminderStatusUpdate,
)

router = APIRouter()


@router.post("/reminders", response_model=ReminderOut, status_code=status.HTTP_201_CREATED)
def create_reminder_endpoint(
    payload: ReminderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.channel not in REMINDER_CHANNELS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid channel '{payload.channel}'. Must be one of: {', '.join(REMINDER_CHANNELS)}.",
        )
    data = payload.model_dump()
    org_id = int(cast(int, current_user.organization_id))
    return create_reminder(db, data, org_id)


@router.get("/reminders/overdue", response_model=List[ReminderOut])
def list_overdue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = int(cast(int, current_user.organization_id))
    return get_overdue_reminders(db, org_id)


@router.get("/reminders", response_model=List[ReminderOut])
def list_reminders(
    status: Optional[str] = Query(None),
    lead_id: Optional[int] = Query(None),
    job_id: Optional[int] = Query(None),
    customer_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = int(cast(int, current_user.organization_id))
    return get_reminders(
        db,
        organization_id=org_id,
        status=status,
        lead_id=lead_id,
        job_id=job_id,
        customer_id=customer_id,
    )


@router.get("/reminders/{reminder_id}", response_model=ReminderOut)
def get_reminder_endpoint(
    reminder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = int(cast(int, current_user.organization_id))
    reminder = get_reminder(db, reminder_id, org_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return reminder


@router.patch("/reminders/{reminder_id}/status", response_model=ReminderOut)
def update_status(
    reminder_id: int,
    update: ReminderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = int(cast(int, current_user.organization_id))
    reminder = get_reminder(db, reminder_id, org_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    reminder, error = update_reminder_status(db, reminder, update.status)
    if error:
        raise HTTPException(status_code=422, detail=error)
    return reminder


@router.post("/reminders/run-due", response_model=ReminderRunResult)
def run_due_reminders(
    payload: ReminderRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    limit = min(max(payload.limit, 1), 500)
    org_id = int(cast(int, current_user.organization_id))
    return dispatch_due_reminders(
        db,
        organization_id=org_id,
        limit=limit,
        dry_run=payload.dry_run,
    )
