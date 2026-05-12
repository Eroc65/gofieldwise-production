# Universal Integration Adapter Guide

## Overview

The Universal Integration Adapter is a flexible, extensible framework for connecting gofieldwise to any external system. It supports:

- **Zapier**: Connect to 1000+ apps
- **Google Sheets**: Sync data to/from spreadsheets
- **Jobber**: Field service management platform
- **HouseCall Pro**: Field service app
- **Custom Webhooks**: Generic webhook support for any system

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    External Systems                         │
│  Zapier | Google Sheets | Jobber | HouseCall | Custom App  │
└──────────────────────┬──────────────────────────────────────┘
                       │ Webhooks / REST APIs
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                Integration API Endpoints                    │
│  POST /api/integrations/webhooks/{token}                    │
│  POST /api/integrations/{config_id}/sync                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Integration Manager                            │
│  - Routes to correct integration                            │
│  - Validates webhooks                                       │
│  - Logs all sync operations                                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   ┌─────────┐  ┌─────────┐  ┌─────────────┐
   │Platform │  │Platform │  │Platform     │
   │Adapter  │  │Adapter  │  │Adapter      │
   │Classes  │  │Classes  │  │Classes      │
   └────┬────┘  └────┬────┘  └────┬────────┘
        │            │             │
        └────────────┼─────────────┘
                     ▼
        ┌────────────────────────┐
        │ Data Mapping Engine    │
        │ Field transformation   │
        └────────────┬───────────┘
                     ▼
        ┌────────────────────────┐
        │ gofieldwise Database   │
        │ Jobs, Customers, etc.  │
        └────────────────────────┘
```

## Getting Started

### 1. Database Setup

The adapter uses two new tables:

- **integration_configs**: Stores integration configurations
- **integration_sync_logs**: Audit trail of all sync operations

Alembic migration included. Run:

```bash
alembic upgrade head
```

### 2. Environment Variables

```env
# Zapier
ZAPIER_WEBHOOK_URL=https://hooks.zapier.com/hooks/catch/YOUR_ZAPIER_ID

# Google Sheets
GOOGLE_SHEETS_CREDENTIALS_JSON=/path/to/service_account.json
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id

# Jobber
JOBBER_API_TOKEN=your_jobber_api_token

# HouseCall Pro
HOUSECALL_API_KEY=your_housecall_api_key

# API Base URL (for webhook URLs)
API_BASE_URL=https://your-domain.com
```

### 3. Register Integration Models

Update `backend/app/models/__init__.py`:

```python
from .integrations import IntegrationConfig, IntegrationSyncLog
```

Update `backend/app/api/__init__.py`:

```python
from .integrations import router as integrations_router
```

Register in `backend/app/factory.py`:

```python
def register_routers(app: FastAPI) -> None:
    # ... existing routers ...
    from app.api.integrations import router as integrations_router
    app.include_router(integrations_router)
```

## API Reference

### List Available Platforms

```bash
GET /api/integrations/platforms
```

**Response**:
```json
{
  "platforms": {
    "zapier": {
      "name": "Zapier",
      "description": "Connect to 1000+ apps via Zapier",
      "supported_directions": ["inbound", "outbound", "bidirectional"],
      "requires_config_fields": ["webhook_url"],
      "webhook_capable": true
    },
    "google_sheets": {...},
    "jobber": {...},
    "housecall_pro": {...},
    "custom_webhook": {...}
  }
}
```

### Create Integration

```bash
POST /api/integrations
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
  "name": "My Zapier Connection",
  "platform": "zapier",
  "direction": "bidirectional",
  "config_data": {
    "webhook_url": "https://hooks.zapier.com/hooks/catch/..."
  },
  "field_mapping": {
    "customer_name": "fullName",
    "customer_email": "email",
    "job_title": "jobTitle",
    "job_date": "scheduledDate"
  },
  "webhook_secret": "optional_secret_for_validation"
}
```

**Response**:
```json
{
  "id": 1,
  "organization_id": 1,
  "name": "My Zapier Connection",
  "platform": "zapier",
  "direction": "bidirectional",
  "is_active": true,
  "webhook_url": "https://your-domain.com/api/integrations/webhooks/abc123xyz",
  "last_sync_at": null,
  "last_sync_status": null,
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:30:00"
}
```

### List Integrations

```bash
GET /api/integrations
Authorization: Bearer YOUR_TOKEN
```

### Get Integration Details

```bash
GET /api/integrations/{config_id}
Authorization: Bearer YOUR_TOKEN
```

### Update Integration

```bash
PATCH /api/integrations/{config_id}
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
  "name": "Updated Name",
  "field_mapping": {...}
}
```

### Check Integration Health

```bash
GET /api/integrations/{config_id}/health
Authorization: Bearer YOUR_TOKEN
```

**Response**:
```json
{
  "id": 1,
  "name": "My Zapier Connection",
  "platform": "zapier",
  "is_active": true,
  "is_authenticated": true,
  "last_sync_at": "2024-01-15T12:00:00",
  "last_sync_status": "success",
  "message": "Integration is healthy"
}
```

### Trigger Manual Sync

```bash
POST /api/integrations/{config_id}/sync
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
  "entity_type": "job",
  "data": {
    "fullName": "John Doe",
    "email": "john@example.com",
    "jobTitle": "Plumbing Repair",
    "scheduledDate": "2024-01-20"
  }
}
```

### Receive Webhook

```bash
POST /api/integrations/webhooks/{webhook_token}
Content-Type: application/json

