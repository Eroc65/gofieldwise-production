"""
Integration models for universal adapter.
Stores integration configs, webhooks, and sync logs.
"""

from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, 
    Boolean, JSON, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from ..core.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class IntegrationPlatform(str, Enum):
    """Supported integration platforms"""
    ZAPIER = "zapier"
    GOOGLE_SHEETS = "google_sheets"
    JOBBER = "jobber"
    HOUSECALL = "housecall"
    CUSTOM_WEBHOOK = "custom_webhook"
    AIRTABLE = "airtable"
    SHOPIFY = "shopify"


class IntegrationDirection(str, Enum):
    """Data flow direction"""
    INBOUND = "inbound"  # Data flows into gofieldwise
    OUTBOUND = "outbound"  # Data flows out from gofieldwise
    BIDIRECTIONAL = "bidirectional"  # Two-way sync


class SyncStatus(str, Enum):
    """Status of sync operations"""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    PARTIAL = "partial"


class IntegrationConfig(Base):
    """
    Stores integration configurations per organization.
    Manages API keys, webhooks, and field mappings.
    """
    __tablename__ = "integration_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    platform = Column(SQLEnum(IntegrationPlatform), nullable=False, index=True)
    name = Column(String(255), nullable=False)  # User-friendly name
    direction = Column(SQLEnum(IntegrationDirection), nullable=False, default=IntegrationDirection.INBOUND)
    
    # Credentials and config (encrypted in production)
    config_data = Column(JSON, nullable=False, default={})  # API keys, tokens, etc.
    
    # Field mappings: {"gofieldwise_field": "external_field", ...}
    field_mapping = Column(JSON, nullable=False, default={})
    
    # Webhook URL for inbound integrations
    webhook_url = Column(String(500), nullable=True, unique=True)
    webhook_secret = Column(String(255), nullable=True)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    last_sync_at = Column(DateTime, nullable=True)
    last_sync_status = Column(SQLEnum(SyncStatus), nullable=True)
    last_sync_error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    updated_at = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)
    
    # Relationships
    organization = relationship("Organization", foreign_keys=[organization_id])
    sync_logs = relationship("IntegrationSyncLog", back_populates="integration_config")
    
    def __repr__(self):
        return f"<IntegrationConfig(id={self.id}, platform={self.platform}, name={self.name})>"


class IntegrationSyncLog(Base):
    """
    Audit trail for all sync operations.
    Useful for debugging and monitoring.
    """
    __tablename__ = "integration_sync_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    integration_config_id = Column(Integer, ForeignKey("integration_configs.id"), nullable=False, index=True)
    
    # Operation details
    sync_type = Column(String(50), nullable=False)  # "job", "customer", "estimate", etc.
    external_id = Column(String(255), nullable=True)  # ID in external system
    gofieldwise_id = Column(Integer, nullable=True)  # ID in gofieldwise
    
    # Sync details
    status = Column(SQLEnum(SyncStatus), nullable=False)
    direction = Column(SQLEnum(IntegrationDirection), nullable=False)
    
    # Payload (for debugging)
    request_payload = Column(JSON, nullable=True)
    response_payload = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=_utcnow, index=True)
    
    # Relationships
    integration_config = relationship("IntegrationConfig", back_populates="sync_logs")
    
    def __repr__(self):
        return f"<IntegrationSyncLog(id={self.id}, sync_type={self.sync_type}, status={self.status})>"
