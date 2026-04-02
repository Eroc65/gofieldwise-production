from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..core.db import get_db
from ..crud.invoice import (
    create_invoice,
    escalate_payment_reminders,
    get_invoice,
    get_invoices,
    get_overdue_invoices,
    update_invoice_status,
)
from ..models.core import User
from ..schemas.invoice import InvoiceCreate, InvoiceOut, InvoiceStatusUpdate

router = APIRouter()


class PaymentEscalationResult(BaseModel):
    initial_reminders_created: int
    first_overdue_reminders_created: int
    second_overdue_reminders_created: int
    final_reminders_created: int
    total_escalations: int


@router.post("/invoices", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def create_invoice_endpoint(
    payload: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice, error = create_invoice(db, payload.model_dump(), current_user.organization_id)
    if error:
        raise HTTPException(status_code=422, detail=error)
    return invoice


@router.get("/invoices", response_model=List[InvoiceOut])
def list_invoices(
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_invoices(db, current_user.organization_id, status=status)


@router.get("/invoices/overdue", response_model=List[InvoiceOut])
def list_overdue_invoices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_overdue_invoices(db, current_user.organization_id)


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice_endpoint(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = get_invoice(db, invoice_id, current_user.organization_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.patch("/invoices/{invoice_id}/status", response_model=InvoiceOut)
def update_invoice_status_endpoint(
    invoice_id: int,
    payload: InvoiceStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = get_invoice(db, invoice_id, current_user.organization_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    updated, error = update_invoice_status(db, invoice, payload.status)
    if error:
        raise HTTPException(status_code=422, detail=error)
    return updated


@router.post("/invoices/escalate-payments", response_model=PaymentEscalationResult)
def escalate_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check all unpaid invoices and escalate payment reminders based on days overdue."""
    initial, first, second, final = escalate_payment_reminders(db, current_user.organization_id)
    return PaymentEscalationResult(
        initial_reminders_created=initial,
        first_overdue_reminders_created=first,
        second_overdue_reminders_created=second,
        final_reminders_created=final,
        total_escalations=initial + first + second + final,
    )
