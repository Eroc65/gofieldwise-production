"""
CRM Integration Hub models.
Handles multi-CRM integration, intake capture, and handoffs.
"""

from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON, 
    Enum as SQLEnum, Float, Index
)
from sqlalchemy.orm import relationship
from ..core.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CRMProvider(str, Enum):
    """Supported CRM providers"""
    HOUSECALL_PRO = "housecall_pro"
    SERVICETITAN = "servicetitan"
    JOBBER = "jobber"
    GOOGLE_CALENDAR = "google_calendar"
    GOOGLE_BUSINESS_PROFILE = "google_business_profile"
    ZAPIER = "zapier"
    CUSTOM_WEBHOOK = "custom_webhook"
    MANUAL = "manual"


class IntegrationMode(str, Enum):
    """Integration method"""
    NATIVE_API = "native_api"
    OAUTH = "oauth"
    ZAPIER = "zapier"
    WEBHOOK = "webhook"
    MANUAL = "manual"


class HandoffStatus(str, Enum):
    """Status of lead/call handoff to CRM"""
    PENDING_SETUP = "pending_setup"
    READY = "ready"
    TESTING = "testing"
    LIVE = "live"
    PAUSED = "paused"
    FAILED = "failed"


class IntakeType(str, Enum):
    """Type of intake captured"""
    INCOMING_CALL = "incoming_call"
    FORM_SUBMISSION = "form_submission"
    CHAT = "chat"
    EMAIL = "email"
    MANUAL_ENTRY = "manual_entry"


class CRMConfiguration(Base):
    """CRM integration configuration per organization."""
    __tablename__ = "crm_configurations"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    crm_provider = Column(SQLEnum(CRMProvider), nullable=False, index=True)
    integration_mode = Column(SQLEnum(IntegrationMode), nullable=False)
    name = Column(String(255), nullable=False)  # User-friendly name
    
    # Configuration (credentials stored securely - encrypted in production)
    config_data = Column(JSON, nullable=False, default={})  # API keys, tokens, tenant IDs, etc.
    field_mapping = Column(JSON, nullable=False, default={})  # CRM field mappings
    
    # Status
    is_active = Column(Boolean, nullable=False, default=False)
    handoff_status = Column(SQLEnum(HandoffStatus), nullable=False, default=HandoffStatus.PENDING_SETUP)
    
    # Approval tracking
    requires_approval = Column(Boolean, nullable=False, default=True)
    approved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    # Testing
    last_test_at = Column(DateTime, nullable=True)
    last_test_status = Column(String(50), nullable=True)
    test_lead_count = Column(Integer, nullable=False, default=0)
    
    # Tracking
    leads_synced_count = Column(Integer, nullable=False, default=0)
    last_sync_at = Column(DateTime, nullable=True)
    last_sync_error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    updated_at = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)
    
    organization = relationship("Organization", foreign_keys=[organization_id])
    user = relationship("User", foreign_keys=[approved_by_user_id])
    intakes = relationship("IntakeCapture", back_populates="crm_config")
    handoffs = relationship("CRMHandoff", back_populates="crm_config")
    
    def __repr__(self):
        return f"<CRMConfiguration(id={self.id}, crm={self.crm_provider}, status={self.handoff_status})>"


class IntakeCapture(Base):
    """Standardized intake from calls, forms, chats, etc."""
    __tablename__ = "intake_captures"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    crm_config_id = Column(Integer, ForeignKey("crm_configurations.id"), nullable=True)
    
    # Intake metadata
    intake_type = Column(SQLEnum(IntakeType), nullable=False, index=True)
    source = Column(String(100), nullable=False)  # "phone_system", "web_form", "chat", etc.
    intake_timestamp = Column(DateTime, nullable=False, default=_utcnow, index=True)
    
    # Caller/contact info
    caller_name = Column(String(255), nullable=True)
    caller_phone = Column(String(20), nullable=True)
    caller_email = Column(String(255), nullable=True)
    caller_address = Column(String(500), nullable=True)
    
    # Service details
    service_type = Column(String(255), nullable=True)
    service_description = Column(Text, nullable=True)
    urgency_level = Column(String(50), nullable=True)  # "high", "medium", "low"
    preferred_time = Column(DateTime, nullable=True)
    
    # Extracted data
    raw_transcript = Column(Text, nullable=True)
    extracted_fields = Column(JSON, nullable=False, default={})  # Any additional extracted fields
    
    # Quality flags
    missing_fields = Column(JSON, nullable=False, default=[])  # List of missing required fields
    ai_confidence = Column(Float, nullable=True)  # 0.0-1.0 confidence in extraction
    
    # Processing
    is_processed = Column(Boolean, nullable=False, default=False)
    processing_error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=_utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)
    
    organization = relationship("Organization", foreign_keys=[organization_id])
    crm_config = relationship("CRMConfiguration", foreign_keys=[crm_config_id])
    handoffs = relationship("CRMHandoff", back_populates="intake")
    
    __table_args__ = (
        Index('idx_organization_timestamp', organization_id, intake_timestamp),
        Index('idx_organization_processed', organization_id, is_processed),
    )
    
    def __repr__(self):
        return f"<IntakeCapture(id={self.id}, type={self.intake_type}, caller={self.caller_name})>"


