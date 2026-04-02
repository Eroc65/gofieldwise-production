from datetime import timedelta
from typing import cast

from sqlalchemy import func

from ..models.core import Invoice, Job, Lead, Reminder, User, _utcnow


OPERATOR_QUEUE_ITEM_TYPES = {
    "invoice_collection",
    "job_completion",
    "reminder_followup",
    "lead_followup",
}


def _queue_ack_message(item_type: str, entity_id: int) -> str:
    return f"Queue ack: {item_type}#{entity_id}"


def _queue_unack_message(item_type: str, entity_id: int) -> str:
    return f"Queue unack: {item_type}#{entity_id}"


def _queue_parse_event(message: str) -> tuple[str, tuple[str, int]] | tuple[None, None]:
    if message.startswith("Queue ack: "):
        action = "ack"
        payload = message[len("Queue ack: "):]
    elif message.startswith("Queue unack: "):
        action = "unack"
        payload = message[len("Queue unack: "):]
    else:
        return None, None

    if "#" not in payload:
        return None, None
    item_type, entity_str = payload.split("#", 1)
    if item_type not in OPERATOR_QUEUE_ITEM_TYPES:
        return None, None
    try:
        entity_id = int(entity_str)
    except ValueError:
        return None, None
    return action, (item_type, entity_id)


def _queue_suppression_state(db, organization_id: int) -> dict[tuple[str, int], bool]:
    state: dict[tuple[str, int], bool] = {}
    events = (
        db.query(Reminder)
        .filter(
            Reminder.organization_id == organization_id,
            Reminder.message.like("Queue %:%"),
        )
        .order_by(Reminder.created_at.asc(), Reminder.id.asc())
        .all()
    )
    for evt in events:
        action, key = _queue_parse_event(evt.message)
        if not action or not key:
            continue
        state[key] = action == "ack"
    return state


def _queue_actor_user_id(reminder: Reminder) -> int | None:
    raw_val = cast(str | None, reminder.last_dispatch_error)
    if raw_val is None:
        return None
    raw = str(raw_val)
    prefix = "actor_user_id="
    if not raw.startswith(prefix):
        return None
    try:
        return int(raw[len(prefix):])
    except ValueError:
        return None


def get_revenue_path_report(db, organization_id: int) -> dict:
    now = _utcnow()

    leads_total = db.query(Lead).filter(Lead.organization_id == organization_id).count()
    leads_new = db.query(Lead).filter(Lead.organization_id == organization_id, Lead.status == "new").count()
    leads_contacted = db.query(Lead).filter(Lead.organization_id == organization_id, Lead.status == "contacted").count()
    leads_qualified = (
        db.query(Lead)
        .filter(Lead.organization_id == organization_id, Lead.qualified_at.isnot(None))
        .count()
    )
    leads_converted = db.query(Lead).filter(Lead.organization_id == organization_id, Lead.status == "converted").count()

    jobs_total = db.query(Job).filter(Job.organization_id == organization_id).count()
    jobs_dispatched = db.query(Job).filter(Job.organization_id == organization_id, Job.status == "dispatched").count()

    invoices_total = db.query(Invoice).filter(Invoice.organization_id == organization_id).count()
    invoices_unpaid = db.query(Invoice).filter(Invoice.organization_id == organization_id, Invoice.status == "unpaid").count()
    invoices_overdue = (
        db.query(Invoice)
        .filter(
            Invoice.organization_id == organization_id,
            Invoice.status == "unpaid",
            Invoice.due_at.isnot(None),
            Invoice.due_at < now,
        )
        .count()
    )

    reminders_pending = (
        db.query(Reminder)
        .filter(Reminder.organization_id == organization_id, Reminder.status == "pending")
        .count()
    )
    reminders_overdue = (
        db.query(Reminder)
        .filter(
            Reminder.organization_id == organization_id,
            Reminder.status == "pending",
            Reminder.due_at <= now,
        )
        .count()
    )
    collection_reminders_pending = (
        db.query(Reminder)
        .filter(
            Reminder.organization_id == organization_id,
            Reminder.status == "pending",
            Reminder.message.like("Collect payment for invoice%"),
        )
        .count()
    )

    return {
        "organization_id": organization_id,
        "leads_total": leads_total,
        "leads_new": leads_new,
        "leads_contacted": leads_contacted,
        "leads_qualified": leads_qualified,
        "leads_converted": leads_converted,
        "jobs_total": jobs_total,
        "jobs_dispatched": jobs_dispatched,
        "invoices_total": invoices_total,
        "invoices_unpaid": invoices_unpaid,
        "invoices_overdue": invoices_overdue,
        "reminders_pending": reminders_pending,
        "reminders_overdue": reminders_overdue,
        "collection_reminders_pending": collection_reminders_pending,
    }


