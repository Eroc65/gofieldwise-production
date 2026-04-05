from typing import List, Optional, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..core.db import get_db
from ..crud.estimate import create_estimate, get_estimate, get_estimates, update_estimate_status
from ..models.core import User
from ..schemas.estimate import EstimateCreate, EstimateOut, EstimateStatusUpdate

router = APIRouter()


@router.post("/estimates", response_model=EstimateOut, status_code=status.HTTP_201_CREATED)
def create_estimate_endpoint(
    payload: EstimateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = int(cast(int, current_user.organization_id))
    estimate, error = create_estimate(db, payload.model_dump(), org_id)
    if error:
        raise HTTPException(status_code=422, detail=error)
    return estimate


@router.get("/estimates", response_model=List[EstimateOut])
def list_estimates(
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = int(cast(int, current_user.organization_id))
    return get_estimates(db, org_id, status=status)


@router.get("/estimates/{estimate_id}", response_model=EstimateOut)
def get_estimate_endpoint(
    estimate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = int(cast(int, current_user.organization_id))
    estimate = get_estimate(db, estimate_id, org_id)
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    return estimate


@router.patch("/estimates/{estimate_id}/status", response_model=EstimateOut)
def update_estimate_status_endpoint(
    estimate_id: int,
    payload: EstimateStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = int(cast(int, current_user.organization_id))
    estimate = get_estimate(db, estimate_id, org_id)
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")

    updated, error = update_estimate_status(db, estimate, payload.status)
    if error:
        raise HTTPException(status_code=422, detail=error)
    return updated
