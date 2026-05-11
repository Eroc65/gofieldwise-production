"""
Platform-specific integrations.
Zapier, Google Sheets, Jobber, HouseCall, and custom webhooks.
"""

from typing import Any, Dict, List, Optional
from .integration_adapter import (
    BaseIntegration, WebhookIntegration, RESTIntegration, SyncResult
)
import json
import logging

logger = logging.getLogger(__name__)


class ZapierIntegration(WebhookIntegration):
    """
    Zapier integration for connecting gofieldwise to 1000+ apps.
    Receives webhooks from Zapier, triggers actions, and sends data back.
    
    Features:
    - Inbound: Receive data from any connected Zapier app
    - Outbound: Send gofieldwise events to Zapier for automation
    - Bidirectional: Sync customer/job data across systems
    """
    
    def authenticate(self) -> bool:
        """Verify Zapier webhook URL is configured."""
        return bool(self.config_data.get("webhook_url"))
    
    def get_name(self) -> str:
        return "Zapier"
    
    def normalize_webhook_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Zapier payloads are flexible and depend on the connected app.
        This method handles common patterns and applies field mapping.
        """
        # Extract data from various Zapier webhook formats
        if isinstance(payload, dict):
            # Direct payload format
            data = payload.copy()
        else:
            return {}
        
        # Apply field mapping
        normalized = self.field_mapping.to_gofieldwise(data)
        return normalized
    
    async def inbound_sync(self, external_data: Dict[str, Any]) -> SyncResult:
        """
        Process data from Zapier webhook.
        Determines entity type (customer, job, lead, etc.) and syncs accordingly.
        """
        result = SyncResult(success=True, data=external_data)
        
        # Determine entity type from payload
        entity_type = external_data.get("entity_type") or external_data.get("type")
        if not entity_type:
            result.add_warning("No entity_type detected; using raw data")
            result.data = external_data
            return result
        
        # Log the sync
        logger.info(f"Zapier inbound sync: {entity_type}", extra={"payload": external_data})
        
        return result
    
    async def outbound_sync(self, gfw_data: Dict[str, Any], gfw_id: int) -> SyncResult:
        """
        Push gofieldwise data to Zapier webhook.
        Zapier will then distribute to connected apps.
        """
        result = SyncResult(success=True, synced_id=str(gfw_id))
        
        # Convert to external format
        external_data = self.field_mapping.to_external(gfw_data)
        external_data["gofieldwise_id"] = gfw_id
        
        webhook_url = self.config_data.get("webhook_url")
        if not webhook_url:
            result.add_error("Zapier webhook URL not configured")
            return result
        
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=external_data)
                response.raise_for_status()
            logger.info(f"Zapier outbound sync completed: {gfw_id}")
        except Exception as e:
            result.add_error(f"Failed to push to Zapier: {str(e)}")
        
        return result


class GoogleSheetsIntegration(RESTIntegration):
    """
    Google Sheets integration for syncing data to/from Google Sheets.
    Uses Google Sheets API for read/write operations.
    
    Features:
    - Inbound: Read updates from Sheet
    - Outbound: Write jobs/estimates/invoices to Sheet
    - Bidirectional: Two-way sync
    - Batch operations: Sync multiple records at once
    """
    
    def authenticate(self) -> bool:
        """Verify Google Sheets credentials are valid."""
        # In production, validate service account or OAuth token
        required_fields = ["spreadsheet_id", "sheet_id"]
        return all(self.config_data.get(field) for field in required_fields)
    
    def get_name(self) -> str:
        return "Google Sheets"
    
    def normalize_webhook_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Google Sheets doesn't use webhooks; data comes via REST API.
        This is for compatibility with base class.
        """
        return self.field_mapping.to_gofieldwise(payload)
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get Google API authentication headers."""
        token = self.config_data.get("access_token")
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}
    
    async def inbound_sync(self, external_data: Dict[str, Any]) -> SyncResult:
        """
        Fetch data from Google Sheet and sync to gofieldwise.
        """
        result = SyncResult(success=True)
        
        try:
            spreadsheet_id = self.config_data.get("spreadsheet_id")
            sheet_name = external_data.get("sheet_name", "Sheet1")
            
            # Fetch from Google Sheets API
            session = await self.get_http_session()
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{sheet_name}"
            response = await session.get(url, headers=self.get_auth_headers())
            response.raise_for_status()
            
            data = response.json()
            result.data = data
            logger.info(f"Fetched from Google Sheets: {sheet_name}")
        except Exception as e:
            result.success = False
            result.add_error(f"Failed to fetch from Google Sheets: {str(e)}")
        
        return result
    
    async def outbound_sync(self, gfw_data: Dict[str, Any], gfw_id: int) -> SyncResult:
        """
        Write gofieldwise data to Google Sheet.
        Appends a new row or updates existing row.
        """
        result = SyncResult(success=True, synced_id=str(gfw_id))
        
        try:
            spreadsheet_id = self.config_data.get("spreadsheet_id")
            sheet_name = gfw_data.get("sheet_name", "Sheet1")
            
            # Convert to external format
            external_data = self.field_mapping.to_external(gfw_data)
            
            # Prepare rows for append
            values = [list(external_data.values())]
            
            # Append to Google Sheets
            session = await self.get_http_session()
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{sheet_name}!A:Z:append"
            
            response = await session.post(
                url,
                headers=self.get_auth_headers(),
                json={"values": values}
            )
            response.raise_for_status()
            
            logger.info(f"Appended to Google Sheets: {sheet_name}")
        except Exception as e:
            result.success = False
            result.add_error(f"Failed to write to Google Sheets: {str(e)}")
        
        return result


class JobberIntegration(RESTIntegration):
    """
    Jobber integration for syncing jobs, customers, and estimates.
    Jobber is a field service management platform (jobber.com).
    
    Features:
    - Inbound: Import jobs/customers from Jobber
    - Outbound: Export gofieldwise jobs to Jobber
    - Bidirectional: Keep both systems in sync
    - Webhooks: Subscribe to Jobber events
    """
    
    def authenticate(self) -> bool:
        """Verify Jobber API credentials."""
        return bool(self.config_data.get("api_token"))
    
    def get_name(self) -> str:
        return "Jobber"
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Jobber uses Basic Auth or Bearer token."""
        token = self.config_data.get("api_token")
        return {"Authorization": f"Bearer {token}"} if token else {}
    
    def normalize_webhook_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Jobber webhooks have specific format."""
        # Extract event data
        data = payload.get("data", payload)
        return self.field_mapping.to_gofieldwise(data)
    
    async def inbound_sync(self, external_data: Dict[str, Any]) -> SyncResult:
        """
        Import job/customer from Jobber.
        """
        result = SyncResult(success=True)
        
        entity_type = external_data.get("type", "unknown")
        logger.info(f"Jobber inbound sync: {entity_type}")
        
        result.data = external_data
        return result
    
    async def outbound_sync(self, gfw_data: Dict[str, Any], gfw_id: int) -> SyncResult:
        """
        Create or update job/customer in Jobber.
        """
        result = SyncResult(success=True, synced_id=str(gfw_id))
        
        try:
            external_data = self.field_mapping.to_external(gfw_data)
            
            # Determine endpoint based on entity type
            entity_type = gfw_data.get("entity_type", "job").lower()
            endpoint = f"https://api.jobber.com/{entity_type}s"
            
            session = await self.get_http_session()
            response = await session.post(
                endpoint,
                headers=self.get_auth_headers(),
                json=external_data
            )
            response.raise_for_status()
            
            response_data = response.json()
            result.data = response_data
            logger.info(f"Jobber outbound sync: {gfw_id}")
        except Exception as e:
            result.success = False
            result.add_error(f"Jobber API error: {str(e)}")
        
        return result
    
    async def fetch_external_record(self, external_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a job/customer from Jobber."""
        try:
            session = await self.get_http_session()
            url = f"https://api.jobber.com/record/{external_id}"
            response = await session.get(url, headers=self.get_auth_headers())
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch from Jobber: {str(e)}")
            return None