def get_operational_dashboard(db, organization_id: int) -> dict:
    """Comprehensive operational dashboard with pipeline visibility and urgent metrics."""
    now = _utcnow()
    
    # Lead pipeline
    leads_new = db.query(Lead).filter(Lead.organization_id == organization_id, Lead.status == "new").count()
    leads_contacted = db.query(Lead).filter(Lead.organization_id == organization_id, Lead.status == "contacted").count()
    leads_qualified = db.query(Lead).filter(Lead.organization_id == organization_id, Lead.qualified_at.isnot(None)).count()
    leads_converted = db.query(Lead).filter(Lead.organization_id == organization_id, Lead.status == "converted").count()
    leads_dismissed = db.query(Lead).filter(Lead.organization_id == organization_id, Lead.status == "dismissed").count()
    
    # Job breakdown
    jobs_pending = db.query(Job).filter(Job.organization_id == organization_id, Job.status == "pending").count()
    jobs_approved = db.query(Job).filter(Job.organization_id == organization_id, Job.status == "approved").count()
    jobs_dispatched = db.query(Job).filter(Job.organization_id == organization_id, Job.status == "dispatched").count()
    jobs_completed = db.query(Job).filter(Job.organization_id == organization_id, Job.status == "completed").count()
    
    # Invoice breakdown
    invoices_unpaid = db.query(Invoice).filter(Invoice.organization_id == organization_id, Invoice.status == "unpaid").count()
    invoices_paid = db.query(Invoice).filter(Invoice.organization_id == organization_id, Invoice.status == "paid").count()
    invoices_void = db.query(Invoice).filter(Invoice.organization_id == organization_id, Invoice.status == "void").count()
    
    # Overdue invoices by escalation level
    invoices_initial_due = db.query(Invoice).filter(
        Invoice.organization_id == organization_id,
        Invoice.status == "unpaid",
        Invoice.payment_reminder_stage == "initial",
    ).count()
    invoices_3days_overdue = db.query(Invoice).filter(
        Invoice.organization_id == organization_id,
        Invoice.status == "unpaid",
        Invoice.payment_reminder_stage == "first_overdue",
    ).count()
    invoices_7days_overdue = db.query(Invoice).filter(
        Invoice.organization_id == organization_id,
        Invoice.status == "unpaid",
        Invoice.payment_reminder_stage == "second_overdue",
    ).count()
    invoices_14days_overdue = db.query(Invoice).filter(
        Invoice.organization_id == organization_id,
        Invoice.status == "unpaid",
        Invoice.payment_reminder_stage == "final",
    ).count()
    stale_dispatched_jobs = db.query(Job).filter(
        Job.organization_id == organization_id,
        Job.status == "dispatched",
        Job.scheduled_time.isnot(None),
        Job.scheduled_time <= (now - timedelta(days=2)),
    ).count()
    severe_overdue_invoices = db.query(Invoice).filter(
        Invoice.organization_id == organization_id,
        Invoice.status == "unpaid",
        Invoice.due_at.isnot(None),
        Invoice.due_at <= (now - timedelta(days=14)),
    ).count()
    
    # Urgent reminders
    reminders_pending_total = db.query(Reminder).filter(
        Reminder.organization_id == organization_id,
        Reminder.status == "pending",
    ).count()
    reminders_overdue_total = db.query(Reminder).filter(
        Reminder.organization_id == organization_id,
        Reminder.status == "pending",
        Reminder.due_at <= now,
    ).count()
    reminders_due_today = db.query(Reminder).filter(
        Reminder.organization_id == organization_id,
        Reminder.status == "pending",
        func.date(Reminder.due_at) == now.date().isoformat(),
    ).count()
    
    # Collection reminders
    collection_reminders_pending = db.query(Reminder).filter(
        Reminder.organization_id == organization_id,
        Reminder.status == "pending",
        Reminder.message.like("Collect payment for invoice%"),
    ).count()
    
    collection_reminders_overdue = db.query(Reminder).filter(
        Reminder.organization_id == organization_id,
        Reminder.status == "pending",
        Reminder.due_at <= now,
        Reminder.message.like("Collect payment for invoice%"),
    ).count()
    sla_job_alerts_pending = db.query(Reminder).filter(
        Reminder.organization_id == organization_id,
        Reminder.status == "pending",
        Reminder.message.like("SLA breach: dispatched job%"),
    ).count()
    sla_invoice_alerts_pending = db.query(Reminder).filter(
        Reminder.organization_id == organization_id,
        Reminder.status == "pending",
        Reminder.message.like("SLA breach: invoice%"),
    ).count()
    
    # Estimated revenue metrics
    total_revenue_invoiced = db.query(func.sum(Invoice.amount)).filter(
        Invoice.organization_id == organization_id,
        Invoice.status.in_(["paid", "unpaid"]),
    ).scalar() or 0.0
    
    total_revenue_paid = db.query(func.sum(Invoice.amount)).filter(
        Invoice.organization_id == organization_id,
        Invoice.status == "paid",
    ).scalar() or 0.0
    
    outstanding_revenue = db.query(func.sum(Invoice.amount)).filter(
        Invoice.organization_id == organization_id,
        Invoice.status == "unpaid",
    ).scalar() or 0.0
    
    return {
        "organization_id": organization_id,
        "timestamp": now.isoformat(),
        "lead_pipeline": {
            "new": leads_new,
            "contacted": leads_contacted,
            "qualified": leads_qualified,
            "converted": leads_converted,
            "dismissed": leads_dismissed,
            "total": leads_new + leads_contacted + leads_qualified + leads_converted + leads_dismissed,
        },
        "job_status": {
            "pending": jobs_pending,
            "approved": jobs_approved,
            "dispatched": jobs_dispatched,
            "completed": jobs_completed,
            "total": jobs_pending + jobs_approved + jobs_dispatched + jobs_completed,
        },
        "invoice_summary": {
            "unpaid": invoices_unpaid,
            "paid": invoices_paid,
            "void": invoices_void,
            "total": invoices_unpaid + invoices_paid + invoices_void,
        },
        "overdue_invoices": {
            "due_today": invoices_initial_due,
            "3_days_overdue": invoices_3days_overdue,
            "7_days_overdue": invoices_7days_overdue,
            "14_plus_days_overdue": invoices_14days_overdue,
            "total_overdue": invoices_3days_overdue + invoices_7days_overdue + invoices_14days_overdue,
        },
        "sla_breaches": {
            "stale_dispatched_jobs": stale_dispatched_jobs,
            "severe_overdue_invoices": severe_overdue_invoices,
            "pending_job_alerts": sla_job_alerts_pending,
            "pending_invoice_alerts": sla_invoice_alerts_pending,
            "pending_total_alerts": sla_job_alerts_pending + sla_invoice_alerts_pending,
        },
        "reminders": {
            "pending_total": reminders_pending_total,
            "pending_overdue": reminders_overdue_total,
            "collection_pending": collection_reminders_pending,
            "collection_overdue": collection_reminders_overdue,
        },
        "revenue_metrics": {
            "total_invoiced": round(total_revenue_invoiced, 2),
            "total_paid": round(total_revenue_paid, 2),
            "outstanding": round(outstanding_revenue, 2),
            "collection_rate_percent": round((total_revenue_paid / total_revenue_invoiced * 100) if total_revenue_invoiced > 0 else 0, 1),
        },
        "action_priorities": {
            "urgent_now": reminders_overdue_total + invoices_14days_overdue + collection_reminders_overdue,
            "today": reminders_due_today + invoices_initial_due,
            "this_week": jobs_dispatched + invoices_3days_overdue + invoices_7days_overdue,
            "total_open_actions": (
                reminders_pending_total + invoices_unpaid + jobs_dispatched
            ),
        },
    }


