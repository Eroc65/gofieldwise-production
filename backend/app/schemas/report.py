from pydantic import BaseModel


class RevenuePathReportOut(BaseModel):
    organization_id: int
    leads_total: int
    leads_new: int
    leads_contacted: int
    leads_qualified: int
    leads_converted: int
    jobs_total: int
    jobs_dispatched: int
    invoices_total: int
    invoices_unpaid: int
    invoices_overdue: int
    reminders_pending: int
    reminders_overdue: int
    collection_reminders_pending: int


class OperationalDashboardOut(BaseModel):
    organization_id: int
    timestamp: str
    lead_pipeline: dict
    job_status: dict
    invoice_summary: dict
    overdue_invoices: dict
    sla_breaches: dict
    reminders: dict
    revenue_metrics: dict
    action_priorities: dict


class SLABreachEscalationOut(BaseModel):
    organization_id: int
    stale_dispatched_jobs: int
    severe_overdue_invoices: int
    job_sla_alerts_created: int
    invoice_sla_alerts_created: int
    total_alerts_created: int


class DailyDigestOut(BaseModel):
    organization_id: int
    timestamp: str
    summary: dict
    cash_risk: dict
    sla: dict
    pipeline: dict
    weekly_trends: dict
    recommended_actions: list[str]


class OperatorQueueItemOut(BaseModel):
    item_type: str
    entity_id: int
    title: str
    urgency: str
    priority_score: int
    revenue_impact: float | None = None
    due_at: str | None = None
    action: str


class OperatorQueueOut(BaseModel):
    organization_id: int
    timestamp: str
    limit: int
    total_candidates: int
    items: list[OperatorQueueItemOut]


class OperatorQueueAckIn(BaseModel):
    item_type: str
    entity_id: int


class OperatorQueueAckOut(BaseModel):
    organization_id: int
    item_type: str
    entity_id: int
    acknowledged: bool
    already_acknowledged: bool
    acknowledged_at: str


class OperatorQueueUnackIn(BaseModel):
    item_type: str
    entity_id: int


class OperatorQueueUnackOut(BaseModel):
    organization_id: int
    item_type: str
    entity_id: int
    unacknowledged: bool
    already_unacknowledged: bool
    unacknowledged_at: str


class OperatorQueueHistoryEventOut(BaseModel):
    action: str
    item_type: str
    entity_id: int
    timestamp: str


class OperatorQueueHistoryOut(BaseModel):
    organization_id: int
    timestamp: str
    limit: int
    events: list[OperatorQueueHistoryEventOut]
