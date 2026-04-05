from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..models.core import Reminder


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def send_job_lifecycle_notification(
    db: Session,
    *,
    organization_id: int,
    customer_id: int | None,
    job_id: int,
    to_status: str,
) -> None:
    """Queue a lightweight internal notification for lifecycle transitions."""
    reminder = Reminder(
        message=f"Job #{job_id} moved to {to_status.replace('_', ' ')}",
        channel="internal",
        status="pending",
        due_at=_utcnow(),
        job_id=job_id,
        customer_id=customer_id,
        organization_id=organization_id,
    )
    db.add(reminder)
    db.commit()
