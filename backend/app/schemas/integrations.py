"""
Pydantic schemas for integration API endpoints.
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Dict, Any, Optional, List
from enum import Enum


class IntegrationPlatformEnum(str, Enum):
    """Available integration platforms"""
    ZAPIER = "zapier"
    GOOGLE_SHEETS = "google_sheets"
    JOBBER = "jobber"
    HOUSECALL = "housecall"
    HOUSECALL_PRO = "housecall_pro"
    CUSTOM_WEBHOOK = "custom_webhook"


class IntegrationDirectionEnum(str, Enum):
    """Data flow direction"""
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    BIDIRECTIONAL = "bidirectional"


class IntegrationConfigCreate(BaseModel):
    """Request to create an integration config."""
    name: str = Field(..., min_length=1, max_length=255)
    platform: IntegrationPlatformEnum
    direction: IntegrationDirectionEnum = IntegrationDirectionEnum.INBOUND
    config_data: Dict[str, Any] = Field(default_factory=dict, description="API keys, tokens, etc.")
    field_mapping: Dict[str, str] = Field(default_factory=dict, description="Field mapping: gfw_field -> external_field")
    webhook_secret: Optional[str] = Field(None, description="Optional webhook secret for validation")


class IntegrationConfigUpdate(BaseModel):
    """Request to update an integration config."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    direction: Optional[IntegrationDirectionEnum] = None
    config_data: Optional[Dict[str, Any]] = None
    field_mapping: Optional[Dict[str, str]] = None
    webhook_secret: Optional[str] = None
    is_active: Optional[bool] = None


class IntegrationConfigResponse(BaseModel):
    """Integration config response."""
    id: int
    organization_id: int
    name: str
    platform: str
    direction: str
    is_active: bool
    webhook_url: Optional[str] = None
    last_sync_at: Optional[str] = None
    last_sync_status: Optional[str] = None
    last_sync_error: Optional[str] = None
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class WebhookPayload(BaseModel):
    """Generic webhook payload."""
    data: Dict[str, Any]
    entity_type: Optional[str] = None
    external_id: Optional[str] = None


class SyncRequest(BaseModel):
    """Request to trigger manual sync."""
    data: Dict[str, Any]
    entity_type: str = Field(..., description="Entity type: job, customer, estimate, etc.")


class SyncResultData(BaseModel):
    """Result of a sync operation."""
    success: bool
    synced_id: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    timestamp: str


class IntegrationHealthResponse(BaseModel):
    """Integration health check response."""
    id: int
    name: str
    platform: str
    is_active: bool
    is_authenticated: bool
    last_sync_at: Optional[str] = None
    last_sync_status: Optional[str] = None
    message: str


class IntegrationListResponse(BaseModel):
    """List of integrations."""
    total: int
    configs: List[IntegrationConfigResponse]


class PlatformInfoResponse(BaseModel):
    """Information about a specific platform."""
    name: str
    description: str
    supported_directions: List[str]
    requires_config_fields: List[str]
    webhook_capable: bool
    docs_url: Optional[str] = None


class AvailablePlatformsResponse(BaseModel):
    """List of available platforms."""
    platforms: Dict[str, PlatformInfoResponse]
