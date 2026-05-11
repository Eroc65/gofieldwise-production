"""
Integration Manager and Registry.
Central place for managing all integrations.
"""

from typing import Dict, Any, Optional, List, Type
from .integration_adapter import BaseIntegration, SyncResult
from .integrations import (
    ZapierIntegration,
    GoogleSheetsIntegration,
    JobberIntegration,
    HouseCallIntegration,
    CustomWebhookIntegration,
)
import logging

logger = logging.getLogger(__name__)


class IntegrationRegistry:
    """
    Registry of available integrations.
    Maps platform names to integration classes.
    """
    
    _integrations: Dict[str, Type[BaseIntegration]] = {
        "zapier": ZapierIntegration,
        "google_sheets": GoogleSheetsIntegration,
        "jobber": JobberIntegration,
        "housecall": HouseCallIntegration,
        "housecall_pro": HouseCallIntegration,
        "custom_webhook": CustomWebhookIntegration,
    }
    
    @classmethod
    def get_integration_class(cls, platform: str) -> Optional[Type[BaseIntegration]]:
        """Get integration class by platform name."""
        return cls._integrations.get(platform.lower())
    
    @classmethod
    def list_available(cls) -> List[str]:
        """List all available integrations."""
        return list(cls._integrations.keys())
    
    @classmethod
    def register(cls, platform: str, integration_class: Type[BaseIntegration]) -> None:
        """Register a new integration."""
        cls._integrations[platform.lower()] = integration_class
        logger.info(f"Registered integration: {platform}")


class IntegrationManager:
    """
    Manages integration lifecycle and orchestrates sync operations.
    """
    
    def __init__(self):
        self.active_integrations: Dict[int, BaseIntegration] = {}  # config_id -> integration instance
    
    def create_integration(self, 
                          platform: str,
                          config_data: Dict[str, Any],
                          field_mapping: Dict[str, str],
                          webhook_secret: Optional[str] = None,
                          config_id: Optional[int] = None) -> Optional[BaseIntegration]:
        """
        Create and initialize an integration instance.
        
        Args:
            platform: Integration platform (zapier, google_sheets, etc.)
            config_data: Platform-specific configuration
            field_mapping: Field mapping for data transformation
            webhook_secret: Optional webhook validation secret
            config_id: Optional config ID for caching
        
        Returns:
            Integration instance or None if platform not found
        """
        integration_class = IntegrationRegistry.get_integration_class(platform)
        if not integration_class:
            logger.error(f"Unknown integration platform: {platform}")
            return None
        
        try:
            integration = integration_class(
                config_data=config_data,
                field_mapping=field_mapping,
                webhook_secret=webhook_secret,
            )
            
            # Verify authentication
            if not integration.authenticate():
                logger.warning(f"Authentication failed for {platform}")
                return None
            
            # Cache if config_id provided
            if config_id:
                self.active_integrations[config_id] = integration
            
            logger.info(f"Created {platform} integration (config_id={config_id})")
            return integration
        except Exception as e:
            logger.error(f"Failed to create integration: {str(e)}", exc_info=True)
            return None
    
    def get_integration(self, config_id: int) -> Optional[BaseIntegration]:
        """Get cached integration by config ID."""
        return self.active_integrations.get(config_id)
    
    def remove_integration(self, config_id: int) -> None:
        """Remove integration from cache."""
        if config_id in self.active_integrations:
            del self.active_integrations[config_id]
            logger.info(f"Removed integration: config_id={config_id}")
    
    async def handle_webhook(self,
                            integration: BaseIntegration,
                            payload: Dict[str, Any],
                            headers: Dict[str, str]) -> SyncResult:
        """
        Process incoming webhook from external system.
        
        Args:
            integration: Integration instance
            payload: Webhook payload
            headers: HTTP headers (for secret validation)
        
        Returns:
            SyncResult with operation details
        """
        try:
            # Validate webhook if secret configured
            webhook_secret = headers.get("x-webhook-secret") or headers.get("authorization")
            if integration.webhook_secret and webhook_secret:
                if not integration.validate_webhook_secret(webhook_secret):
                    result = SyncResult(success=False)
                    result.add_error("Invalid webhook secret")
                    return result
            
            # Process webhook
            if hasattr(integration, 'process_webhook'):
                result = await integration.process_webhook(payload)
            else:
                # Fallback to inbound_sync
                normalized = integration.normalize_webhook_payload(payload)
                result = await integration.inbound_sync(normalized)
            
            logger.info(f"Webhook processed: {integration.get_name()}, success={result.success}")
            return result
        except Exception as e:
            logger.error(f"Webhook processing error: {str(e)}", exc_info=True)
            result = SyncResult(success=False)
            result.add_error(str(e))
            return result
    
    async def sync_outbound(self,
                           integration: BaseIntegration,
                           gfw_data: Dict[str, Any],
                           gfw_id: int) -> SyncResult:
        """
        Push data from gofieldwise to external system.
        
        Args:
            integration: Integration instance
            gfw_data: Data to sync
            gfw_id: gofieldwise record ID
        
        Returns:
            SyncResult with operation details
        """
        try:
            result = await integration.outbound_sync(gfw_data, gfw_id)
            logger.info(f"Outbound sync: {integration.get_name()}, gfw_id={gfw_id}, success={result.success}")
            return result
        except Exception as e:
            logger.error(f"Outbound sync error: {str(e)}", exc_info=True)
            result = SyncResult(success=False)
            result.add_error(str(e))
            return result
    
    async def fetch_from_external(self,
                                 integration: BaseIntegration,
                                 external_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a single record from external system.
        
        Args:
            integration: Integration instance
            external_id: ID in external system
        
        Returns:
            External system record or None
        """
        try:
            record = await integration.fetch_external_record(external_id)
            return record
        except Exception as e:
            logger.error(f"Failed to fetch from external system: {str(e)}", exc_info=True)
            return None


# Global singleton instance
_manager = IntegrationManager()


def get_manager() -> IntegrationManager:
    """Get global integration manager instance."""
    return _manager
