# Universal Integration Adapter - Quick Start

## 5-Minute Setup

### 1. Copy Files

Copy these files to your gofieldwise backend:

```
backend/app/
  models/integrations.py          # Database models
  schemas/integrations.py         # Pydantic schemas
  services/integration_adapter.py # Base classes
  services/integrations.py        # Platform integrations
  services/integration_manager.py # Manager/registry
  api/integrations.py             # API endpoints

alembic/versions/
  integration_adapter_001.py      # Database migration

tests/
  test_integrations.py            # Test suite

docs/
  INTEGRATION_ADAPTER_GUIDE.md    # Full documentation
```

### 2. Update FastAPI Factory

Edit `backend/app/factory.py`:

```python
def register_routers(app: FastAPI) -> None:
    """Register all routers"""
    # ... existing imports ...
    from .api.integrations import router as integrations_router
    
    # ... existing router registrations ...
    app.include_router(integrations_router)
```

### 3. Update Models __init__.py

Edit `backend/app/models/__init__.py`:

```python
from .integrations import IntegrationConfig, IntegrationSyncLog
```

### 4. Run Migration

```bash
cd backend
alembic upgrade head
```

### 5. Test Integration

```bash
# Start server
python -m uvicorn app.main:app --reload

# List platforms
curl http://localhost:8000/api/integrations/platforms

# Expected response:
# {
#   "platforms": {
#     "zapier": {...},
#     "google_sheets": {...},
#     ...
#   }
# }
```

Done! Now set up your first integration.

## Create Your First Integration

### Option A: Zapier

```bash
# 1. Get your Zapier webhook URL first

# 2. Create integration
curl -X POST http://localhost:8000/api/integrations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "Zapier - Stripe Payments",
    "platform": "zapier",
    "direction": "inbound",
    "config_data": {
      "webhook_url": "https://hooks.zapier.com/hooks/catch/YOUR_ID"
    },
    "field_mapping": {
      "customer_name": "firstName",
      "customer_email": "email",
      "job_title": "description"
    }
  }'

# 3. You'll get back a webhook_url from gofieldwise
# 4. Use this URL in Zapier actions
```

### Option B: Google Sheets

```bash
# 1. Set up Google Cloud service account
# 2. Get your spreadsheet ID from Google Sheets URL
# 3. Create integration

curl -X POST http://localhost:8000/api/integrations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "Google Sheets - Weekly Jobs",
    "platform": "google_sheets",
    "direction": "outbound",
    "config_data": {
      "spreadsheet_id": "1BxiMVs0XRA5nFMERTMsS6_18ZdrIOqUQq7ATLjwqIQA",
      "sheet_id": 0,
      "access_token": "YOUR_GOOGLE_TOKEN"
    },
    "field_mapping": {
      "customer_name": "Customer Name",
      "customer_email": "Email",
      "job_date": "Scheduled Date"
    }
  }'
```

### Option C: Jobber

```bash
# 1. Get Jobber API token from Settings > Integrations
# 2. Create integration

curl -X POST http://localhost:8000/api/integrations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "Jobber Sync",
    "platform": "jobber",
    "direction": "bidirectional",
    "config_data": {
      "api_token": "YOUR_JOBBER_TOKEN"
    },
    "field_mapping": {
      "customer_name": "firstName",
      "customer_email": "email",
      "job_title": "title",
      "job_date": "startDate"
    }
  }'
```

### Option D: HouseCall Pro

```bash
# 1. Get HouseCall API key from Settings > API
# 2. Create integration

curl -X POST http://localhost:8000/api/integrations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "HouseCall Pro Sync",
    "platform": "housecall_pro",
    "direction": "bidirectional",
    "config_data": {
      "api_key": "YOUR_HOUSECALL_KEY"
    },
    "field_mapping": {
      "customer_name": "customerName",
      "customer_email": "email",
      "job_title": "jobTitle"
    }
  }'
```

### Option E: Custom Webhook

```bash
# 1. Get your external system's webhook URL
# 2. Create integration

curl -X POST http://localhost:8000/api/integrations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "My Custom App",
    "platform": "custom_webhook",
    "direction": "bidirectional",
    "config_data": {
      "webhook_url": "https://myapp.com/webhooks/gofieldwise"
    },
    "field_mapping": {
      "customer_name": "name",
      "customer_email": "email"
    }
  }'
```

