from datetime import timedelta
from typing import cast

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models.core import Customer
from ..models.core import Job
from ..models.core import MarketingCampaign
from ..models.core import MarketingCampaignRecipient
from ..models.core import Reminder
from ..models.core import _utcnow


VALID_KINDS = {"review_harvester", "reactivation"}
VALID_CHANNELS = {"sms", "email", "internal"}


def _default_template(kind: str) -> str:
    if kind == "reactivation":
        return "Hi from FrontDesk Pro. We are offering priority scheduling this week if you need service."
    return "Thanks for choosing us. Would you share a quick review of your recent service?"


def create_campaign(db: Session, payload: dict, organization_id: int) -> MarketingCampaign:
    kind = str(payload.get("kind", "review_harvester")).strip().lower()
    channel = str(payload.get("channel", "sms")).strip().lower()
    if kind not in VALID_KINDS:
        raise HTTPException(status_code=422, detail="Invalid campaign kind")
    if channel not in VALID_CHANNELS:
        raise HTTPException(status_code=422, detail="Invalid campaign channel")

    template = payload.get("template")
    if not template:
        template = _default_template(kind)

    campaign = MarketingCampaign(
        name=payload["name"],
        kind=kind,
        channel=channel,
        template=template,
        lookback_days=int(payload.get("lookback_days", 90)),
        status="draft",
        organization_id=organization_id,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


def list_campaigns(db: Session, organization_id: int) -> list[MarketingCampaign]:
    return (
        db.query(MarketingCampaign)
        .filter(MarketingCampaign.organization_id == organization_id)
        .order_by(MarketingCampaign.created_at.desc(), MarketingCampaign.id.desc())
        .all()
    )


def get_campaign(db: Session, campaign_id: int, organization_id: int) -> MarketingCampaign | None:
    return (
        db.query(MarketingCampaign)
        .filter(
            MarketingCampaign.id == campaign_id,
            MarketingCampaign.organization_id == organization_id,
        )
        .first()
    )


def _review_harvester_customer_ids(db: Session, organization_id: int) -> list[int]:
    rows = (
        db.query(Customer.id)
        .join(Job, Job.customer_id == Customer.id)
        .filter(
            Customer.organization_id == organization_id,
            Job.organization_id == organization_id,
            Job.status == "completed",
        )
        .group_by(Customer.id)
        .all()
    )
    return [int(cast(int, row[0])) for row in rows]


def _reactivation_customer_ids(db: Session, organization_id: int, lookback_days: int) -> list[int]:
    cutoff = _utcnow() - timedelta(days=max(lookback_days, 7))

    rows = (
        db.query(Customer.id)
        .outerjoin(Job, (Job.customer_id == Customer.id) & (Job.organization_id == organization_id))
        .filter(Customer.organization_id == organization_id)
        .group_by(Customer.id)
        .having(func.max(func.coalesce(Job.completed_at, Job.scheduled_time)) < cutoff)
        .all()
    )

    # Include customers with no jobs ever as reactivation targets.
    no_job_rows = (
        db.query(Customer.id)
        .outerjoin(Job, (Job.customer_id == Customer.id) & (Job.organization_id == organization_id))
        .filter(Customer.organization_id == organization_id)
        .group_by(Customer.id)
        .having(func.count(Job.id) == 0)
        .all()
    )

    out = {int(cast(int, row[0])) for row in rows}
    out.update({int(cast(int, row[0])) for row in no_job_rows})
    return sorted(out)


def launch_campaign(db: Session, campaign: MarketingCampaign) -> int:
    campaign_status = str(cast(str, campaign.status))
    if campaign_status != "draft":
        raise HTTPException(status_code=409, detail="Campaign already launched")

    campaign_kind = str(cast(str, campaign.kind))
    if campaign_kind == "review_harvester":
        customer_ids = _review_harvester_customer_ids(db, int(cast(int, campaign.organization_id)))
    else:
        customer_ids = _reactivation_customer_ids(
            db,
            int(cast(int, campaign.organization_id)),
            int(cast(int, campaign.lookback_days)),
        )

    generated = 0
    for customer_id in customer_ids:
        reminder = Reminder(
            message=str(cast(str, campaign.template)),
            channel=str(cast(str, campaign.channel)),
            status="pending",
            due_at=_utcnow(),
            customer_id=customer_id,
            organization_id=int(cast(int, campaign.organization_id)),
        )
        db.add(reminder)
        db.flush()

        recipient = MarketingCampaignRecipient(
            campaign_id=int(cast(int, campaign.id)),
            customer_id=customer_id,
            status="queued",
            reminder_id=int(cast(int, reminder.id)),
            organization_id=int(cast(int, campaign.organization_id)),
        )
        db.add(recipient)
        generated += 1

    setattr(campaign, "status", "launched")
    setattr(campaign, "launched_at", _utcnow())
    db.commit()
    return generated