class CRMHandoff(Base):
    """Log of intake handoff to CRM system."""
    __tablename__ = "crm_handoffs"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    intake_id = Column(Integer, ForeignKey("intake_captures.id"), nullable=False, index=True)
    crm_config_id = Column(Integer, ForeignKey("crm_configurations.id"), nullable=False, index=True)
    
    # Handoff details
    crm_provider = Column(SQLEnum(CRMProvider), nullable=False)
    integration_mode = Column(SQLEnum(IntegrationMode), nullable=False)
    
    # Handoff payload
    crm_payload = Column(JSON, nullable=False)  # What was sent to CRM
    crm_response = Column(JSON, nullable=True)  # Response from CRM (if applicable)
    
    # CRM record reference
    external_record_id = Column(String(255), nullable=True)  # ID in external CRM
    external_record_url = Column(String(500), nullable=True)  # Direct link to record
    
    # Status
    is_successful = Column(Boolean, nullable=False, default=False)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    
    # Tracking
    handoff_method = Column(String(100), nullable=False)  # "api", "zapier", "webhook", "manual"
    handled_by = Column(String(100), nullable=True)  # "system", "zapier", "human", etc.
    
    # Timestamps
    sent_at = Column(DateTime, nullable=False, default=_utcnow, index=True)
    received_at = Column(DateTime, nullable=True)
    
    # Audit
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    updated_at = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)
    
    organization = relationship("Organization", foreign_keys=[organization_id])
    intake = relationship("IntakeCapture", back_populates="handoffs")
    crm_config = relationship("CRMConfiguration", back_populates="handoffs")
    
    __table_args__ = (
        Index('idx_organization_crm', organization_id, crm_provider),
        Index('idx_intake_id', intake_id),
    )
    
    def __repr__(self):
        return f"<CRMHandoff(id={self.id}, crm={self.crm_provider}, success={self.is_successful})>"


class OnboardingProgress(Base):
    """Track CRM onboarding progress for clients."""
    __tablename__ = "onboarding_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, unique=True)
    crm_config_id = Column(Integer, ForeignKey("crm_configurations.id"), nullable=True)
    
    # Onboarding steps
    step_1_crm_selected = Column(Boolean, nullable=False, default=False)
    step_2_integration_mode = Column(Boolean, nullable=False, default=False)
    step_3_credentials_provided = Column(Boolean, nullable=False, default=False)
    step_4_field_mapping = Column(Boolean, nullable=False, default=False)
    step_5_test_lead = Column(Boolean, nullable=False, default=False)
    step_6_approved = Column(Boolean, nullable=False, default=False)
    step_7_live = Column(Boolean, nullable=False, default=False)
    
    # Current state
    current_step = Column(Integer, nullable=False, default=1)
    completed_at = Column(DateTime, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime, nullable=False, default=_utcnow)
    updated_at = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)
    
    organization = relationship("Organization", foreign_keys=[organization_id])
    crm_config = relationship("CRMConfiguration", foreign_keys=[crm_config_id])
    
    def __repr__(self):
        return f"<OnboardingProgress(org_id={self.organization_id}, step={self.current_step})>"


class IntegrationHubStatus(Base):
    """System status and health for integration hub."""
    __tablename__ = "integration_hub_status"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, unique=True)
    
    # Overall status
    total_crm_configs = Column(Integer, nullable=False, default=0)
    active_configs = Column(Integer, nullable=False, default=0)
    total_intakes_captured = Column(Integer, nullable=False, default=0)
    total_handoffs = Column(Integer, nullable=False, default=0)
    successful_handoffs = Column(Integer, nullable=False, default=0)
    failed_handoffs = Column(Integer, nullable=False, default=0)
    
    # Health metrics
    last_intake_at = Column(DateTime, nullable=True)
    last_handoff_at = Column(DateTime, nullable=True)
    last_error_at = Column(DateTime, nullable=True)
    last_error_message = Column(Text, nullable=True)
    
    # Updated at
    updated_at = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)
    
    organization = relationship("Organization", foreign_keys=[organization_id])
    
    def __repr__(self):
        return f"<IntegrationHubStatus(org_id={self.organization_id}, active={self.active_configs})>"