class HouseCallIntegration(RESTIntegration):
    """
    HouseCall Pro integration for syncing service calls, customers, invoices.
    HouseCall Pro is a field service app (housecallpro.com).
    
    Features:
    - Inbound: Import customers/jobs from HouseCall
    - Outbound: Export jobs/invoices to HouseCall
    - Bidirectional: Keep both systems in sync
    """
    
    def authenticate(self) -> bool:
        """Verify HouseCall API credentials."""
        return bool(self.config_data.get("api_key"))
    
    def get_name(self) -> str:
        return "HouseCall Pro"
    
    def get_auth_headers(self) -> Dict[str, str]:
        """HouseCall uses API key in header."""
        api_key = self.config_data.get("api_key")
        return {"Authorization": f"Key {api_key}"} if api_key else {}
    
    def normalize_webhook_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """HouseCall webhook payload normalization."""
        event_type = payload.get("type")
        data = payload.get("data", payload)
        normalized = self.field_mapping.to_gofieldwise(data)
        normalized["event_type"] = event_type
        return normalized
    
    async def inbound_sync(self, external_data: Dict[str, Any]) -> SyncResult:
        """
        Import customer/job from HouseCall.
        """
        result = SyncResult(success=True)
        
        event_type = external_data.get("event_type", "unknown")
        logger.info(f"HouseCall inbound sync: {event_type}")
        
        result.data = external_data
        return result
    
    async def outbound_sync(self, gfw_data: Dict[str, Any], gfw_id: int) -> SyncResult:
        """
        Create or update customer/job in HouseCall.
        """
        result = SyncResult(success=True, synced_id=str(gfw_id))
        
        try:
            external_data = self.field_mapping.to_external(gfw_data)
            
            # Determine endpoint based on entity type
            entity_type = gfw_data.get("entity_type", "customer").lower()
            endpoint = f"https://api.housecallpro.com/api/v1/{entity_type}s"
            
            session = await self.get_http_session()
            response = await session.post(
                endpoint,
                headers=self.get_auth_headers(),
                json=external_data
            )
            response.raise_for_status()
            
            response_data = response.json()
            result.data = response_data
            logger.info(f"HouseCall outbound sync: {gfw_id}")
        except Exception as e:
            result.success = False
            result.add_error(f"HouseCall API error: {str(e)}")
        
        return result


