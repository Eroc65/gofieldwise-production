from fastapi import APIRouter

from . import (
    admin_monitoring,
    auth,
    crm_hub,
    customers,
    estimates,
    external_integrations,
    integrations,
    invoices,
    jobs,
    leads,
    marketing,
    platform,
    protected,
    reminders,
    reports,
    technicians,
)


router = APIRouter()
router.include_router(auth.router, prefix="/api/auth", tags=["auth"])
router.include_router(leads.router, prefix="/api", tags=["leads"])
router.include_router(protected.router, prefix="/api", tags=["protected"])
router.include_router(customers.router, prefix="/api", tags=["customers"])
router.include_router(jobs.router, prefix="/api", tags=["jobs"])
router.include_router(technicians.router, prefix="/api", tags=["technicians"])
router.include_router(reminders.router, prefix="/api", tags=["reminders"])
router.include_router(invoices.router, prefix="/api", tags=["invoices"])
router.include_router(reports.router, prefix="/api", tags=["reports"])
router.include_router(estimates.router, prefix="/api", tags=["estimates"])
router.include_router(marketing.router, prefix="/api", tags=["marketing"])
router.include_router(platform.router, prefix="/api", tags=["platform"])
router.include_router(admin_monitoring.router, prefix="/api", tags=["admin-monitoring"])
router.include_router(external_integrations.router, prefix="/api", tags=["external-integrations"])
router.include_router(integrations.router, tags=["integrations"])
router.include_router(crm_hub.router, tags=["crm-hub"])
