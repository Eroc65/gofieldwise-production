"""
Universal Integration Adapter Framework.
Base classes and interfaces for all integrations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Generic, TypeVar
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class DataMapping:
    """Manages field mapping between gofieldwise and external systems."""
    
    def __init__(self, mapping: Dict[str, str]):
        """
        Args:
            mapping: {"gofieldwise_field": "external_field"}
        """
        self.mapping = mapping
        self.reverse_mapping = {v: k for k, v in mapping.items()}
    
    def to_external(self, gfw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert gofieldwise data to external system format."""
        external_data = {}
        for gfw_key, gfw_value in gfw_data.items():
            external_key = self.mapping.get(gfw_key, gfw_key)
            external_data[external_key] = gfw_value
        return external_data
    
    def to_gofieldwise(self, external_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert external system data to gofieldwise format."""
        gfw_data = {}
        for ext_key, ext_value in external_data.items():
            gfw_key = self.reverse_mapping.get(ext_key, ext_key)
            gfw_data[gfw_key] = ext_value
        return gfw_data
    
    def map_external_to_gfw(self, external_field: str) -> str:
        """Map single external field to gofieldwise field."""
        return self.reverse_mapping.get(external_field, external_field)
    
    def map_gfw_to_external(self, gfw_field: str) -> str:
        """Map single gofieldwise field to external field."""
        return self.mapping.get(gfw_field, gfw_field)


@dataclass
class SyncResult:
    """Result of a sync operation."""
    success: bool
    synced_id: Optional[str] = None  # External or internal ID
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def add_error(self, error: str) -> None:
        self.errors.append(error)
        self.success = False
    
    def add_warning(self, warning: str) -> None:
        self.warnings.append(warning)
    
    def __dict__(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "synced_id": self.synced_id,
            "data": self.data,
            "errors": self.errors,
            "warnings": self.warnings,
            "timestamp": self.timestamp.isoformat(),
        }


class BaseIntegration(ABC):
    """
    Base class for all integrations.
    Defines required interface and common functionality.
    """
    
    def __init__(self, 
                 config_data: Dict[str, Any],
                 field_mapping: Dict[str, str],
                 webhook_secret: Optional[str] = None):
        """
        Args:
            config_data: Integration-specific config (API keys, tokens, etc.)
            field_mapping: Field mapping from gofieldwise to external system
            webhook_secret: Optional webhook secret for validating requests
        """
        self.config_data = config_data
        self.field_mapping = DataMapping(field_mapping)
        self.webhook_secret = webhook_secret
        self.logger = logger
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Verify authentication credentials. Return True if valid."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Return integration name."""
        pass
    
    @abstractmethod
    def normalize_webhook_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize incoming webhook payload to gofieldwise format.
        Should map external fields to gofieldwise fields.
        """
        pass
    
    def validate_webhook_secret(self, received_secret: str) -> bool:
        """Validate webhook secret if required."""
        if not self.webhook_secret:
            return True
        import hmac
        return hmac.compare_digest(received_secret, self.webhook_secret)
    
    async def inbound_sync(self, external_data: Dict[str, Any]) -> SyncResult:
        """
        Process inbound data from external system.
        Override in subclass for specific behavior.
        """
        raise NotImplementedError("Subclass must implement inbound_sync")
    
    async def outbound_sync(self, gfw_data: Dict[str, Any], gfw_id: int) -> SyncResult:
        """
        Push data to external system.
        Override in subclass for specific behavior.
        """
        raise NotImplementedError("Subclass must implement outbound_sync")
    
    async def fetch_external_record(self, external_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a single record from external system.
        Override in subclass for bidirectional sync.
        """
        return None
    
    async def list_external_records(self, **filters) -> List[Dict[str, Any]]:
        """
        List records from external system with optional filters.
        Override in subclass for batch operations.
        """
        return []


class WebhookIntegration(BaseIntegration):
    """
    Base class for webhook-based integrations.
    Handles common webhook validation and processing.
    """
    
    async def validate_webhook_request(self, 
                                      headers: Dict[str, str],
                                      body: Dict[str, Any]) -> bool:
        """
        Validate incoming webhook request.
        Override for integration-specific validation.
        """
        return True
    
    async def process_webhook(self, payload: Dict[str, Any]) -> SyncResult:
        """
        Main webhook processor.
        1. Validate payload
        2. Normalize to gofieldwise format
        3. Sync to database
        """
        try:
            # Normalize payload
            normalized = self.normalize_webhook_payload(payload)
            
            # Perform inbound sync
            result = await self.inbound_sync(normalized)
            
            return result
        except Exception as e:
            self.logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
            result = SyncResult(success=False)
            result.add_error(str(e))
            return result


class RESTIntegration(BaseIntegration):
    """
    Base class for REST API integrations.
    Provides common HTTP client setup and error handling.
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
                         **kwargs) -> Dict[str, Any]:
        """
        Make authenticated API request.
        Override for custom error handling.
        """
        session = await self.get_http_session()
        headers = self.get_auth_headers()
        headers.update(kwargs.pop("headers", {}))
        
        try:
            response = await session.request(method, endpoint, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"API request failed: {str(e)}")
            raise
