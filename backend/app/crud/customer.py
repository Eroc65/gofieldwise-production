from sqlalchemy.orm import Session
from ..models.core import Customer
from typing import List, Optional

def get_customers(db: Session, organization_id: int) -> List[Customer]:
    return db.query(Customer).filter(Customer.organization_id == organization_id).all()

def get_customer(db: Session, customer_id: int, organization_id: int) -> Optional[Customer]:
    return db.query(Customer).filter(Customer.id == customer_id, Customer.organization_id == organization_id).first()

def create_customer(db: Session, customer: dict, organization_id: int) -> Customer:
    db_customer = Customer(**customer, organization_id=organization_id)
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer

def update_customer(db: Session, db_customer: Customer, updates: dict) -> Customer:
    for key, value in updates.items():
        setattr(db_customer, key, value)
    db.commit()
    db.refresh(db_customer)
    return db_customer
