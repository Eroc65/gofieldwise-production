# CRM Integration Hub - Environment Variables & Configuration

Configure credentials for each CRM provider.

---

## Overview

All credentials should be stored in environment variables, **never hardcoded**.

```bash
# .env file (backend root)
HOUSECALL_PRO_API_KEY=hcp_xxxxxxxxxxxxx
SERVICETITAN_ACCESS_TOKEN=st_xxxxxxxxxxxxx
JOBBER_ACCESS_TOKEN=j_xxxxxxxxxxxxx
GOOGLE_OAUTH_TOKEN=google_xxxxxxxxxxxxx
ZAPIER_WEBHOOK_URL=https://hooks.zapier.com/...
```

---

## Provider-Specific Configuration

### 1. Housecall Pro

#### What You Need
- API Key (not OAuth)

#### How to Get It
1. Log in to Housecall Pro → Settings
2. Go to "Integrations" section
3. Click "API Keys"
4. Generate new key or copy existing
5. Copy the key

#### Environment Variable
```bash
HOUSECALL_PRO_API_KEY=hcp_xxx...
```

#### Config Data (In API)
```json
{
  "config_data": {
    "api_key": "${HOUSECALL_PRO_API_KEY}"
  }
}
```

#### Field Mapping Example
```json
{
  "field_mapping": {
    "caller_name": "firstName",
    "caller_phone": "phone",
    "caller_email": "email",
    "service_type": "title",
    "service_description": "description",
    "urgency_level": "status"
  }
}
```

#### API Docs
https://docs.housecallpro.com/api

#### Testing
```bash
curl https://api.housecallpro.com/customers \
  -H "Authorization: Bearer $HOUSECALL_PRO_API_KEY"
```

---

### 2. ServiceTitan

#### What You Need
- OAuth Access Token (requires OAuth flow)
- Tenant ID
- App Key (custom header)

#### How to Get It
1. Create app in ServiceTitan Developer Portal
2. Use OAuth 2.0 flow to get access token
3. Get Tenant ID from account settings
4. Generate App Key in developer console

#### Environment Variables
```bash
SERVICETITAN_ACCESS_TOKEN=st_access_token_xxx
SERVICETITAN_TENANT_ID=xxx-xxx-xxx-xxx
SERVICETITAN_APP_KEY=st_app_key_xxx
```

#### Config Data (In API)
```json
{
  "config_data": {
    "access_token": "${SERVICETITAN_ACCESS_TOKEN}",
    "tenant_id": "${SERVICETITAN_TENANT_ID}",
    "app_key": "${SERVICETITAN_APP_KEY}"
  }
}
```

#### Field Mapping Example
```json
{
  "field_mapping": {
    "caller_name": "name",
    "caller_phone": "phone",
    "caller_email": "email",
    "service_type": "serviceType",
    "urgency_level": "priority"
  }
}
```

#### Token Refresh
Access tokens expire - implement refresh:
```python
# In crm_connectors.py ServiceTitanAdapter
def refresh_token(self):
    # OAuth refresh token flow
    # Update config_data with new token
    pass
```

#### API Docs
https://servicetitan-api.readme.io/

#### Testing
```bash
curl https://api.servicetitan.com/v2/customers \
  -H "Authorization: Bearer $SERVICETITAN_ACCESS_TOKEN" \
  -H "X-Tenant-ID: $SERVICETITAN_TENANT_ID" \
  -H "X-App-Key: $SERVICETITAN_APP_KEY"
```

---

### 3. Jobber

#### What You Need
- OAuth Access Token
- (Tenant/Account ID in token payload)

#### How to Get It
1. Create OAuth app in Jobber Developer Portal
2. Use OAuth 2.0 flow (redirect to Jobber login)
3. Get authorization code
4. Exchange for access token

#### Environment Variables
```bash
JOBBER_ACCESS_TOKEN=j_access_token_xxx
```

#### Config Data (In API)
```json
{
  "config_data": {
    "access_token": "${JOBBER_ACCESS_TOKEN}"
  }
}
```

#### Field Mapping Example
```json
{
  "field_mapping": {
    "caller_name": "name",
    "caller_phone": "phoneNumber",
    "caller_email": "email",
    "service_type": "title",
    "service_description": "description"
  }
}
```

#### API Docs
https://developer.getjobber.com/

#### Testing (GraphQL)
```bash
curl https://api.jobber.com/graphql \
  -H "Authorization: Bearer $JOBBER_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ viewer { account { id } } }"}'
```

---

### 4. Google Calendar

#### What You Need
- OAuth 2.0 Access Token (from Google Cloud)
- Calendar ID (usually "primary")

