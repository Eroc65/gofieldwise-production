from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import cast

from ..api.auth import get_current_user
from ..core.db import get_db
from ..crud.report import escalate_sla_breaches
from ..crud.report import acknowledge_operator_queue_item
from ..crud.report import unacknowledge_operator_queue_item
from ..crud.report import get_daily_digest
from ..crud.report import get_lead_conversion_metrics
from ..crud.report import get_growth_control_tower
from ..crud.report import get_operator_queue_ack_history
from ..crud.report import get_operator_queue
from ..crud.report import get_revenue_path_report
from ..crud.report import get_operational_dashboard
from ..models.core import User
from ..schemas.report import DailyDigestOut
from ..schemas.report import LeadConversionMetricsOut
from ..schemas.report import GrowthControlTowerOut
from ..schemas.report import OperatorQueueAckIn
from ..schemas.report import OperatorQueueAckOut
from ..schemas.report import OperatorQueueUnackIn
from ..schemas.report import OperatorQueueHistoryOut
from ..schemas.report import OperatorQueueUnackOut
from ..schemas.report import OperatorQueueOut
from ..schemas.report import RevenuePathReportOut
from ..schemas.report import OperationalDashboardOut
from ..schemas.report import SLABreachEscalationOut

router = APIRouter()


@router.get("/reports/revenue-path", response_model=RevenuePathReportOut)
def revenue_path_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = cast(int, current_user.organization_id)
    return get_revenue_path_report(db, org_id)


@router.get("/reports/lead-conversion", response_model=LeadConversionMetricsOut)
def lead_conversion_metrics(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = cast(int, current_user.organization_id)
    return get_lead_conversion_metrics(db, org_id, days=days)


@router.get("/reports/operational-dashboard", response_model=OperationalDashboardOut)
def operational_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = cast(int, current_user.organization_id)
    return get_operational_dashboard(db, org_id)


@router.post("/reports/sla-breaches/escalate", response_model=SLABreachEscalationOut)
def escalate_sla_breaches_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = cast(int, current_user.organization_id)
    return escalate_sla_breaches(db, org_id)


@router.get("/reports/daily-digest", response_model=DailyDigestOut)
def daily_digest(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = cast(int, current_user.organization_id)
    return get_daily_digest(db, org_id)


@router.get("/reports/operator-queue", response_model=OperatorQueueOut)
def operator_queue(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = cast(int, current_user.organization_id)
    return get_operator_queue(db, org_id, limit=limit)


@router.post("/reports/operator-queue/ack", response_model=OperatorQueueAckOut)
def operator_queue_ack(
    payload: OperatorQueueAckIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = cast(int, current_user.organization_id)
    actor_user_id = cast(int, current_user.id)
    result, error = acknowledge_operator_queue_item(
        db,
        org_id,
        payload.item_type,
        payload.entity_id,
        actor_user_id=actor_user_id,
    )
    if error:
        raise HTTPException(status_code=422, detail=error)
    return result


@router.post("/reports/operator-queue/unack", response_model=OperatorQueueUnackOut)
def operator_queue_unack(
    payload: OperatorQueueUnackIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = cast(int, current_user.organization_id)
    actor_user_id = cast(int, current_user.id)
    result, error = unacknowledge_operator_queue_item(
        db,
        org_id,
        payload.item_type,
        payload.entity_id,
        actor_user_id=actor_user_id,
    )
    if error:
        raise HTTPException(status_code=422, detail=error)
    return result


@router.get("/reports/operator-queue/history", response_model=OperatorQueueHistoryOut)
def operator_queue_history(
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = cast(int, current_user.organization_id)
    return get_operator_queue_ack_history(db, org_id, limit=limit)


@router.get("/reports/growth-control-tower", response_model=GrowthControlTowerOut)
def growth_control_tower(
    days: int = Query(7, ge=1, le=30),
    queue_limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = cast(int, current_user.organization_id)
    return get_growth_control_tower(
        db,
        org_id,
        days=days,
        queue_limit=queue_limit,
    )
