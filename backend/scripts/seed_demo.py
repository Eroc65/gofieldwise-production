import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../app')))
from core.db import SessionLocal, engine
from models.core import Organization, Customer, Job, Technician

def seed_demo():
    db = SessionLocal()
    # Create demo org
    org = Organization(name="Demo Org")
    db.add(org)
    db.commit()
    db.refresh(org)
    # Add customers
    customers = [Customer(name=f"Customer {i}", email=f"customer{i}@demo.com", phone="555-0000", organization_id=org.id) for i in range(1, 4)]
    db.add_all(customers)
    db.commit()
    # Add technicians
    techs = [Technician(name=f"Tech {i}", organization_id=org.id) for i in range(1, 3)]
    db.add_all(techs)
    db.commit()
    # Add jobs
    jobs = [Job(title=f"Job {i}", description="Demo job", organization_id=org.id, customer_id=customers[0].id, technician_id=techs[0].id) for i in range(1, 3)]
    db.add_all(jobs)
    db.commit()
    print("Demo data seeded.")

if __name__ == "__main__":
    seed_demo()
