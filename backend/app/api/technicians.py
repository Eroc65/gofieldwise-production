from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..core.db import get_db
from ..crud.technician import create_technician, get_technician, get_technicians, update_technician
from ..models.core import User
from ..schemas.technician import TechnicianCreate, TechnicianOut, TechnicianUpdate

router = APIRouter()


@router.get("/technicians", response_model=List[TechnicianOut])
def list_technicians(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_technicians(db, current_user.organization_id)


@router.post("/technicians", response_model=TechnicianOut, status_code=status.HTTP_201_CREATED)
def create_technician_api(
    technician: TechnicianCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_technician(db, technician.model_dump(), current_user.organization_id)


@router.get("/technicians/{technician_id}", response_model=TechnicianOut)
def get_technician_api(
    technician_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    technician = get_technician(db, technician_id, current_user.organization_id)
    if not technician:
        raise HTTPException(status_code=404, detail="Technician not found")
    return technician


@router.put("/technicians/{technician_id}", response_model=TechnicianOut)
def update_technician_api(
    technician_id: int,
    update: TechnicianUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    technician = get_technician(db, technician_id, current_user.organization_id)
    if not technician:
        raise HTTPException(status_code=404, detail="Technician not found")
    return update_technician(db, technician, update.model_dump(exclude_unset=True))