{
  "entity_type": "customer",
  "data": {
    "fullName": "Jane Smith",
    "email": "jane@example.com"
  }
}
```

## Integration Setup

### Zapier Integration

1. **Create a Zapier Zap**:
   - Choose a trigger app (e.g., Stripe, Lead Form, Google Forms)
   - Set action to "Webhooks" → "POST"
   - Get your webhook URL from `/api/integrations`

2. **Configure Mapping**:
   ```json
   {
     "field_mapping": {
       "customer_name": "name",
       "customer_email": "email",
       "job_type": "service_type"
     }
  }
   ```

3. **Set Webhook**:
   - Copy the `webhook_url` from integration response
   - Paste into Zapier webhook action

### Google Sheets Integration

1. **Set Up Google Cloud**:
   - Create service account in Google Cloud Console
   - Download service account JSON
   - Enable Google Sheets API

2. **Configure Integration**:
   ```json
   {
     "config_data": {
       "spreadsheet_id": "your_spreadsheet_id",
       "sheet_id": 0,
       "access_token": "your_token"
     },
     "field_mapping": {
       "customer_name": "Customer Name",
       "customer_email": "Email",
       "job_title": "Job Title"
     }
   }
   ```

3. **Map Data**:
   - Create columns in your sheet matching external field names
   - Integration will append/update rows

### Jobber Integration

1. **Get API Token**:
   - Log in to Jobber
   - Go to Settings → Integrations
   - Generate API token

2. **Configure Integration**:
   ```json
   {
     "config_data": {
       "api_token": "your_jobber_token"
     },
     "field_mapping": {
       "customer_name": "firstName",
       "customer_email": "email",
       "job_title": "title"
     }
   }
   ```

### HouseCall Pro Integration

1. **Get API Key**:
   - Log in to HouseCall Pro
   - Go to Settings → API
   - Generate API key

2. **Configure Integration**:
   ```json
   {
     "config_data": {
       "api_key": "your_housecall_key"
     },
     "field_mapping": {
       "customer_name": "customerName",
       "customer_email": "customerEmail",
       "job_title": "jobTitle"
     }
   }
   ```

### Custom Webhook Integration

1. **Set Up External System**:
   - Configure your external system to POST to the webhook URL
   - Set webhook secret for validation

2. **Configure Integration**:
   ```json
   {
     "config_data": {
       "webhook_url": "https://your-external-system.com/webhook"
     },
     "field_mapping": {
       "customer_name": "name",
       "customer_email": "email"
     },
     "webhook_secret": "your_shared_secret"
   }
   ```

## Field Mapping

Field mapping allows flexible data transformation between gofieldwise and external systems:

```json
{
  "field_mapping": {
    "gofieldwise_field": "external_field",
    "customer_name": "fullName",
    "customer_email": "email",
    "job_title": "serviceType",
    "job_date": "appointmentDate"
  }
}
```

**How it works**:
- **Inbound**: External fields are mapped to gofieldwise fields
- **Outbound**: gofieldwise fields are mapped to external fields
- **Unmapped fields**: Passed through unchanged

## Sync Operations

### Inbound Sync (Webhook)

```
External System → Webhook → gofieldwise Database
```

Automatically triggered when external system POSTs to webhook URL.

### Outbound Sync (Push)

```
gofieldwise → REST API → External System
```

Can be triggered:
- Manually via `/api/integrations/{config_id}/sync`
- Programmatically via integration manager
- Automatically on certain events (future)

### Bidirectional Sync

Data flows both directions:
- Inbound: External changes → gofieldwise
- Outbound: gofieldwise changes → External
- Conflict resolution: Last write wins (configurable)

## Monitoring & Debugging

### View Sync Logs

```python
# Query sync logs
from app.models.integrations import IntegrationSyncLog