#### How to Get It
1. Go to Google Cloud Console
2. Create OAuth 2.0 credentials
3. Set authorized redirect URIs
4. Use OAuth flow to get access token
5. User authorizes calendar access

#### Environment Variables
```bash
GOOGLE_CALENDAR_ACCESS_TOKEN=google_calendar_token_xxx
GOOGLE_CALENDAR_ID=primary
```

#### Config Data (In API)
```json
{
  "config_data": {
    "access_token": "${GOOGLE_CALENDAR_ACCESS_TOKEN}",
    "calendar_id": "${GOOGLE_CALENDAR_ID}"
  }
}
```

#### Field Mapping Example
```json
{
  "field_mapping": {
    "caller_name": "summary",
    "service_description": "description",
    "preferred_time": "startTime"
  }
}
```

#### API Docs
https://developers.google.com/calendar/api

#### Token Refresh
Google tokens expire after 1 hour - refresh:
```python
def refresh_token(self):
    # Use refresh_token from OAuth flow
    # Get new access_token
    pass
```

#### Testing
```bash
curl https://www.googleapis.com/calendar/v3/calendars/primary \
  -H "Authorization: Bearer $GOOGLE_CALENDAR_ACCESS_TOKEN"
```

---

### 5. Google Business Profile

#### What You Need
- OAuth 2.0 Access Token
- Location ID (Google Business account)

#### How to Get It
1. Similar to Google Calendar
2. Use Google Business API scope
3. Get Location ID from account

#### Environment Variables
```bash
GOOGLE_BUSINESS_ACCESS_TOKEN=google_business_token_xxx
GOOGLE_BUSINESS_LOCATION_ID=ChIJ...
```

#### Config Data (In API)
```json
{
  "config_data": {
    "access_token": "${GOOGLE_BUSINESS_ACCESS_TOKEN}",
    "location_id": "${GOOGLE_BUSINESS_LOCATION_ID}"
  }
}
```

#### Field Mapping Example
```json
{
  "field_mapping": {
    "caller_name": "topic",
    "service_description": "content"
  }
}
```

#### API Docs
https://developers.google.com/business/connect/posts-api

#### Testing
```bash
curl https://businessprofileapi.googleapis.com/v1/locations/ChIJ.../posts \
  -H "Authorization: Bearer $GOOGLE_BUSINESS_ACCESS_TOKEN"
```

---

### 6. Zapier (Webhook)

#### What You Need
- Zapier Webhook URL (from Zapier)

#### How to Get It
1. Create new Zap in Zapier.com
2. Choose "Webhooks" trigger
3. Copy the webhook URL
4. Use in gofieldwise integration

#### Environment Variables
```bash
ZAPIER_WEBHOOK_URL=https://hooks.zapier.com/hooks/catch/YOUR_ID/YOUR_SECRET
```

#### Config Data (In API)
```json
{
  "config_data": {
    "webhook_url": "${ZAPIER_WEBHOOK_URL}"
  }
}
```

#### Field Mapping
Not needed for Zapier (sends raw JSON)
```json
{
  "field_mapping": {}
}
```

#### API Docs
https://zapier.com/help/create/code-webhooks/webhook-triggers

#### Testing
```bash
curl -X POST $ZAPIER_WEBHOOK_URL \
  -H "Content-Type: application/json" \
  -d '{
    "caller_name": "Test",
    "caller_phone": "555-0000"
  }'
```

---

### 7. Custom Webhook (Advanced)

Use any webhook URL for custom integrations.

#### Config Data
```json
{
  "config_data": {
    "webhook_url": "https://your-api.com/webhook",
    "webhook_auth_type": "bearer",  // or "api_key"
    "webhook_auth_value": "YOUR_TOKEN"
  }
}
```

---

## Setup Instructions

### Step 1: Create .env File

```bash
# backend/.env
HOUSECALL_PRO_API_KEY=hcp_xxx
SERVICETITAN_ACCESS_TOKEN=st_xxx
SERVICETITAN_TENANT_ID=xxx
SERVICETITAN_APP_KEY=st_xxx
JOBBER_ACCESS_TOKEN=j_xxx
GOOGLE_CALENDAR_ACCESS_TOKEN=google_xxx
GOOGLE_CALENDAR_ID=primary
GOOGLE_BUSINESS_ACCESS_TOKEN=google_xxx
GOOGLE_BUSINESS_LOCATION_ID=ChIJ...
ZAPIER_WEBHOOK_URL=https://hooks.zapier.com/...
```

### Step 2: Load in Python

```python
# backend/app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    housecall_pro_api_key: str
    servicetitan_access_token: str
    servicetitan_tenant_id: str
    servicetitan_app_key: str
    jobber_access_token: str
    google_calendar_access_token: str
    google_calendar_id: str
    google_business_access_token: str
    google_business_location_id: str
    zapier_webhook_url: str
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### Step 3: Use in Adapters

```python
# backend/app/services/crm_connectors.py
from ..core.config import settings