def escalate_sla_breaches(
    db,
    organization_id: int,
    job_breach_days: int = 2,
    invoice_breach_days: int = 14,
) -> dict:
    """Create internal reminders for SLA-breached jobs and invoices (idempotent)."""
    now = _utcnow()
    stale_job_cutoff = now - timedelta(days=job_breach_days)
    stale_invoice_cutoff = now - timedelta(days=invoice_breach_days)

    stale_jobs = (
        db.query(Job)
        .filter(
            Job.organization_id == organization_id,
            Job.status == "dispatched",
            Job.scheduled_time.isnot(None),
            Job.scheduled_time <= stale_job_cutoff,
        )
        .all()
    )
    severe_overdue_invoices = (
        db.query(Invoice)
        .filter(
            Invoice.organization_id == organization_id,
            Invoice.status == "unpaid",
            Invoice.due_at.isnot(None),
            Invoice.due_at <= stale_invoice_cutoff,
        )
        .all()
    )

    created_job_alerts = 0
    created_invoice_alerts = 0

    for job in stale_jobs:
        message = f"SLA breach: dispatched job #{job.id} is stale"
        existing = (
            db.query(Reminder)
            .filter(
                Reminder.organization_id == organization_id,
                Reminder.job_id == job.id,
                Reminder.status == "pending",
                Reminder.message == message,
            )
            .first()
        )
        if existing:
            continue

        reminder = Reminder(
            message=message,
            channel="internal",
            status="pending",
            due_at=now,
            job_id=job.id,
            customer_id=job.customer_id,
            organization_id=organization_id,
        )
        db.add(reminder)
        created_job_alerts += 1

    for invoice in severe_overdue_invoices:
        message = f"SLA breach: invoice #{invoice.id} is 14+ days overdue"
        existing = (
            db.query(Reminder)
            .filter(
                Reminder.organization_id == organization_id,
                Reminder.job_id == invoice.job_id,
                Reminder.status == "pending",
                Reminder.message == message,
            )
            .first()
        )
        if existing:
            continue

        reminder = Reminder(
            message=message,
            channel="internal",
            status="pending",
            due_at=now,
            job_id=invoice.job_id,
            customer_id=invoice.job.customer_id if invoice.job else None,
            organization_id=organization_id,
        )
        db.add(reminder)
        created_invoice_alerts += 1

    db.commit()

    return {
        "organization_id": organization_id,
        "stale_dispatched_jobs": len(stale_jobs),
        "severe_overdue_invoices": len(severe_overdue_invoices),
        "job_sla_alerts_created": created_job_alerts,
        "invoice_sla_alerts_created": created_invoice_alerts,
        "total_alerts_created": created_job_alerts + created_invoice_alerts,
    }