logs = db.query(IntegrationSyncLog).filter(
    IntegrationSyncLog.integration_config_id == config_id
).order_by(IntegrationSyncLog.created_at.desc()).limit(100).all()

for log in logs:
    print(f"{log.sync_type}: {log.status} at {log.created_at}")
    if log.error_message:
        print(f"  Error: {log.error_message}")
```

### Check Integration Health

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://your-domain.com/api/integrations/{config_id}/health
```

### Enable Debug Logging

Add to your logging config:

```python
logging.getLogger("app.services.integration_manager").setLevel(logging.DEBUG)
logging.getLogger("app.services.integrations").setLevel(logging.DEBUG)
```

## Advanced Usage

### Custom Integration

Extend `BaseIntegration` to create custom integrations:

```python
from app.services.integration_adapter import BaseIntegration, SyncResult

class MyCustomIntegration(BaseIntegration):
    def authenticate(self) -> bool:
        # Verify credentials
        return True
    
    def get_name(self) -> str:
        return "My Custom System"
    
    def normalize_webhook_payload(self, payload: dict) -> dict:
        # Transform external format to gofieldwise
        return self.field_mapping.to_gofieldwise(payload)
    
    async def inbound_sync(self, external_data: dict) -> SyncResult:
        # Process inbound data
        result = SyncResult(success=True)
        # ... your logic ...
        return result
    
    async def outbound_sync(self, gfw_data: dict, gfw_id: int) -> SyncResult:
        # Push to external system
        result = SyncResult(success=True, synced_id=str(gfw_id))
        # ... your logic ...
        return result
```

Register your integration:

```python
from app.services.integration_manager import IntegrationRegistry

IntegrationRegistry.register("my_custom", MyCustomIntegration)
```

### Programmatic Usage

```python
from app.services.integration_manager import get_manager

manager = get_manager()

# Create integration
integration = manager.create_integration(
    platform="zapier",
    config_data={"webhook_url": "..."},
    field_mapping={...},
    config_id=1
)

# Sync outbound
result = await manager.sync_outbound(
    integration=integration,
    gfw_data={"customer_name": "John"},
    gfw_id=123
)

print(f"Sync {'succeeded' if result.success else 'failed'}")
```

## Troubleshooting

### Integration Not Authenticating

1. Verify API credentials are correct
2. Check environment variables are set
3. Verify network connectivity to external service
4. Review integration health endpoint

### Webhook Not Received

1. Verify webhook URL is correct and accessible
2. Check firewall/networking rules
3. Enable webhook secret validation if needed
4. Review sync logs for errors

### Field Mapping Issues

1. Verify external field names are correct
2. Check data types match (string, number, date, etc.)
3. Test mapping with manual sync
4. Review request/response payloads in sync logs

### Performance Issues

1. Implement batch operations for large datasets
2. Use appropriate sync frequency
3. Index database columns used in filtering
4. Monitor sync log table size; archive old logs

## Security Considerations

1. **Store credentials securely**:
   - Use environment variables for API keys
   - Encrypt credentials in database
   - Never commit secrets to git

2. **Validate webhooks**:
   - Use webhook secrets for validation
   - Verify HTTPS certificates
   - Implement rate limiting

3. **Audit trails**:
   - All syncs are logged to `integration_sync_logs`
   - Review logs for suspicious activity
   - Archive logs periodically

4. **Access control**:
   - Integrations are scoped to organizations
   - Users can only access their org's integrations
   - Use API tokens/OAuth for authentication

## Best Practices

1. **Test field mapping** before production
2. **Start with inbound** webhooks first
3. **Monitor sync health** with health checks
4. **Archive old logs** to prevent table bloat
5. **Document custom field mappings** for your team
6. **Implement error notifications** when syncs fail
7. **Rate limit** webhook endpoints
8. **Validate all external data** before saving

## Support & Resources

- **Integrations API**: `/api/integrations/platforms`
- **Webhooks**: `/api/integrations/webhooks/{token}`
- **Sync Logs**: Query `IntegrationSyncLog` model
- **Debug**: Enable logging via environment variables
- **Documentation**: See individual platform guides above
