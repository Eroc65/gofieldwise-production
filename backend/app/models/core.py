from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..core.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Organization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    users = relationship("User", back_populates="organization")
    customers = relationship("Customer", back_populates="organization")
    jobs = relationship("Job", back_populates="organization")
    technicians = relationship("Technician", back_populates="organization")
    estimates = relationship("Estimate", back_populates="organization")
    invoices = relationship("Invoice", back_populates="organization")
    reminders = relationship("Reminder", back_populates="organization")
    notes = relationship("Note", back_populates="organization")
    leads = relationship("Lead", back_populates="organization")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    organization = relationship("Organization", back_populates="users")

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, index=True)
    phone = Column(String)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    organization = relationship("Organization", back_populates="customers")
    jobs = relationship("Job", back_populates="customer")
    notes = relationship("Note", back_populates="customer")
    reminders = relationship("Reminder", back_populates="customer")

JOB_VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"approved", "estimate_rejected"},
    "approved": {"dispatched"},
    "estimate_rejected": {"pending"},
    "dispatched": {"completed"},
    "completed": set(),
}


class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    status = Column(String, default="pending")
    scheduled_time = Column(DateTime)
    completed_at = Column(DateTime)
    completion_notes = Column(Text)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    technician_id = Column(Integer, ForeignKey("technicians.id"))
    organization = relationship("Organization", back_populates="jobs")
    customer = relationship("Customer", back_populates="jobs")
    technician = relationship("Technician", back_populates="jobs")
    estimates = relationship("Estimate", back_populates="job")
    invoices = relationship("Invoice", back_populates="job")
    reminders = relationship("Reminder", back_populates="job")
    notes = relationship("Note", back_populates="job")

class Technician(Base):
    __tablename__ = "technicians"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    availability_start_hour_utc = Column(Integer, nullable=False, default=8)
    availability_end_hour_utc = Column(Integer, nullable=False, default=19)
    availability_weekdays = Column(String, nullable=False, default="0,1,2,3,4")
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    organization = relationship("Organization", back_populates="technicians")
    jobs = relationship("Job", back_populates="technician")

class Estimate(Base):
    __tablename__ = "estimates"
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    description = Column(Text)
    status = Column(String, nullable=False, default="draft")
    issued_at = Column(DateTime, default=_utcnow, nullable=False)
    approved_at = Column(DateTime)
    rejected_at = Column(DateTime)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    organization = relationship("Organization", back_populates="estimates")
    job = relationship("Job", back_populates="estimates")

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    status = Column(String, default="unpaid")
    issued_at = Column(DateTime, default=_utcnow, nullable=False)
    due_at = Column(DateTime, index=True)
    paid_at = Column(DateTime)
    payment_reminder_stage = Column(String, default="none")  # none | initial | first_overdue | second_overdue | final
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    organization = relationship("Organization", back_populates="invoices")
    job = relationship("Job", back_populates="invoices")

REMINDER_STATUSES = ("pending", "sent", "dismissed")
REMINDER_CHANNELS = ("sms", "email", "call", "internal")


class Reminder(Base):
    __tablename__ = "reminders"
    id = Column(Integer, primary_key=True, index=True)
    message = Column(Text, nullable=False)
    channel = Column(String, nullable=False, default="internal")  # sms | email | call | internal
    status = Column(String, nullable=False, default="pending")    # pending | sent | dismissed
    due_at = Column(DateTime, nullable=False, index=True)          # when the follow-up is due
    sent_at = Column(DateTime)                                     # set when status → sent
    dispatch_attempts = Column(Integer, nullable=False, default=0)
    last_dispatch_error = Column(Text)
    # Optional context links — a reminder may be for a lead, job, or standalone
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)
    organization = relationship("Organization", back_populates="reminders")
    job = relationship("Job", back_populates="reminders")
    lead = relationship("Lead", back_populates="reminders")
    customer = relationship("Customer", back_populates="reminders")

class Note(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    customer_id = Column(Integer, ForeignKey("customers.id"))
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    organization = relationship("Organization", back_populates="notes")
    job = relationship("Job", back_populates="notes")
    customer = relationship("Customer", back_populates="notes")


# ---------------------------------------------------------------------------
# Lead — inbound contact before it becomes a customer/job
# ---------------------------------------------------------------------------

LEAD_VALID_TRANSITIONS: dict[str, set[str]] = {
    "new": {"contacted", "qualified", "dismissed"},
    "contacted": {"qualified", "dismissed"},
    "qualified": {"converted", "dismissed"},
    "converted": set(),
    "dismissed": set(),
}


class Lead(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    phone = Column(String, index=True)
    email = Column(String)
    source = Column(String, nullable=False, default="manual")  # web_form | missed_call | sms | manual
    status = Column(String, nullable=False, default="new")     # new | contacted | qualified | converted | dismissed
    raw_message = Column(Text)   # voicemail transcript, form body, SMS text, etc.
    notes = Column(Text)
    priority_score = Column(Integer)  # 0-100 score used for qualification ranking
    qualified_at = Column(DateTime)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)
    organization = relationship("Organization", back_populates="leads")
    reminders = relationship("Reminder", back_populates="lead")