class HousecallProAdapter(APIBasedCRMAdapter):
    def __init__(self):
        self.api_key = settings.housecall_pro_api_key
        super().__init__()
```

### Step 4: Never Commit .env

```bash
# .gitignore
.env
.env.local
.env.*.local
```

---

## Token Refresh Strategy

### For OAuth Providers (ServiceTitan, Jobber, Google)

Token expiration handling:

```python
async def _refresh_token_if_needed(self, config):
    """Refresh OAuth token if expired."""
    if is_token_expired(config["access_token"]):
        new_token = await self.refresh_oauth_token(
            config["refresh_token"],
            config["oauth_client_id"],
            config["oauth_client_secret"]
        )
        # Update config_data in database
        config["access_token"] = new_token
        db.add(config)
        db.commit()
```

Store refresh tokens too:
```json
{
  "config_data": {
    "access_token": "short_lived",
    "refresh_token": "long_lived",
    "token_expires_at": "2024-05-11T15:00:00"
  }
}
```

---

## Security Best Practices

✅ **DO:**
- Store all credentials in environment variables
- Use .env files locally only (never commit)
- Rotate API keys monthly
- Use OAuth with expiration times
- Encrypt tokens at rest (use Django/FastAPI encryption)
- Log token usage, not token values
- Use different keys per environment (dev, staging, prod)

❌ **DON'T:**
- Hardcode API keys in code
- Print tokens in logs
- Commit .env files
- Share credentials via email
- Use same key for multiple environments
- Store passwords instead of API keys

---

## Multi-Environment Setup

### Development
```bash
# backend/.env.local
HOUSECALL_PRO_API_KEY=hcp_test_key_xxx
# Test/sandbox credentials
```

### Staging
```bash
# backend/.env.staging
HOUSECALL_PRO_API_KEY=hcp_staging_key_xxx
# Real credentials, test account
```

### Production
```bash
# Deployed as environment variables in your host
# Never use .env files in production
# Use:
# - AWS Secrets Manager
# - GCP Secret Manager
# - Azure Key Vault
# - HashiCorp Vault
```

---

## Troubleshooting

### "API Key Invalid"
- Check key is correct (copy/paste mistakes?)
- Check key hasn't been rotated
- Check key has required permissions
- Test key directly with provider's API

### "OAuth Token Expired"
- Implement token refresh
- Check token expiration time
- Manually refresh and update .env

### "Connection Refused"
- Check internet connection
- Check provider API endpoint is correct
- Check firewall rules

### "Field Not Found in CRM"
- Check field_mapping is correct
- Check field exists in provider
- Check field name (case-sensitive?)
- Check user permissions to access field

---

## Examples

### Full Housecall Pro Setup

```bash
# 1. Get API key from HCP Settings
# 2. Add to .env
HOUSECALL_PRO_API_KEY=hcp_abc123def456

# 3. Create config via API
curl -X POST http://localhost:8000/api/crm-hub/configs \
  -H "Content-Type: application/json" \
  -d '{
    "crm_provider": "housecall_pro",
    "integration_mode": "native_api",
    "name": "My HCP Integration",
    "config_data": {
      "api_key": "'$HOUSECALL_PRO_API_KEY'"
    },
    "field_mapping": {
      "caller_name": "firstName",
      "caller_phone": "phone"
    }
  }'
```

### Full Jobber Setup

```bash
# 1. Create OAuth app at https://developer.getjobber.com
# 2. Get access token via OAuth flow
# 3. Add to .env
JOBBER_ACCESS_TOKEN=j_access_token_xyz

# 4. Create config
curl -X POST http://localhost:8000/api/crm-hub/configs \
  -H "Content-Type: application/json" \
  -d '{
    "crm_provider": "jobber",
    "integration_mode": "oauth",
    "name": "My Jobber Integration",
    "config_data": {
      "access_token": "'$JOBBER_ACCESS_TOKEN'"
    },
    "field_mapping": {
      "caller_name": "name",
      "caller_phone": "phoneNumber"
    }
  }'
```

---

## Monitoring Credentials

```python
# Monitor API usage
def log_api_call(provider, endpoint, status_code):
    logger.info(f"{provider} {endpoint}: {status_code}")

# Don't log credentials!
def sanitize_config(config):
    """Remove sensitive data before logging."""
    return {
        "api_key": "***",
        "access_token": "***",
        "webhook_url": "https://...[hidden]"
    }
```

---

**Credentials Setup Complete** ✅

Now you're ready to create CRM configs!
