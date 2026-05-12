# CRM Integration Hub - Quick Start Guide

Get up and running in 5 minutes!

---

## 1. Setup (1 minute)

### Copy Files
```bash
# Copy to your gofieldwise-production folder
backend/app/models/crm_hub.py
backend/app/services/crm_adapter.py
backend/app/services/crm_connectors.py
backend/app/services/crm_hub.py
backend/app/schemas/crm_hub.py
backend/app/api/crm_hub.py
alembic/versions/crm_hub_001.py
```

### Register Routes (factory.py)
```python
# Add to backend/app/factory.py
from .api.crm_hub import router as crm_hub_router

def register_routers(app: FastAPI):
    # ... existing routers ...
    app.include_router(crm_hub_router)
```

### Run Migration
```bash
cd backend
alembic upgrade head
```

---

## 2. List Providers (< 1 minute)

```bash
curl http://localhost:8000/api/crm-hub/providers
```

Response shows all 7 available CRMs with requirements.

---

## 3. Create Config (1 minute)

### Housecall Pro (Easiest)
```bash
curl -X POST http://localhost:8000/api/crm-hub/configs \
  -H "Content-Type: application/json" \
  -d '{
    "crm_provider": "housecall_pro",
    "integration_mode": "native_api",
    "name": "My Housecall Pro",
    "config_data": {
      "api_key": "YOUR_HCP_API_KEY"
    },
    "field_mapping": {
      "caller_name": "firstName",
      "caller_phone": "phone",
      "service_type": "title"
    }
  }'
```

### Jobber (OAuth)
```bash
curl -X POST http://localhost:8000/api/crm-hub/configs \
  -H "Content-Type: application/json" \
  -d '{
    "crm_provider": "jobber",
    "integration_mode": "oauth",
    "name": "My Jobber",
    "config_data": {
      "access_token": "YOUR_JOBBER_ACCESS_TOKEN"
    },
    "field_mapping": {
      "caller_name": "name",
      "caller_phone": "phone"
    }
  }'
```

### Google Calendar (OAuth)
```bash
curl -X POST http://localhost:8000/api/crm-hub/configs \
  -H "Content-Type: application/json" \
  -d '{
    "crm_provider": "google_calendar",
    "integration_mode": "oauth",
    "name": "My Google Calendar",
    "config_data": {
      "access_token": "YOUR_GOOGLE_TOKEN",
      "calendar_id": "primary"
    },
    "field_mapping": {
      "caller_name": "summary",
      "service_description": "description"
    }
  }'
```

### Zapier (Simple Webhook)
```bash
curl -X POST http://localhost:8000/api/crm-hub/configs \
  -H "Content-Type: application/json" \
  -d '{
    "crm_provider": "zapier",
    "integration_mode": "webhook",
    "name": "My Zapier",
    "config_data": {
      "webhook_url": "https://hooks.zapier.com/hooks/catch/YOUR_WEBHOOK_ID"
    },
    "field_mapping": {}
  }'
```

Save the returned `id` for next steps.

---

## 4. Test Lead (1 minute)

Verify integration works:

```bash
CONFIG_ID=1  # from previous step

curl -X POST http://localhost:8000/api/crm-hub/configs/$CONFIG_ID/test \
  -H "Content-Type: application/json" \
  -d '{
    "caller_name": "Test Lead",
    "caller_phone": "555-0000",
    "service_type": "Test Service"
  }'
```

Response:
```json
{
  "success": true,
  "message": "Test successful. External ID: job_12345"
}
```

---

## 5. Approve (< 1 minute)

Go live:

```bash
curl -X POST http://localhost:8000/api/crm-hub/configs/$CONFIG_ID/approve \
  -H "Content-Type: application/json" \
  -d '{"approved_by_user_id": 1}'
```

---

## 6. Capture Lead (1 minute)

Now captures go straight to CRM:

```bash
curl -X POST http://localhost:8000/api/crm-hub/intakes \
  -H "Content-Type: application/json" \
  -d '{
    "intake_type": "incoming_call",
    "source": "phone_system",
    "caller_name": "John Smith",
    "caller_phone": "555-0123",
    "caller_email": "john@example.com",
    "service_type": "Plumbing",
    "urgency_level": "high"
  }'
```

Response:
```json
{
  "id": 42,
  "is_processed": false,
  "created_at": "2024-05-11T10:35:00"
}
```

---

## 7. Check Status (< 1 minute)

View overall success:

```bash
curl http://localhost:8000/api/crm-hub/status
```

Response:
```json
{
  "total_crm_configs": 1,
  "active_configs": 1,
  "total_intakes_captured": 5,
  "total_handoffs": 5,
  "successful_handoffs": 5,
  "failed_handoffs": 0,
  "success_rate": 100.0,
  "last_intake_at": "2024-05-11T15:30:00",
  "last_handoff_at": "2024-05-11T15:30:05"
}
```

---

## Common Curl Examples

### List All Configs
```bash
curl http://localhost:8000/api/crm-hub/configs
```

### Get One Config
```bash
curl http://localhost:8000/api/crm-hub/configs/1
```

### View Recent Handoffs
```bash
curl http://localhost:8000/api/crm-hub/handoffs?limit=10
```

### View Recent Intakes
```bash
curl http://localhost:8000/api/crm-hub/intakes?limit=10
```

### Get Config Stats
```bash
curl http://localhost:8000/api/crm-hub/configs/1/stats
```

---

## API Key Locations

| Provider | Key Type | Where to Find |
|----------|----------|---------------|
| Housecall Pro | API Key | Settings → API Keys |
| ServiceTitan | Access Token + Tenant ID + App Key | Settings → Integrations |
| Jobber | OAuth Access Token | App Store → Connected Apps |
| Google Calendar | OAuth Token | Google Cloud Console |
| Google Business | OAuth Token | Google Cloud Console |
| Zapier | Webhook URL | Zap → Webhooks |

---

## What Happens Next

1. ✅ Lead captured (phone/form/chat)
2. ✅ Standardized to universal format
3. ✅ Routed to active CRM
4. ✅ Tries native API first
5. ✅ Falls back to Zapier if API fails
6. ✅ Falls back to manual if both fail
7. ✅ Logged in CRMHandoff for audit trail

---

## Troubleshooting

### Test Lead Failed
- Check API key is correct
- Verify credentials in config_data
- Check internet connection

### Intake Not Processing
- Ensure config is approved (is_active = true)
- Check field_mapping has required fields
- View error_message in response

### Handoff Failed
- Check CRMHandoff table for error_message
- Verify CRM account has available slots/capacity
- Try manual fallback in UI

---

## Next Steps

1. ✅ Complete this quick start (you are here)
2. 📖 Read [CRM_HUB_GUIDE.md](CRM_HUB_GUIDE.md) for full reference
3. 🧪 Write tests (see test examples)
4. 🎨 Build UI (7-step onboarding forms)
5. 📊 Add monitoring & alerts

---

**Time to Production: ~5 minutes** ✨
