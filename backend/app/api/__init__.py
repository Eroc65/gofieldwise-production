from fastapi import APIRouter, Depends

from . import (
    admin_monitoring,
    admin_auth,
    auth,
    billing,
    connect,
    customers,
    estimates,
    external_integrations,
    invoices,
    jobs,
    leads,
    marketing,
    operator,
    platform,
    protected,
    reminders,
    reports,
    technicians,
)
from .auth import require_active_org

# Convenience shorthand used on every business router registration.
_active = [Depends(require_active_org)]

router = APIRouter()

# ── Auth & billing: NO subscription gate (needed during checkout flow) ──────
router.include_router(auth.router, prefix="/api/auth", tags=["auth"])
router.include_router(billing.router, tags=["billing"])
router.include_router(operator.router, prefix="/api", tags=["operator"])
router.include_router(admin_auth.router, prefix="/api", tags=["admin-auth"])

# ── Business routes: require active subscription ─────────────────────────────
router.include_router(leads.router, prefix="/api", tags=["leads"], dependencies=_active)
router.include_router(protected.router, prefix="/api", tags=["protected"], dependencies=_active)
router.include_router(customers.router, prefix="/api", tags=["customers"], dependencies=_active)
router.include_router(jobs.router, prefix="/api", tags=["jobs"], dependencies=_active)
router.include_router(technicians.router, prefix="/api", tags=["technicians"], dependencies=_active)
router.include_router(reminders.router, prefix="/api", tags=["reminders"], dependencies=_active)
router.include_router(invoices.router, prefix="/api", tags=["invoices"], dependencies=_active)
router.include_router(reports.router, prefix="/api", tags=["reports"], dependencies=_active)
router.include_router(estimates.router, prefix="/api", tags=["estimates"], dependencies=_active)
router.include_router(marketing.router, prefix="/api", tags=["marketing"], dependencies=_active)
router.include_router(platform.router, prefix="/api", tags=["platform"], dependencies=_active)
router.include_router(connect.router, prefix="/api", tags=["connect"], dependencies=_active)
router.include_router(admin_monitoring.router, prefix="/api", tags=["admin-monitoring"])
router.include_router(external_integrations.router, prefix="/api", tags=["external-integrations"], dependencies=_active)
