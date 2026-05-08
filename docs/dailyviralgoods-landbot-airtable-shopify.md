# DailyViralGoods Landbot -> Airtable -> Shopify Flow

## What is wired

- Backend webhook endpoint accepts Landbot JSON payloads.
- Payload is normalized into common contact fields (`name`, `email`, `phone`, `product`, `message`, `source`).
- Airtable sync writes into the configured base/table using matching field names when available.
- Shopify sync creates or updates a customer record when the payload contains an email or phone number.

## Endpoints

- Health check:
  - `/api/integrations/dailyviralgoods/health`
- Provider-neutral lead capture:
  - `/api/integrations/dailyviralgoods/lead-capture`
- Landbot webhook:
  - `/api/integrations/landbot/dailyviralgoods/webhook`

## Recommended production flow

- `Tidio -> Zapier -> /api/integrations/dailyviralgoods/lead-capture -> Airtable -> Shopify`

Use the provider-neutral endpoint for any future Tidio, Zapier, or other chat automation handoff.

## Optional webhook protection

If `LANDBOT_WEBHOOK_SECRET` is set, send one of:

- `X-Landbot-Secret: <secret>`
- `X-Webhook-Secret: <secret>`
- `Authorization: Bearer <secret>`

## Recommended Landbot payload fields

The webhook is flexible and can infer values from nested payloads, but these names are ideal:

- `name`
- `first_name`
- `last_name`
- `email`
- `phone`
- `product`
- `message`
- `source`
- `session_id`

## Suggested Airtable columns

If these columns exist, the sync will populate them automatically:

- `Name`
- `Full Name`
- `First Name`
- `Last Name`
- `Email`
- `Phone`
- `Product`
- `Offer`
- `Message`
- `Notes`
- `Source`
- `Channel`
- `Session ID`
- `Landbot Session ID`
- `Marketing Opt In`
- `Raw Payload`

## Shopify behavior

- Uses the configured Shopify store connection.
- Searches existing customers by email first, then phone.
- Updates an existing customer if found.
- Creates a new customer if no match exists.
- Adds tags:
  - `dailyviralgoods`
  - `landbot-lead`

## Next deployment step

Deploy the backend that contains:

- `backend/app/api/external_integrations.py`
- `backend/app/services/dailyviralgoods_flow.py`

Then paste the live webhook URL into the final webhook/API step inside Landbot.
