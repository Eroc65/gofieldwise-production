"""
Integration API endpoints.
RESTful endpoints for managing integrations, webhooks, and sync operations.
"""

import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Request, Depends, Header
from sqlalchemy.orm import Session

from ..core.db import get_db
from .auth import get_current_user
from ..models.core import Organization
from ..models.integrations import (
    IntegrationConfig, IntegrationSyncLog, IntegrationPlatform, 
    IntegrationDirection, SyncStatus
)
from ..schemas.integrations import (
    IntegrationConfigCreate, IntegrationConfigUpdate, IntegrationConfigResponse,
    SyncRequest, SyncResultData, IntegrationHealthResponse, IntegrationListResponse,
    PlatformInfoResponse, AvailablePlatformsResponse, WebhookPayload
)
from ..services.integration_manager import get_manager, IntegrationRegistry
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


# Helper functions

def get_org_from_user(user, db: Session) -> Organization:
    """Get organization from current user."""
    org = db.query(Organization).filter(
        Organization.id == user.organization_id
    ).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


def _log_sync(db: Session, 
             config_id: int,
             sync_type: str,
             status: SyncStatus,
             direction: str,
             request_payload: Dict = None,
             response_payload: Dict = None,
             error_message: str = None) -> IntegrationSyncLog:
    """Log a sync operation."""
    log = IntegrationSyncLog(
        integration_config_id=config_id,
        sync_type=sync_type,
        status=status,
        direction=direction,
        request_payload=request_payload,
        response_payload=response_payload,
        error_message=error_message,
    )
    db.add(log)
    db.commit()
    return log


# Endpoints

@router.get("/platforms", response_model=AvailablePlatformsResponse)
def get_available_platforms():
    """List all available integration platforms."""
    platforms = {}
    
    platform_info = {
        "zapier": {
            "name": "Zapier",
            "description": "Connect to 1000+ apps via Zapier. Receive webhooks and sync data.",
            "supported_directions": ["inbound", "outbound", "bidirectional"],
            "requires_config_fields": ["webhook_url"],
            "webhook_capable": True,
            "docs_url": "https://zapier.com/help/",
        },
        "google_sheets": {
            "name": "Google Sheets",
            "description": "Sync data to/from Google Sheets. Read and write spreadsheet data.",
            "supported_directions": ["inbound", "outbound", "bidirectional"],
            "requires_config_fields": ["spreadsheet_id", "sheet_id", "access_token"],
            "webhook_capable": False,
            "docs_url": "https://developers.google.com/sheets/api",
        },
        "jobber": {
            "name": "Jobber",
            "description": "Field service management platform. Sync jobs, customers, estimates.",
            "supported_directions": ["inbound", "outbound", "bidirectional"],
            "requires_config_fields": ["api_token"],
            "webhook_capable": True,
            "docs_url": "https://developer.getjobber.com/",
        },
        "housecall_pro": {
            "name": "HouseCall Pro",
            "description": "Field service app. Sync customers, jobs, invoices.",
            "supported_directions": ["inbound", "outbound", "bidirectional"],
            "requires_config_fields": ["api_key"],
            "webhook_capable": True,
            "docs_url": "https://api.housecallpro.com/",
        },
        "custom_webhook": {
            "name": "Custom Webhook",
            "description": "Generic webhook integration. Flexible field mapping for any system.",
            "supported_directions": ["inbound", "outbound", "bidirectional"],
            "requires_config_fields": ["webhook_url"],
            "webhook_capable": True,
            "docs_url": None,
        },
    }
    
    for key, info in platform_info.items():
        platforms[key] = PlatformInfoResponse(**info)
    
    return AvailablePlatformsResponse(platforms=platforms)


