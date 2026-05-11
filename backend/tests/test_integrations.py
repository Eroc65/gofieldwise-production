"""
Tests for universal integration adapter.
Tests for adapters, managers, and API endpoints.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime

# Tests for BaseIntegration and DataMapping

def test_data_mapping_to_external():
    """Test converting gofieldwise data to external format."""
    from app.services.integration_adapter import DataMapping
    
    mapping = DataMapping({
        "customer_name": "fullName",
        "customer_email": "email",
        "job_title": "serviceType",
    })
    
    gfw_data = {
        "customer_name": "John Doe",
        "customer_email": "john@example.com",
        "job_title": "Plumbing",
    }
    
    external_data = mapping.to_external(gfw_data)
    
    assert external_data["fullName"] == "John Doe"
    assert external_data["email"] == "john@example.com"
    assert external_data["serviceType"] == "Plumbing"


def test_data_mapping_to_gofieldwise():
    """Test converting external data to gofieldwise format."""
    from app.services.integration_adapter import DataMapping
    
    mapping = DataMapping({
        "customer_name": "fullName",
        "customer_email": "email",
    })
    
    external_data = {
        "fullName": "Jane Smith",
        "email": "jane@example.com",
    }
    
    gfw_data = mapping.to_gofieldwise(external_data)
    
    assert gfw_data["customer_name"] == "Jane Smith"
    assert gfw_data["customer_email"] == "jane@example.com"


def test_sync_result():
    """Test SyncResult data structure."""
    from app.services.integration_adapter import SyncResult
    
    result = SyncResult(success=True, synced_id="ext_123")
    result.data = {"key": "value"}
    result.add_warning("Test warning")
    
    assert result.success is True
    assert result.synced_id == "ext_123"
    assert "Test warning" in result.warnings
    assert len(result.errors) == 0


def test_sync_result_with_error():
    """Test SyncResult with errors."""
    from app.services.integration_adapter import SyncResult
    
    result = SyncResult(success=False)
    result.add_error("Failed to authenticate")
    result.add_warning("Retry after 60 seconds")
    
    assert result.success is False
    assert "Failed to authenticate" in result.errors
    assert len(result.warnings) == 1


# Tests for ZapierIntegration

def test_zapier_integration_authenticate():
    """Test Zapier integration authentication."""
    from app.services.integrations import ZapierIntegration
    
    config_data = {"webhook_url": "https://hooks.zapier.com/..."}
    integration = ZapierIntegration(config_data, {})
    
    assert integration.authenticate() is True


def test_zapier_integration_normalize():
    """Test Zapier webhook payload normalization."""
    from app.services.integrations import ZapierIntegration
    
    field_mapping = {
        "customer_name": "fullName",
        "customer_email": "email",
    }
    
    integration = ZapierIntegration({}, field_mapping)
    
    payload = {
        "fullName": "John Doe",
        "email": "john@example.com",
    }
    
    normalized = integration.normalize_webhook_payload(payload)
    
    assert normalized["customer_name"] == "John Doe"
    assert normalized["customer_email"] == "john@example.com"


# Tests for GoogleSheetsIntegration

def test_google_sheets_integration_authenticate():
    """Test Google Sheets integration authentication."""
    from app.services.integrations import GoogleSheetsIntegration
    
    config_data = {
        "spreadsheet_id": "abc123",
        "sheet_id": 0,
        "access_token": "token123"
    }
    
    integration = GoogleSheetsIntegration(config_data, {})
    assert integration.authenticate() is True


def test_google_sheets_integration_missing_config():
    """Test Google Sheets with missing config."""
    from app.services.integrations import GoogleSheetsIntegration
    
    integration = GoogleSheetsIntegration({}, {})
    assert integration.authenticate() is False


# Tests for JobberIntegration

def test_jobber_integration_authenticate():
    """Test Jobber integration authentication."""
    from app.services.integrations import JobberIntegration
    
    config_data = {"api_token": "jobber_token_123"}
    integration = JobberIntegration(config_data, {})
    
    assert integration.authenticate() is True


def test_jobber_integration_auth_headers():
    """Test Jobber auth headers."""
    from app.services.integrations import JobberIntegration
    
    config_data = {"api_token": "token123"}
    integration = JobberIntegration(config_data, {})
    
    headers = integration.get_auth_headers()
    assert headers["Authorization"] == "Bearer token123"


# Tests for HouseCallIntegration

def test_housecall_integration_authenticate():
    """Test HouseCall integration authentication."""
    from app.services.integrations import HouseCallIntegration
    
    config_data = {"api_key": "housecall_key_123"}
    integration = HouseCallIntegration(config_data, {})
    
    assert integration.authenticate() is True


def test_housecall_integration_auth_headers():
    """Test HouseCall auth headers."""
    from app.services.integrations import HouseCallIntegration
    
    config_data = {"api_key": "key123"}
    integration = HouseCallIntegration(config_data, {})
    
    headers = integration.get_auth_headers()
    assert headers["Authorization"] == "Key key123"


# Tests for CustomWebhookIntegration

def test_custom_webhook_integration():
    """Test custom webhook integration."""
    from app.services.integrations import CustomWebhookIntegration
    
    config_data = {"webhook_url": "https://external-system.com/webhook"}
    field_mapping = {"customer_name": "name"}
    
    integration = CustomWebhookIntegration(config_data, field_mapping)
    
    assert integration.authenticate() is True
    assert integration.get_name() == "Custom Webhook"


# Tests for IntegrationRegistry

def test_integration_registry_get():
    """Test getting integration class from registry."""
    from app.services.integration_manager import IntegrationRegistry
    
    zapier_class = IntegrationRegistry.get_integration_class("zapier")
    assert zapier_class is not None
    assert zapier_class.__name__ == "ZapierIntegration"


def test_integration_registry_list():
    """Test listing available integrations."""
    from app.services.integration_manager import IntegrationRegistry
    
    available = IntegrationRegistry.list_available()
    
    assert "zapier" in available
    assert "google_sheets" in available
    assert "jobber" in available
    assert "housecall" in available
    assert "custom_webhook" in available


# Tests for IntegrationManager

def test_integration_manager_create():
    """Test creating an integration via manager."""
    from app.services.integration_manager import IntegrationManager
    
    manager = IntegrationManager()
    
    integration = manager.create_integration(
        platform="zapier",
        config_data={"webhook_url": "https://hooks.zapier.com/..."},
        field_mapping={},
        config_id=1
    )
    
    assert integration is not None
    assert integration.get_name() == "Zapier"


def test_integration_manager_caching():
    """Test integration caching."""
    from app.services.integration_manager import IntegrationManager
    
    manager = IntegrationManager()
    
    integration1 = manager.create_integration(
        platform="zapier",
        config_data={"webhook_url": "https://hooks.zapier.com/..."},
        field_mapping={},
        config_id=1
    )
    
    # Get from cache
    integration2 = manager.get_integration(1)
    
    assert integration2 is not None
    assert integration1 is integration2


def test_integration_manager_remove():
    """Test removing integration from cache."""
    from app.services.integration_manager import IntegrationManager
    
    manager = IntegrationManager()
    
    manager.create_integration(
        platform="zapier",
        config_data={"webhook_url": "https://hooks.zapier.com/..."},
        field_mapping={},
        config_id=1
    )
    
    manager.remove_integration(1)
    
    assert manager.get_integration(1) is None


# Tests for API endpoints (these would need test database)

@pytest.mark.asyncio
async def test_zapier_inbound_sync():
    """Test Zapier inbound sync."""
    from app.services.integrations import ZapierIntegration
    
    integration = ZapierIntegration(
        {"webhook_url": "https://hooks.zapier.com/..."},
        {"customer_name": "fullName"}
    )
    
    result = await integration.inbound_sync({
        "customer_name": "John Doe",
        "entity_type": "customer"
    })
    
    assert result.success is True


@pytest.mark.asyncio
async def test_custom_webhook_outbound_sync():
    """Test custom webhook outbound sync."""
    from app.services.integrations import CustomWebhookIntegration
    from app.services.integration_adapter import SyncResult
    
    integration = CustomWebhookIntegration(
        {"webhook_url": "https://external.com/webhook"},
        {"customer_name": "name"}
    )
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = AsyncMock()
        
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )
        
        result = await integration.outbound_sync(
            {"customer_name": "John Doe"},
            gfw_id=123
        )
        
        assert result.success is True
        assert result.synced_id == "123"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
