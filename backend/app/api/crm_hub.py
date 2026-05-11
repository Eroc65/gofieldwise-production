"""
CRM Integration Hub API endpoints.
Orchestrates onboarding, intake capture, and handoff routing.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from typing import List

from ..core.db import get_db
from .auth import get_current_user
from ..models.core import Organization, User
from ..models.crm_hub import (
    CRMConfiguration, IntakeCapture, CRMHandoff,
    CRMProvider, IntegrationMode, IntakeType
)
from ..schemas.crm_hub import (
    CRMConfigCreateRequest, CRMConfigResponse, IntakeCaptureRequest, 
    IntakeCaptureResponse, TestLeadRequest, HandoffResponse, 
    OnboardingStepResponse, HubStatusResponse, ApproveConfigRequest,
    AvailableCRMResponse, AvailableCRMsResponse
)
from ..services.crm_hub import get_hub, IntakeProcessor
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/crm-hub", tags=["crm_hub"])


# ============================================================================
# HELPERS
# ============================================================================

def get_org_from_user(user: User, db: Session) -> Organization:
    """Get organization from current user."""
    org = db.query(Organization).filter(
        Organization.id == user.organization_id
    ).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


# ============================================================================
# PROVIDER MANAGEMENT
# ============================================================================

@router.get("/providers", response_model=AvailableCRMsResponse)
def list_available_providers():
    """List all available CRM providers."""
    providers = [
        AvailableCRMResponse(
            provider="housecall_pro",
            name="Housecall Pro",
            supported_modes=["native_api", "zapier"],
            required_config_fields=["api_key"],
            status="active",
            fallback_available=True,
            documentation_url="https://housecallpro.com/api"
        ),
        AvailableCRMResponse(
            provider="servicetitan",
            name="ServiceTitan",
            supported_modes=["oauth", "zapier"],
            required_config_fields=["access_token", "tenant_id", "app_key"],
            status="active",
            fallback_available=True,
            documentation_url="https://servicetitan.com/api"
        ),
        AvailableCRMResponse(
            provider="jobber",
            name="Jobber",
            supported_modes=["oauth", "webhook"],
            required_config_fields=["access_token"],
            status="active",
            fallback_available=True,
            documentation_url="https://getjobber.com/api"
        ),
        AvailableCRMResponse(
            provider="google_calendar",
            name="Google Calendar",
            supported_modes=["oauth"],
            required_config_fields=["access_token", "calendar_id"],
            status="active",
            fallback_available=False,
            documentation_url="https://developers.google.com/calendar"
        ),
        AvailableCRMResponse(
            provider="google_business_profile",
            name="Google Business Profile",
            supported_modes=["oauth"],
            required_config_fields=["access_token", "location_id"],
            status="beta",
            fallback_available=False,
            documentation_url="https://developers.google.com/business"
        ),
        AvailableCRMResponse(
            provider="zapier",
            name="Zapier (Universal)",
            supported_modes=["webhook"],
            required_config_fields=["webhook_url"],
            status="active",
            fallback_available=False,
            documentation_url="https://zapier.com"
        ),
        AvailableCRMResponse(
            provider="manual",
            name="Manual Handoff",
            supported_modes=["manual"],
            required_config_fields=[],
            status="active",
            fallback_available=False,
            documentation_url=None
        ),
    ]
    return AvailableCRMsResponse(providers=providers)


# ============================================================================
# CRM CONFIGURATION
# ============================================================================

@router.post("/configs", response_model=CRMConfigResponse, status_code=201)
def create_crm_config(
    req: CRMConfigCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create new CRM integration config."""
    org = get_org_from_user(current_user, db)
    hub = get_hub(db)
    
    config = hub.create_crm_config(
        org_id=org.id,
        crm_provider=CRMProvider[req.crm_provider.upper().replace("-", "_")],
        integration_mode=IntegrationMode[req.integration_mode.upper()],
        name=req.name,
        config_data=req.config_data,
        field_mapping=req.field_mapping,
    )
    
    if not config:
        raise HTTPException(status_code=400, detail="Failed to create config")
    
    return CRMConfigResponse.from_orm(config)