class CustomWebhookIntegration(WebhookIntegration):
    """
    Generic custom webhook integration.
    Allows customers to set up webhooks to any system.
    
    Features:
    - Flexible field mapping
    - Custom payload transformation
    - Generic error handling
    """
    
    def authenticate(self) -> bool:
        """Custom webhook just needs a URL."""
        return bool(self.config_data.get("webhook_url"))
    
    def get_name(self) -> str:
        return "Custom Webhook"
    
    def normalize_webhook_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply custom transformation if configured.
        Otherwise, just apply field mapping.
        """
        # Check for custom transformation function
        transform_fn = self.config_data.get("transform_function")
        if transform_fn:
            try:
                # In production, compile and execute transformation safely
                # For now, just apply field mapping
                pass
            except Exception as e:
                logger.error(f"Custom transformation failed: {str(e)}")
        
        return self.field_mapping.to_gofieldwise(payload)
    
    async def inbound_sync(self, external_data: Dict[str, Any]) -> SyncResult:
        """Process generic webhook payload."""
        result = SyncResult(success=True, data=external_data)
        
        logger.info(f"Custom webhook inbound sync: {len(external_data)} fields")
        return result
    
    async def outbound_sync(self, gfw_data: Dict[str, Any], gfw_id: int) -> SyncResult:
        """Push to custom webhook URL."""
        result = SyncResult(success=True, synced_id=str(gfw_id))
        
        try:
            webhook_url = self.config_data.get("webhook_url")
            if not webhook_url:
                result.add_error("Webhook URL not configured")
                return result
            
            external_data = self.field_mapping.to_external(gfw_data)
            external_data["gofieldwise_id"] = gfw_id
            external_data["timestamp"] = __import__("datetime").datetime.utcnow().isoformat()
            
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=external_data)
                response.raise_for_status()
            
            logger.info(f"Custom webhook push to {webhook_url}: {gfw_id}")
        except Exception as e:
            result.success = False
            result.add_error(f"Webhook push failed: {str(e)}")
        
        return result