def get_daily_digest(db, organization_id: int) -> dict:
    """Operator-focused morning snapshot of urgent work and cash-risk."""
    now = _utcnow()

    reminders_overdue = db.query(Reminder).filter(
        Reminder.organization_id == organization_id,
        Reminder.status == "pending",
        Reminder.due_at <= now,
    ).count()
    reminders_due_today = db.query(Reminder).filter(
        Reminder.organization_id == organization_id,
        Reminder.status == "pending",
        func.date(Reminder.due_at) == now.date().isoformat(),
    ).count()
    collection_overdue = db.query(Reminder).filter(
        Reminder.organization_id == organization_id,
        Reminder.status == "pending",
        Reminder.due_at <= now,
        Reminder.message.like("Collect payment for invoice%"),
    ).count()

    unpaid_invoices = db.query(Invoice).filter(
        Invoice.organization_id == organization_id,
        Invoice.status == "unpaid",
    ).count()
    severe_overdue_invoices = db.query(Invoice).filter(
        Invoice.organization_id == organization_id,
        Invoice.status == "unpaid",
        Invoice.due_at.isnot(None),
        Invoice.due_at <= (now - timedelta(days=14)),
    ).count()
    outstanding_amount = db.query(func.sum(Invoice.amount)).filter(
        Invoice.organization_id == organization_id,
        Invoice.status == "unpaid",
    ).scalar() or 0.0

    stale_dispatched_jobs = db.query(Job).filter(
        Job.organization_id == organization_id,
        Job.status == "dispatched",
        Job.scheduled_time.isnot(None),
        Job.scheduled_time <= (now - timedelta(days=2)),
    ).count()
    dispatched_jobs = db.query(Job).filter(
        Job.organization_id == organization_id,
        Job.status == "dispatched",
    ).count()
    new_leads = db.query(Lead).filter(
        Lead.organization_id == organization_id,
        Lead.status == "new",
    ).count()

    pending_sla_alerts = db.query(Reminder).filter(
        Reminder.organization_id == organization_id,
        Reminder.status == "pending",
        Reminder.message.like("SLA breach:%"),
    ).count()
    weekly_cutoff = now - timedelta(days=7)
    new_leads_last_7d = db.query(Lead).filter(
        Lead.organization_id == organization_id,
        Lead.created_at >= weekly_cutoff,
    ).count()
    jobs_completed_last_7d = db.query(Job).filter(
        Job.organization_id == organization_id,
        Job.status == "completed",
        Job.completed_at.isnot(None),
        Job.completed_at >= weekly_cutoff,
    ).count()
    payments_collected_last_7d_count = db.query(Invoice).filter(
        Invoice.organization_id == organization_id,
        Invoice.status == "paid",
        Invoice.paid_at.isnot(None),
        Invoice.paid_at >= weekly_cutoff,
    ).count()
    payments_collected_last_7d_amount = db.query(func.sum(Invoice.amount)).filter(
        Invoice.organization_id == organization_id,
        Invoice.status == "paid",
        Invoice.paid_at.isnot(None),
        Invoice.paid_at >= weekly_cutoff,
    ).scalar() or 0.0

    urgent_now = reminders_overdue + severe_overdue_invoices + collection_overdue
    today_actions = reminders_due_today + new_leads
    this_week_actions = dispatched_jobs + stale_dispatched_jobs

    recommendations: list[str] = []
    if severe_overdue_invoices > 0:
        recommendations.append("Call customers with 14+ day overdue invoices first.")
    if stale_dispatched_jobs > 0:
        recommendations.append("Close or reschedule stale dispatched jobs before noon.")
    if new_leads > 0:
        recommendations.append("Contact all new leads today to avoid missed revenue.")
    if not recommendations:
        recommendations.append("No urgent actions right now. Keep follow-ups current.")

    return {
        "organization_id": organization_id,
        "timestamp": now.isoformat(),
        "summary": {
            "urgent_now": urgent_now,
            "today_actions": today_actions,
            "this_week_actions": this_week_actions,
        },
        "cash_risk": {
            "unpaid_invoices": unpaid_invoices,
            "severe_overdue_invoices": severe_overdue_invoices,
            "collection_overdue_reminders": collection_overdue,
            "outstanding_amount": round(outstanding_amount, 2),
        },
        "sla": {
            "stale_dispatched_jobs": stale_dispatched_jobs,
            "pending_sla_alerts": pending_sla_alerts,
        },
        "pipeline": {
            "new_leads": new_leads,
            "dispatched_jobs": dispatched_jobs,
        },
        "weekly_trends": {
            "new_leads_last_7d": new_leads_last_7d,
            "jobs_completed_last_7d": jobs_completed_last_7d,
            "payments_collected_last_7d_count": payments_collected_last_7d_count,
            "payments_collected_last_7d_amount": round(payments_collected_last_7d_amount, 2),
        },
        "recommended_actions": recommendations,
    }