@router.post("/", response_model=IntegrationConfigResponse, status_code=201)
def create_integration(
    req: IntegrationConfigCreate,
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new integration config."""
    org = get_org_from_user(current_user, db)
    
    # Validate platform
    if not IntegrationRegistry.get_integration_class(req.platform):
        raise HTTPException(status_code=400, detail=f"Unknown platform: {req.platform}")
    
    # Generate webhook URL for inbound integrations
    webhook_url = None
    if req.direction in ["inbound", "bidirectional"]:
        # Generate unique webhook URL
        import secrets
        webhook_token = secrets.token_urlsafe(24)
        webhook_url = f"{os.getenv('API_BASE_URL', 'http://localhost:8000')}/api/integrations/webhooks/{webhook_token}"
    
    # Create config
    config = IntegrationConfig(
        organization_id=org.id,
        platform=IntegrationPlatform[req.platform.upper().replace("-", "_")],
        name=req.name,
        direction=IntegrationDirection[req.direction.upper()],
        config_data=req.config_data,
        field_mapping=req.field_mapping,
        webhook_url=webhook_url,
        webhook_secret=req.webhook_secret,
        is_active=True,
    )
    
    db.add(config)
    db.commit()
    db.refresh(config)
    
    logger.info(f"Created integration: org_id={org.id}, platform={req.platform}, config_id={config.id}")
    return IntegrationConfigResponse.from_orm(config)


@router.get("/", response_model=IntegrationListResponse)
def list_integrations(
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all integrations for the organization."""
    org = get_org_from_user(current_user, db)
    
    configs = db.query(IntegrationConfig).filter(
        IntegrationConfig.organization_id == org.id
    ).all()
    
    return IntegrationListResponse(
        total=len(configs),
        configs=[IntegrationConfigResponse.from_orm(c) for c in configs]
    )


@router.get("/{config_id}", response_model=IntegrationConfigResponse)
def get_integration(
    config_id: int,
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific integration config."""
    org = get_org_from_user(current_user, db)
    
    config = db.query(IntegrationConfig).filter(
        IntegrationConfig.id == config_id,
        IntegrationConfig.organization_id == org.id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    return IntegrationConfigResponse.from_orm(config)


@router.patch("/{config_id}", response_model=IntegrationConfigResponse)
def update_integration(
    config_id: int,
    req: IntegrationConfigUpdate,
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an integration config."""
    org = get_org_from_user(current_user, db)
    
    config = db.query(IntegrationConfig).filter(
        IntegrationConfig.id == config_id,
        IntegrationConfig.organization_id == org.id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    # Update fields
    if req.name is not None:
        config.name = req.name
    if req.direction is not None:
        config.direction = IntegrationDirection[req.direction.upper()]
    if req.config_data is not None:
        config.config_data = req.config_data
    if req.field_mapping is not None:
        config.field_mapping = req.field_mapping
    if req.webhook_secret is not None:
        config.webhook_secret = req.webhook_secret
    if req.is_active is not None:
        config.is_active = req.is_active
    
    config.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(config)
    
    logger.info(f"Updated integration: config_id={config_id}")
    return IntegrationConfigResponse.from_orm(config)


@router.delete("/{config_id}", status_code=204)
def delete_integration(
    config_id: int,
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an integration config."""
    org = get_org_from_user(current_user, db)
    
    config = db.query(IntegrationConfig).filter(
        IntegrationConfig.id == config_id,
        IntegrationConfig.organization_id == org.id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    db.delete(config)
    db.commit()
    
    logger.info(f"Deleted integration: config_id={config_id}")


@router.get("/{config_id}/health", response_model=IntegrationHealthResponse)
def check_integration_health(
    config_id: int,
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Check health of an integration."""
    org = get_org_from_user(current_user, db)
    
    config = db.query(IntegrationConfig).filter(
        IntegrationConfig.id == config_id,
        IntegrationConfig.organization_id == org.id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    manager = get_manager()
    integration = manager.create_integration(
        platform=config.platform.value,
        config_data=config.config_data,
        field_mapping=config.field_mapping,
        webhook_secret=config.webhook_secret,
    )
    
    is_authenticated = integration is not None and integration.authenticate()
    
    return IntegrationHealthResponse(
        id=config.id,
        name=config.name,
        platform=config.platform.value,
        is_active=config.is_active,
        is_authenticated=is_authenticated,
        last_sync_at=config.last_sync_at.isoformat() if config.last_sync_at else None,
        last_sync_status=config.last_sync_status.value if config.last_sync_status else None,
        message="Integration is healthy" if is_authenticated else "Authentication failed",
    )


@router.post("/{config_id}/sync", response_model=SyncResultData)
async def trigger_manual_sync(
    config_id: int,
    req: SyncRequest,
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually trigger a sync operation."""
    org = get_org_from_user(current_user, db)
    
    config = db.query(IntegrationConfig).filter(
        IntegrationConfig.id == config_id,
        IntegrationConfig.organization_id == org.id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if not config.is_active:
        raise HTTPException(status_code=400, detail="Integration is not active")
    
    manager = get_manager()
    integration = manager.create_integration(
        platform=config.platform.value,
        config_data=config.config_data,
        field_mapping=config.field_mapping,
        webhook_secret=config.webhook_secret,
    )
    
    if not integration:
        raise HTTPException(status_code=400, detail="Failed to initialize integration")
    
    # Perform sync
    result = await integration.inbound_sync(req.data)
    
    # Log sync
    _log_sync(
        db,
        config_id=config_id,
        sync_type=req.entity_type,
        status=SyncStatus.SUCCESS if result.success else SyncStatus.FAILED,
        direction="inbound",
        request_payload=req.data,
        response_payload=result.data,
        error_message="; ".join(result.errors) if result.errors else None,
    )
    
    # Update config
    config.last_sync_at = datetime.utcnow()
    config.last_sync_status = SyncStatus.SUCCESS if result.success else SyncStatus.FAILED
    if result.errors:
        config.last_sync_error = "; ".join(result.errors)
    db.commit()
    
    logger.info(f"Manual sync triggered: config_id={config_id}, success={result.success}")
    
    return SyncResultData(**result.__dict__())


@router.post("/webhooks/{webhook_token}")
async def handle_webhook(
    webhook_token: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Generic webhook endpoint for all integrations.
    Validates webhook and routes to appropriate integration handler.
    """
    # Find integration config by webhook token (extracted from URL)
    # In production, use database lookup or cache
    config = db.query(IntegrationConfig).filter(
        IntegrationConfig.webhook_url.contains(webhook_token)
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    # Get request body and headers
    body = await request.json()
    headers = dict(request.headers)
    
    # Initialize integration
    manager = get_manager()
    integration = manager.create_integration(
        platform=config.platform.value,
        config_data=config.config_data,
        field_mapping=config.field_mapping,
        webhook_secret=config.webhook_secret,
    )
    
    if not integration:
        raise HTTPException(status_code=500, detail="Failed to initialize integration")
    
    # Process webhook
    result = await manager.handle_webhook(integration, body, headers)
    
    # Log sync
    _log_sync(
        db,
        config_id=config.id,
        sync_type=body.get("entity_type", "unknown"),
        status=SyncStatus.SUCCESS if result.success else SyncStatus.FAILED,
        direction="inbound",
        request_payload=body,
        response_payload=result.data,
        error_message="; ".join(result.errors) if result.errors else None,
    )
    
    # Update config
    config.last_sync_at = datetime.utcnow()
    config.last_sync_status = SyncStatus.SUCCESS if result.success else SyncStatus.FAILED
    if result.errors:
        config.last_sync_error = "; ".join(result.errors)
    db.commit()
    
    return {
        "success": result.success,
        "errors": result.errors,
        "warnings": result.warnings,
        "timestamp": result.timestamp.isoformat(),
    }