@router.get("/configs", response_model=List[CRMConfigResponse])
def list_crm_configs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all CRM configs for organization."""
    org = get_org_from_user(current_user, db)
    hub = get_hub(db)
    
    configs = hub.list_crm_configs(org.id)
    return [CRMConfigResponse.from_orm(c) for c in configs]


@router.get("/configs/{config_id}", response_model=CRMConfigResponse)
def get_crm_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get specific CRM config."""
    org = get_org_from_user(current_user, db)
    hub = get_hub(db)
    
    config = hub.get_crm_config(config_id, org.id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    
    return CRMConfigResponse.from_orm(config)


# ============================================================================
# INTAKE CAPTURE
# ============================================================================

@router.post("/intakes", response_model=IntakeCaptureResponse, status_code=201)
def capture_intake(
    req: IntakeCaptureRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Capture intake from call, form, chat, etc."""
    org = get_org_from_user(current_user, db)
    hub = get_hub(db)
    
    # Process intake
    processor = IntakeProcessor()
    
    if req.intake_type == "incoming_call":
        standardized = processor.process_phone_call(
            caller_name=req.caller_name,
            caller_phone=req.caller_phone,
            email=req.caller_email,
            address=req.caller_address,
            service_type=req.service_type,
            description=req.service_description,
            urgency=req.urgency_level,
            preferred_time=req.preferred_time,
            extra_fields=req.extra_fields,
        )
    elif req.intake_type == "form_submission":
        form_data = {
            "name": req.caller_name,
            "phone": req.caller_phone,
            "email": req.caller_email,
            "address": req.caller_address,
            "service_type": req.service_type,
            "description": req.service_description,
            "urgency": req.urgency_level,
            "preferred_time": req.preferred_time,
            **req.extra_fields,
        }
        standardized = processor.process_web_form(form_data)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown intake type: {req.intake_type}")
    
    # Capture
    intake = hub.capture_intake(
        org_id=org.id,
        intake=standardized,
        intake_type=IntakeType[req.intake_type.upper()],
        source=req.source,
    )
    
    if not intake:
        raise HTTPException(status_code=400, detail="Failed to capture intake")
    
    return IntakeCaptureResponse.from_orm(intake)


@router.get("/intakes", response_model=List[IntakeCaptureResponse])
def list_intakes(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List recent intakes."""
    org = get_org_from_user(current_user, db)
    
    intakes = db.query(IntakeCapture).filter(
        IntakeCapture.organization_id == org.id
    ).order_by(IntakeCapture.intake_timestamp.desc()).offset(offset).limit(limit).all()
    
    return [IntakeCaptureResponse.from_orm(i) for i in intakes]


# ============================================================================
# HANDOFF ROUTING
# ============================================================================

@router.post("/intakes/{intake_id}/handoff", response_model=HandoffResponse)
async def trigger_handoff(
    intake_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually trigger handoff for intake."""
    org = get_org_from_user(current_user, db)
    hub = get_hub(db)
    
    handoff = await hub.handoff_to_crm(intake_id, org.id)
    
    if not handoff:
        raise HTTPException(status_code=400, detail="Failed to handoff intake")
    
    return HandoffResponse.from_orm(handoff)


@router.get("/handoffs", response_model=List[HandoffResponse])
def list_handoffs(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List recent handoffs."""
    org = get_org_from_user(current_user, db)
    
    handoffs = db.query(CRMHandoff).filter(
        CRMHandoff.organization_id == org.id
    ).order_by(CRMHandoff.sent_at.desc()).limit(limit).all()
    
    return [HandoffResponse.from_orm(h) for h in handoffs]


# ============================================================================
# TESTING
# ============================================================================

@router.post("/configs/{config_id}/test")
async def run_test_lead(
    config_id: int,
    req: TestLeadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run test lead to verify CRM integration."""
    org = get_org_from_user(current_user, db)
    hub = get_hub(db)
    
    success, message = await hub.run_test_lead(
        config_id=config_id,
        org_id=org.id,
        test_data=req.dict(),
    )
    
    return {
        "success": success,
        "message": message,
    }


# ============================================================================
# APPROVAL WORKFLOW
# ============================================================================

@router.post("/configs/{config_id}/approve", response_model=CRMConfigResponse)
def approve_crm_config(
    config_id: int,
    req: ApproveConfigRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Approve CRM config to go live."""
    org = get_org_from_user(current_user, db)
    hub = get_hub(db)
    
    # Verify user is org owner or admin
    if current_user.role not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    config = hub.approve_crm_config(config_id, org.id, req.approved_by_user_id)
    
    if not config:
        raise HTTPException(status_code=400, detail="Failed to approve config")
    
    return CRMConfigResponse.from_orm(config)


# ============================================================================
# ONBOARDING
# ============================================================================

@router.get("/onboarding", response_model=OnboardingStepResponse)
def get_onboarding_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get onboarding progress."""
    org = get_org_from_user(current_user, db)
    
    from ..models.crm_hub import OnboardingProgress
    progress = db.query(OnboardingProgress).filter(
        OnboardingProgress.organization_id == org.id
    ).first()
    
    if not progress:
        progress = OnboardingProgress(organization_id=org.id)
        db.add(progress)
        db.commit()
        db.refresh(progress)
    
    return OnboardingStepResponse.from_orm(progress)


# ============================================================================
# STATUS & REPORTING
# ============================================================================

@router.get("/status", response_model=HubStatusResponse)
def get_hub_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get integration hub status."""
    org = get_org_from_user(current_user, db)
    hub = get_hub(db)
    
    status = hub.get_hub_status(org.id)
    if not status:
        raise HTTPException(status_code=500, detail="Failed to get status")
    
    # Calculate success rate
    success_rate = 0.0
    if status.total_handoffs > 0:
        success_rate = (status.successful_handoffs / status.total_handoffs) * 100
    
    return HubStatusResponse(
        total_crm_configs=status.total_crm_configs,
        active_configs=status.active_configs,
        total_intakes_captured=status.total_intakes_captured,
        total_handoffs=status.total_handoffs,
        successful_handoffs=status.successful_handoffs,
        failed_handoffs=status.failed_handoffs,
        last_intake_at=status.last_intake_at.isoformat() if status.last_intake_at else None,
        last_handoff_at=status.last_handoff_at.isoformat() if status.last_handoff_at else None,
        last_error_at=status.last_error_at.isoformat() if status.last_error_at else None,
        last_error_message=status.last_error_message,
        success_rate=round(success_rate, 1),
    )


@router.get("/configs/{config_id}/stats")
def get_config_stats(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get stats for specific CRM config."""
    org = get_org_from_user(current_user, db)
    hub = get_hub(db)
    
    config = hub.get_crm_config(config_id, org.id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    
    handoffs = db.query(CRMHandoff).filter(
        CRMHandoff.crm_config_id == config_id
    ).all()
    
    successful = len([h for h in handoffs if h.is_successful])
    total = len(handoffs)
    success_rate = (successful / total * 100) if total > 0 else 0
    
    return {
        "config_id": config.id,
        "crm_provider": config.crm_provider.value,
        "name": config.name,
        "is_active": config.is_active,
        "total_handoffs": total,
        "successful_handoffs": successful,
        "failed_handoffs": total - successful,
        "success_rate": round(success_rate, 1),
        "leads_synced": config.leads_synced_count,
        "last_sync": config.last_sync_at.isoformat() if config.last_sync_at else None,
        "last_test": config.last_test_at.isoformat() if config.last_test_at else None,
        "test_count": config.test_lead_count,
    }