def get_operator_queue(db, organization_id: int, limit: int = 10) -> dict:
    """Return top actionable items ranked by urgency and revenue impact."""
    now = _utcnow()
    capped_limit = max(1, min(limit, 50))
    items: list[dict] = []
    suppression_state = _queue_suppression_state(db, organization_id)

    severe_overdue_invoices = (
        db.query(Invoice)
        .filter(
            Invoice.organization_id == organization_id,
            Invoice.status == "unpaid",
            Invoice.due_at.isnot(None),
            Invoice.due_at <= (now - timedelta(days=14)),
        )
        .all()
    )
    for invoice in severe_overdue_invoices:
        if suppression_state.get(("invoice_collection", invoice.id), False):
            continue
        days_overdue = max(0, (now - invoice.due_at).days)
        revenue_impact = float(invoice.amount or 0.0)
        priority_score = 100 + days_overdue + min(int(revenue_impact / 20), 60)
        items.append(
            {
                "item_type": "invoice_collection",
                "entity_id": invoice.id,
                "title": f"Collect invoice #{invoice.id}",
                "urgency": "critical",
                "priority_score": priority_score,
                "revenue_impact": round(revenue_impact, 2),
                "due_at": invoice.due_at.isoformat() if invoice.due_at else None,
                "action": "Call customer and collect payment today.",
            }
        )

    stale_jobs = (
        db.query(Job)
        .filter(
            Job.organization_id == organization_id,
            Job.status == "dispatched",
            Job.scheduled_time.isnot(None),
            Job.scheduled_time <= (now - timedelta(days=2)),
        )
        .all()
    )
    for job in stale_jobs:
        if suppression_state.get(("job_completion", job.id), False):
            continue
        days_stale = max(0, (now - job.scheduled_time).days)
        priority_score = 80 + (days_stale * 2)
        items.append(
            {
                "item_type": "job_completion",
                "entity_id": job.id,
                "title": f"Close dispatched job #{job.id}",
                "urgency": "high",
                "priority_score": priority_score,
                "revenue_impact": None,
                "due_at": job.scheduled_time.isoformat() if job.scheduled_time else None,
                "action": "Confirm outcome and mark complete or reschedule.",
            }
        )

    overdue_reminders = (
        db.query(Reminder)
        .filter(
            Reminder.organization_id == organization_id,
            Reminder.status == "pending",
            Reminder.due_at <= now,
        )
        .all()
    )
    for reminder in overdue_reminders:
        if suppression_state.get(("reminder_followup", reminder.id), False):
            continue
        days_late = max(0, (now - reminder.due_at).days)
        is_collection = reminder.message.startswith("Collect payment for invoice")
        priority_score = 70 + days_late + (15 if is_collection else 0)
        items.append(
            {
                "item_type": "reminder_followup",
                "entity_id": reminder.id,
                "title": reminder.message,
                "urgency": "high" if is_collection else "medium",
                "priority_score": priority_score,
                "revenue_impact": None,
                "due_at": reminder.due_at.isoformat(),
                "action": "Complete or dismiss this overdue reminder.",
            }
        )

    new_leads = (
        db.query(Lead)
        .filter(Lead.organization_id == organization_id, Lead.status == "new")
        .all()
    )
    for lead in new_leads:
        if suppression_state.get(("lead_followup", lead.id), False):
            continue
        age_hours = max(0, int((now - lead.created_at).total_seconds() / 3600))
        priority_score = 60 + min(age_hours, 24)
        items.append(
            {
                "item_type": "lead_followup",
                "entity_id": lead.id,
                "title": f"Follow up with lead #{lead.id}",
                "urgency": "medium",
                "priority_score": priority_score,
                "revenue_impact": None,
                "due_at": lead.created_at.isoformat(),
                "action": "Call or text lead and book the job.",
            }
        )

    items.sort(key=lambda i: (-i["priority_score"], i["due_at"] or "9999-12-31T23:59:59"))

    return {
        "organization_id": organization_id,
        "timestamp": now.isoformat(),
        "limit": capped_limit,
        "total_candidates": len(items),
        "items": items[:capped_limit],
    }


