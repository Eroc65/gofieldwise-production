"""
CRM Adapter Framework.
Base classes for building CRM connectors with fallback support.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class HandoffMethod(str, Enum):
    """How intake is handed off to CRM"""
    API = "api"
    ZAPIER = "zapier"
    WEBHOOK = "webhook"
    MANUAL = "manual"


@dataclass
class StandardizedIntake:
    """Standardized intake format from all sources."""
    # Contact info
    caller_name: Optional[str] = None
    caller_phone: Optional[str] = None
    caller_email: Optional[str] = None
    caller_address: Optional[str] = None
    
    # Service details
    service_type: Optional[str] = None
    service_description: Optional[str] = None
    urgency_level: Optional[str] = None  # "high", "medium", "low"
    preferred_time: Optional[datetime] = None
    
    # Additional fields
    extra_fields: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    intake_type: str = "incoming_call"
    source: str = "unknown"
    captured_at: datetime = field(default_factory=datetime.utcnow)
    confidence_score: float = 1.0
    
    def get_all_fields(self) -> Dict[str, Any]:
        """Get all fields as dictionary."""
        return {
            "caller_name": self.caller_name,
            "caller_phone": self.caller_phone,
            "caller_email": self.caller_email,
            "caller_address": self.caller_address,
            "service_type": self.service_type,
            "service_description": self.service_description,
            "urgency_level": self.urgency_level,
            "preferred_time": self.preferred_time,
            **self.extra_fields,
        }
    
    def missing_fields(self, required: List[str]) -> List[str]:
        """Return list of missing required fields."""
        all_fields = self.get_all_fields()
        return [f for f in required if not all_fields.get(f)]


@dataclass
class HandoffResult:
    """Result of handoff to CRM."""
    success: bool
    method: HandoffMethod
    external_record_id: Optional[str] = None
    external_record_url: Optional[str] = None
    payload_sent: Dict[str, Any] = field(default_factory=dict)
    response_received: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    retry_able: bool = False


class BaseCRMAdapter(ABC):
    """
    Base class for CRM adapters.
    Each CRM gets a connector that maps standardized intake to its API fields.
    """
    
    def __init__(self, config_data: Dict[str, Any], field_mapping: Dict[str, str]):
        """
        Args:
            config_data: CRM-specific config (API keys, tokens, tenant IDs, etc.)
            field_mapping: Maps StandardizedIntake fields to CRM fields
                          {"caller_name": "firstName", ...}
        """
        self.config_data = config_data
        self.field_mapping = field_mapping
        self.logger = logger
    
    @abstractmethod
    def get_name(self) -> str:
        """Return CRM name."""
        pass
    
    @abstractmethod
    def validate_credentials(self) -> Tuple[bool, str]:
        """
        Validate that credentials are valid.
        Returns: (is_valid, error_message)
        """
        pass
    
    @abstractmethod
    def get_required_fields(self) -> List[str]:
        """Return list of required fields for this CRM."""
        pass
    
    @abstractmethod
    async def send_intake(self, intake: StandardizedIntake) -> HandoffResult:
        """
        Send standardized intake to CRM.
        Should try primary method, then fallback to webhook/zapier if needed.
        """
        pass
    
    def map_fields(self, intake: StandardizedIntake) -> Dict[str, Any]:
        """
        Map standardized intake fields to CRM fields using field_mapping.
        Override in subclass for custom transformation.
        """
        crm_payload = {}
        all_intake_fields = intake.get_all_fields()
        
        for gfw_field, crm_field in self.field_mapping.items():
            if gfw_field in all_intake_fields:
                value = all_intake_fields[gfw_field]
                if value is not None:
                    crm_payload[crm_field] = value
        
        return crm_payload
    
    async def test_connection(self) -> Tuple[bool, str]:
        """
        Test CRM connection and return status.
        Default implementation validates credentials.
        Override for more comprehensive testing.
        """
        is_valid, error = self.validate_credentials()
        if is_valid:
            return True, "Connection successful"
        return False, error
    
    async def _create_fallback_payload(self, intake: StandardizedIntake) -> Dict[str, Any]:
        """
        Create fallback payload for Zapier/webhook if native API fails.
        Can be overridden in subclass.
        """
        return {
            "source": "gofieldwise",
            "timestamp": intake.captured_at.isoformat(),
            "caller_name": intake.caller_name,
            "caller_phone": intake.caller_phone,
            "caller_email": intake.caller_email,
            "service_type": intake.service_type,
            "service_description": intake.service_description,
            "urgency": intake.urgency_level,
            "preferred_time": intake.preferred_time.isoformat() if intake.preferred_time else None,
        }


class APIBasedCRMAdapter(BaseCRMAdapter):
    """
    Base class for REST API-based CRM integrations.
    Provides common HTTP handling and error recovery.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session = None
    
    async def get_http_session(self):
        """Get or create async HTTP session."""
        if self._session is None:
            import httpx
            self._session = httpx.AsyncClient()
        return self._session
    
    async def close_session(self):
        """Close HTTP session."""
        if self._session:
            await self._session.aclose()
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Return authentication headers. Override in subclass."""
        return {}
    
    async def api_request(self, 
                         method: str,
                         endpoint: str,
                         **kwargs) -> Tuple[bool, Any]:
        """
        Make authenticated API request.
        Returns: (success, response_or_error)
        """
        session = await self.get_http_session()
        headers = self.get_auth_headers()
        headers.update(kwargs.pop("headers", {}))
        
        try:
            response = await session.request(method, endpoint, headers=headers, **kwargs)
            response.raise_for_status()
            return True, response.json()
        except Exception as e:
            self.logger.error(f"API request failed: {str(e)}")
            return False, str(e)


class WebhookBasedCRMAdapter(BaseCRMAdapter):
    """
    Base class for webhook-based CRM integrations.
    Sends data via webhook URL instead of direct API.
    """
    
    def get_webhook_url(self) -> Optional[str]:
        """Get webhook URL from config. Override if custom logic needed."""
        return self.config_data.get("webhook_url")
    
    async def send_to_webhook(self, intake: StandardizedIntake) -> HandoffResult:
        """
        Send intake to webhook URL.
        Used as primary or fallback method.
        """
        webhook_url = self.get_webhook_url()
        if not webhook_url:
            return HandoffResult(
                success=False,
                method=HandoffMethod.WEBHOOK,
                error_message="Webhook URL not configured"
            )
        
        payload = self.map_fields(intake)
        
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload)
                response.raise_for_status()
            
            return HandoffResult(
                success=True,
                method=HandoffMethod.WEBHOOK,
                payload_sent=payload,
                response_received=response.json(),
            )
        except Exception as e:
            self.logger.error(f"Webhook send failed: {str(e)}")
            return HandoffResult(
                success=False,
                method=HandoffMethod.WEBHOOK,
                payload_sent=payload,
                error_message=str(e),
                retry_able=True,
            )


class ManualHandoffCRMAdapter(BaseCRMAdapter):
    """
    Manual handoff adapter - for CRMs where no integration exists yet.
    Simply formats intake data for human review/manual entry.
    """
    
    def get_name(self) -> str:
        return "Manual Handoff"
    
    def validate_credentials(self) -> Tuple[bool, str]:
        """Manual handoff always works."""
        return True, "Manual handoff always available"
    
    def get_required_fields(self) -> List[str]:
        """Recommend these fields for manual entry."""
        return ["caller_name", "caller_phone", "service_type"]
    
    async def send_intake(self, intake: StandardizedIntake) -> HandoffResult:
        """
        Manual handoff: format intake for human review.
        In production, this would create a task/notification for staff.
        """
        formatted = self._format_for_manual(intake)
        
        return HandoffResult(
            success=True,
            method=HandoffMethod.MANUAL,
            payload_sent=formatted,
            warnings=["This is a manual handoff. Please review and enter into CRM manually."],
        )
    
    def _format_for_manual(self, intake: StandardizedIntake) -> Dict[str, str]:
        """Format intake for manual entry."""
        return {
            "Name": intake.caller_name or "[Not captured]",
            "Phone": intake.caller_phone or "[Not captured]",
            "Email": intake.caller_email or "[Not captured]",
            "Address": intake.caller_address or "[Not captured]",
            "Service": intake.service_type or "[Not captured]",
            "Description": intake.service_description or "[Not captured]",
            "Urgency": intake.urgency_level or "medium",
            "Preferred Time": intake.preferred_time.isoformat() if intake.preferred_time else "[Not specified]",
            "Raw Notes": intake.extra_fields.get("notes", ""),
        }
