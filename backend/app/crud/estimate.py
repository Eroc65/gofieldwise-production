from typing import Any, List, Optional, Tuple, cast

from sqlalchemy.orm import Session

from ..models.core import Estimate, Job, _utcnow

VALID_ESTIMATE_STATUSES = {"draft", "sent", "approved", "rejected"}


def create_estimate(db: Session, data: dict, organization_id: int) -> Tuple[Optional[Estimate], Optional[str]]:
    job = (
        db.query(Job)
        .filter(Job.id == data["job_id"], Job.organization_id == organization_id)
        .first()
    )
    if not job:
        return None, "Job not found in your organization"

    estimate = Estimate(
        amount=data["amount"],
        description=data.get("description"),
        status="sent",
        issued_at=_utcnow(),
        job_id=job.id,
        organization_id=organization_id,
    )
    db.add(estimate)
    db.commit()
    db.refresh(estimate)
    return estimate, None


def get_estimate(db: Session, estimate_id: int, organization_id: int) -> Optional[Estimate]:
    return (
        db.query(Estimate)
        .filter(Estimate.id == estimate_id, Estimate.organization_id == organization_id)
        .first()
    )


def get_estimates(db: Session, organization_id: int, status: Optional[str] = None) -> List[Estimate]:
    q = db.query(Estimate).filter(Estimate.organization_id == organization_id)
    if status:
        q = q.filter(Estimate.status == status)
    return q.order_by(Estimate.id.desc()).all()


def update_estimate_status(
    db: Session,
    estimate: Estimate,
    new_status: str,
) -> Tuple[Optional[Estimate], Optional[str]]:
    current_status = str(cast(str, estimate.status))
    if new_status not in VALID_ESTIMATE_STATUSES:
        return None, "Invalid status. Must be one of: draft, sent, approved, rejected"
    if current_status == new_status:
        return estimate, None
    if current_status == "approved" and new_status != "approved":
        return None, "Approved estimates are terminal"
    if current_status == "rejected" and new_status != "rejected":
        return None, "Rejected estimates are terminal"

    estimate_obj = cast(Any, estimate)
    estimate_obj.status = new_status
    if new_status == "approved":
        estimate_obj.approved_at = _utcnow()
        estimate_obj.rejected_at = None
        cast(Any, estimate.job).status = "approved"
    elif new_status == "rejected":
        estimate_obj.rejected_at = _utcnow()
        estimate_obj.approved_at = None
        cast(Any, estimate.job).status = "estimate_rejected"
    else:
        estimate_obj.approved_at = None
        estimate_obj.rejected_at = None

    db.commit()
    db.refresh(estimate)
    return estimate, None
