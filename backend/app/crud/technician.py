from sqlalchemy.orm import Session
from ..models.core import Technician
from typing import List, Optional

def get_technicians(db: Session, organization_id: int) -> List[Technician]:
    return db.query(Technician).filter(Technician.organization_id == organization_id).all()

def get_technician(db: Session, technician_id: int, organization_id: int) -> Optional[Technician]:
    return db.query(Technician).filter(Technician.id == technician_id, Technician.organization_id == organization_id).first()

def create_technician(db: Session, technician: dict, organization_id: int) -> Technician:
    db_technician = Technician(**technician, organization_id=organization_id)
    db.add(db_technician)
    db.commit()
    db.refresh(db_technician)
    return db_technician

def update_technician(db: Session, db_technician: Technician, updates: dict) -> Technician:
    for key, value in updates.items():
        setattr(db_technician, key, value)
    db.commit()
    db.refresh(db_technician)
    return db_technician