## Common Field Mappings

### Zapier
```json
{
  "customer_name": "firstName",
  "customer_email": "email",
  "customer_phone": "phone",
  "job_title": "description",
  "job_date": "date"
}
```

### Google Sheets
```json
{
  "customer_name": "Customer Name",
  "customer_email": "Email Address",
  "job_title": "Service Type",
  "job_date": "Appointment Date"
}
```

### Jobber
```json
{
  "customer_name": "firstName",
  "customer_email": "email",
  "customer_phone": "phone",
  "job_title": "title",
  "job_date": "startDate",
  "job_status": "status"
}
```

### HouseCall Pro
```json
{
  "customer_name": "customerName",
  "customer_email": "customerEmail",
  "customer_phone": "customerPhone",
  "job_title": "jobTitle",
  "job_date": "jobDate"
}
```

## Verify Integration Health

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/integrations/{config_id}/health

# Response:
# {
#   "id": 1,
#   "name": "Zapier - Stripe",
#   "platform": "zapier",
#   "is_active": true,
#   "is_authenticated": true,
#   "last_sync_at": null,
#   "message": "Integration is healthy"
# }
```

## Test Manual Sync

```bash
curl -X POST http://localhost:8000/api/integrations/{config_id}/sync \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "entity_type": "customer",
    "data": {
      "firstName": "John",
      "email": "john@example.com"
    }
  }'

# Response:
# {
#   "success": true,
#   "data": {...},
#   "errors": [],
#   "timestamp": "2024-01-15T12:00:00Z"
# }
```

## Monitor Syncs

```bash
# List integrations
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/integrations

# Get specific integration
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/integrations/{config_id}

# Check database logs (Python)
from app.models.integrations import IntegrationSyncLog
logs = db.query(IntegrationSyncLog).filter(
    IntegrationSyncLog.integration_config_id == 1
).order_by(IntegrationSyncLog.created_at.desc()).limit(10).all()

for log in logs:
    print(f"{log.sync_type}: {log.status} - {log.error_message}")
```

## Troubleshooting

### Integration not authenticating?

```python
# Check credentials in config_data
from app.services.integration_manager import IntegrationRegistry

config = db.query(IntegrationConfig).get(1)
integration_class = IntegrationRegistry.get_integration_class(config.platform.value)
integration = integration_class(config.config_data, config.field_mapping)

print(f"Authenticated: {integration.authenticate()}")
```

### Webhook not working?

1. Check webhook URL is accessible
2. Verify webhook secret (if configured)
3. Check firewall/security settings
4. Review logs in `IntegrationSyncLog`

### Field mapping issues?

```bash
# Test field mapping
curl -X POST http://localhost:8000/api/integrations/{config_id}/sync \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "entity_type": "test",
    "data": {
      "firstName": "Test",
      "email": "test@example.com"
    }
  }'

# Check if mapped correctly in response
```

## Next Steps

1. ✅ Set up integrations (see above)
2. ✅ Verify health checks pass
3. ✅ Test manual syncs
4. ✅ Check sync logs
5. ✅ Configure your external system webhooks
6. ✅ Monitor in production
7. ✅ Set up error notifications (future)

## Performance Tips

- **Batch operations**: Group syncs together
- **Async syncs**: Don't block main app on external API calls
- **Rate limiting**: Implement backoff for failed syncs
- **Caching**: Cache integration configs to reduce DB queries
- **Archiving**: Archive old sync logs after 30 days

## Security Checklist

- [ ] Store API keys in environment variables
- [ ] Encrypt credentials in database
- [ ] Validate webhook secrets
- [ ] Use HTTPS for webhooks
- [ ] Implement rate limiting
- [ ] Audit log all syncs
- [ ] Review access logs periodically
- [ ] Use OAuth where available

## Support

For issues or questions:
1. Check `INTEGRATION_ADAPTER_GUIDE.md` for detailed docs
2. Review sync logs in database
3. Enable debug logging:
   ```python
   import logging
   logging.getLogger("app.services").setLevel(logging.DEBUG)
   ```
4. Check individual platform documentation links

Have fun integrating! 🚀
