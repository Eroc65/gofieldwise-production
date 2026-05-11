"""
Pydantic schemas for CRM Integration Hub API.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class CRMProviderEnum(str, Enum):
    HOUSECALL_PRO = "housecall_pro"
    SERVICETITAN = "servicetitan"
    JOBBER = "jobber"
    GOOGLE_CALENDAR = "google_calendar"
    GOOGLE_BUSINESS_PROFILE = "google_business_profile"
    ZAPIER = "zapier"
    CUSTOM_WEBHOOK = "custom_webhook"
    MANUAL = "manual"


class IntegrationModeEnum(str, Enum):
    NATIVE_API = "native_api"
    OAUTH = "oauth"
    ZAPIER = "zapier"
    WEBHOOK = "webhook"
    MANUAL = "manual"


class CRMConfigCreateRequest(BaseModel):
    """Request to create CRM configuration."""
    crm_provider: CRMProviderEnum
    integration_mode: IntegrationModeEnum
    name: str = Field(..., min_length=1, max_length=255)
    config_data: Dict[str, Any] = Field(default_factory=dict)
    field_mapping: Dict[str, str] = Field(default_factory=dict)


class CRMConfigResponse(BaseModel):
    """CRM configuration response."""
    id: int
    organization_id: int
    crm_provider: str
    integration_mode: str
    name: str
    is_active: bool
    handoff_status: str
    last_test_at: Optional[str]
    last_test_status: Optional[str]
    last_sync_at: Optional[str]
    leads_synced_count: int
    created_at: str
    
    class Config:
        from_attributes = True


class IntakeCaptureRequest(BaseModel):
    """Request to capture intake."""
    intake_type: str
    source: str
    caller_name: Optional[str]
    caller_phone: Optional[str]
    caller_email: Optional[str]
    caller_address: Optional[str]
    service_type: Optional[str]
    service_description: Optional[str]
    urgency_level: Optional[str] = "medium"
    preferred_time: Optional[datetime]
    extra_fields: Dict[str, Any] = Field(default_factory=dict)


class IntakeCaptureResponse(BaseModel):
    """Captured intake response."""
    id: int
    organization_id: int
    crm_config_id: Optional[int]
    intake_type: str
    source: str
    caller_name: Optional[str]
    caller_phone: Optional[str]
    caller_email: Optional[str]
    service_type: Optional[str]
    missing_fields: List[str]
    is_processed: bool
    created_at: str
    
    class Config:
        from_attributes = True


class TestLeadRequest(BaseModel):
    """Request to run test lead."""
    caller_name: Optional[str] = "Test Lead"
    caller_phone: Optional[str] = "555-0000"
    caller_email: Optional[str] = "test@example.com"
    service_type: Optional[str] = "Test Service"


class HandoffResponse(BaseModel):
    """Handoff result response."""
    id: int
    intake_id: int
    crm_provider: str
    is_successful: bool
    handoff_method: str
    external_record_id: Optional[str]
    external_record_url: Optional[str]
    error_message: Optional[str]
    sent_at: str
    
    class Config:
        from_attributes = True


class OnboardingStepResponse(BaseModel):
    """Onboarding progress response."""
    current_step: int
    step_1_crm_selected: bool
    step_2_integration_mode: bool
    step_3_credentials_provided: bool
    step_4_field_mapping: bool
    step_5_test_lead: bool
    step_6_approved: bool
    step_7_live: bool
    completed_at: Optional[str]
    
    class Config:
        from_attributes = True


class HubStatusResponse(BaseModel):
    """Integration hub status response."""
    total_crm_configs: int
    active_configs: int
    total_intakes_captured: int
    total_handoffs: int
    successful_handoffs: int
    failed_handoffs: int
    last_intake_at: Optional[str]
    last_handoff_at: Optional[str]
    last_error_at: Optional[str]
    last_error_message: Optional[str]
    success_rate: float  # percentage
    
    class Config:
        from_attributes = True


class ApproveConfigRequest(BaseModel):
    """Request to approve CRM config."""
    approved_by_user_id: int


class AvailableCRMResponse(BaseModel):
    """Available CRM provider info."""
    provider: str
    name: str
    supported_modes: List[str]
    required_config_fields: List[str]
    status: str  # "active", "beta", "planned"
    fallback_available: bool
    documentation_url: Optional[str]


class AvailableCRMsResponse(BaseModel):
    """List of available CRM providers."""
    providers: List[AvailableCRMResponse]