def acknowledge_operator_queue_item(
    db,
    organization_id: int,
    item_type: str,
    entity_id: int,
    actor_user_id: int | None = None,
) -> tuple[dict | None, str | None]:
    """Acknowledge a queue item without mutating underlying domain entities."""
    if item_type not in OPERATOR_QUEUE_ITEM_TYPES:
        valid = ", ".join(sorted(OPERATOR_QUEUE_ITEM_TYPES))
        return None, f"Invalid item_type '{item_type}'. Must be one of: {valid}"

    now = _utcnow()
    suppression_state = _queue_suppression_state(db, organization_id)
    if suppression_state.get((item_type, entity_id), False):
        existing = (
            db.query(Reminder)
            .filter(
                Reminder.organization_id == organization_id,
                Reminder.message == _queue_ack_message(item_type, entity_id),
            )
            .order_by(Reminder.created_at.desc(), Reminder.id.desc())
            .first()
        )
        return {
            "organization_id": organization_id,
            "item_type": item_type,
            "entity_id": entity_id,
            "acknowledged": True,
            "already_acknowledged": True,
            "acknowledged_at": existing.created_at.isoformat() if existing.created_at else now.isoformat(),
        }, None

    ack = Reminder(
        message=_queue_ack_message(item_type, entity_id),
        channel="internal",
        status="sent",
        due_at=now,
        sent_at=now,
        last_dispatch_error=(f"actor_user_id={actor_user_id}" if actor_user_id is not None else None),
        organization_id=organization_id,
    )
    db.add(ack)
    db.commit()
    db.refresh(ack)

    return {
        "organization_id": organization_id,
        "item_type": item_type,
        "entity_id": entity_id,
        "acknowledged": True,
        "already_acknowledged": False,
        "acknowledged_at": ack.created_at.isoformat(),
    }, None


def unacknowledge_operator_queue_item(
    db,
    organization_id: int,
    item_type: str,
    entity_id: int,
    actor_user_id: int | None = None,
) -> tuple[dict | None, str | None]:
    """Add queue unack marker so the item can appear again."""
    if item_type not in OPERATOR_QUEUE_ITEM_TYPES:
        valid = ", ".join(sorted(OPERATOR_QUEUE_ITEM_TYPES))
        return None, f"Invalid item_type '{item_type}'. Must be one of: {valid}"

    now = _utcnow()
    suppression_state = _queue_suppression_state(db, organization_id)
    if not suppression_state.get((item_type, entity_id), False):
        return {
            "organization_id": organization_id,
            "item_type": item_type,
            "entity_id": entity_id,
            "unacknowledged": True,
            "already_unacknowledged": True,
            "unacknowledged_at": now.isoformat(),
        }, None

    unack = Reminder(
        message=_queue_unack_message(item_type, entity_id),
        channel="internal",
        status="sent",
        due_at=now,
        sent_at=now,
        last_dispatch_error=(f"actor_user_id={actor_user_id}" if actor_user_id is not None else None),
        organization_id=organization_id,
    )
    db.add(unack)
    db.commit()

    return {
        "organization_id": organization_id,
        "item_type": item_type,
        "entity_id": entity_id,
        "unacknowledged": True,
        "already_unacknowledged": False,
        "unacknowledged_at": now.isoformat(),
    }, None


def get_operator_queue_ack_history(db, organization_id: int, limit: int = 100) -> dict:
    """Return ack/unack audit events for operator queue suppression actions."""
    now = _utcnow()
    capped_limit = max(1, min(limit, 200))
    events = (
        db.query(Reminder)
        .filter(
            Reminder.organization_id == organization_id,
            Reminder.message.like("Queue %:%"),
        )
        .order_by(Reminder.created_at.desc(), Reminder.id.desc())
        .limit(capped_limit)
        .all()
    )

    out: list[dict] = []
    actor_ids: set[int] = set()
    parsed: list[tuple[Reminder, str, str, int]] = []
    for evt in events:
        action, key = _queue_parse_event(evt.message)
        if not action or not key:
            continue
        item_type, entity_id = key
        parsed.append((evt, action, item_type, entity_id))
        actor_id = _queue_actor_user_id(evt)
        if actor_id is not None:
            actor_ids.add(actor_id)

    actor_email_by_id: dict[int, str] = {}
    if actor_ids:
        users = (
            db.query(User)
            .filter(
                User.organization_id == organization_id,
                User.id.in_(actor_ids),
            )
            .all()
        )
        actor_email_by_id = {u.id: u.email for u in users}

    for evt, action, item_type, entity_id in parsed:
        actor_id = _queue_actor_user_id(evt)
        created_at = evt.created_at
        out.append(
            {
                "action": action,
                "item_type": item_type,
                "entity_id": entity_id,
                "timestamp": created_at.isoformat() if created_at is not None else now.isoformat(),
                "actor_user_id": actor_id,
                "actor_email": actor_email_by_id.get(actor_id) if actor_id is not None else None,
            }
        )

    return {
        "organization_id": organization_id,
        "timestamp": now.isoformat(),
        "limit": capped_limit,
        "events": out,
    }
