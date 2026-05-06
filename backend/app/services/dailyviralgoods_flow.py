from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Any

import httpx


_HTTP_TIMEOUT = 20.0
_SHOPIFY_API_VERSION = "2025-10"


def _env(*names: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value.strip().strip('"').strip("'")
    return ""


def _landbot_token() -> str:
    return _env("LANDBOT_API_TOKEN")


def _airtable_token() -> str:
    return _env("AIRTABLE_PAT", "AIRTABLE_PERSONAL_ACCESS_TOKEN", "Airtable personal access token")


def _airtable_base_id() -> str:
    return _env("AIRTABLE_BASE_ID", "Airtable base ID")


def _airtable_table_name() -> str:
    return _env("AIRTABLE_TABLE_NAME", "Airtable table name")


def _shopify_store_domain() -> str:
    raw = _env("SHOPIFY_STORE_DOMAIN", "SHOPIFY_STORE", "Shopify store domain")
    return raw.replace("https://", "").replace("http://", "").strip().strip("/")


def _shopify_access_token() -> str:
    return _env("SHOPIFY_ADMIN_ACCESS_TOKEN", "SHOPIFY_API_TOKEN", "Shopify admin access token")


def _shopify_headers() -> dict[str, str]:
    token = _shopify_access_token()
    if not token:
        return {}
    return {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}


def _shopify_candidate_domains() -> list[str]:
    primary = _shopify_store_domain()
    candidates: list[str] = []
    if primary:
        candidates.append(primary)
        if primary.endswith(".myshopify.com") and "dailyviralgoods" in primary.lower():
            candidates.append("dailyviralgoods.com")
    unique: list[str] = []
    for candidate in candidates:
        normalized = candidate.replace("https://", "").replace("http://", "").strip().strip("/")
        if normalized and normalized not in unique:
            unique.append(normalized)
    return unique


def _shopify_base_urls() -> list[str]:
    return [f"https://{domain}/admin/api/{_SHOPIFY_API_VERSION}" for domain in _shopify_candidate_domains()]


def _normalize_phone(value: str | None) -> str | None:
    if not value:
        return None
    compact = "".join(ch for ch in value if ch.isdigit() or ch == "+")
    return compact or None


def _to_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        compact = value.strip()
        return compact or None
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        parts = [_to_text(item) for item in value]
        compact = ", ".join(item for item in parts if item)
        return compact or None
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=True)
    return str(value).strip() or None


def _flatten_payload(data: Any, prefix: str = "") -> dict[str, str]:
    flattened: dict[str, str] = {}
    if isinstance(data, Mapping):
        for key, value in data.items():
            key_text = str(key).strip()
            next_prefix = f"{prefix}.{key_text}" if prefix else key_text
            flattened.update(_flatten_payload(value, next_prefix))
    elif isinstance(data, list):
        for idx, value in enumerate(data):
            next_prefix = f"{prefix}[{idx}]"
            flattened.update(_flatten_payload(value, next_prefix))
    else:
        text = _to_text(data)
        if prefix and text:
            flattened[prefix] = text
    return flattened


def _pick_first(flattened: dict[str, str], *candidates: str) -> str | None:
    lowered = {key.lower(): value for key, value in flattened.items() if value}
    for candidate in candidates:
        for key, value in lowered.items():
            if candidate in key:
                return value
    return None


def normalize_landbot_payload(payload: dict[str, Any]) -> dict[str, Any]:
    source_payload = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload
    flattened = _flatten_payload(source_payload)

    full_name = _pick_first(flattened, "full_name", "fullname", "name")
    email = _pick_first(flattened, "email")
    phone = _normalize_phone(_pick_first(flattened, "phone", "mobile", "whatsapp"))
    product = _pick_first(flattened, "product", "sku", "offer", "item")
    message = _pick_first(flattened, "message", "notes", "comment", "problem", "question")
    source = _pick_first(flattened, "source", "campaign", "channel", "medium") or "landbot"
    session_id = _pick_first(flattened, "session", "conversation", "contact_id", "visitor")
    opt_in = _pick_first(flattened, "optin", "opt_in", "marketing")

    first_name = _pick_first(flattened, "first_name", "firstname")
    last_name = _pick_first(flattened, "last_name", "lastname")
    if not first_name and full_name:
        parts = full_name.split()
        first_name = parts[0]
        if len(parts) > 1:
            last_name = " ".join(parts[1:])
    if not full_name and first_name:
        full_name = " ".join(part for part in [first_name, last_name] if part).strip() or None

    return {
        "full_name": full_name,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone,
        "product": product,
        "message": message,
        "source": source,
        "session_id": session_id,
        "marketing_opt_in": opt_in,
        "flattened_payload": flattened,
        "raw_payload": source_payload,
    }


def _airtable_headers() -> dict[str, str]:
    token = _airtable_token()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _fetch_airtable_field_names(client: httpx.Client) -> list[str]:
    base_id = _airtable_base_id()
    table_name = _airtable_table_name()
    if not base_id or not table_name:
        return []
    try:
        resp = client.get(f"https://api.airtable.com/v0/meta/bases/{base_id}/tables")
        if resp.status_code >= 400:
            return []
        data = resp.json()
        for table in data.get("tables", []):
            table_id = str(table.get("id", "")).strip().lower()
            table_label = str(table.get("name", "")).strip().lower()
            target = table_name.strip().lower()
            if table_id == target or table_label == target:
                return [str(field.get("name", "")).strip() for field in table.get("fields", []) if field.get("name")]
    except Exception:
        return []
    return []


def _airtable_field_map(normalized: dict[str, Any], available_fields: list[str]) -> dict[str, Any]:
    available = {field.strip().lower(): field for field in available_fields if field.strip()}
    mapped: dict[str, Any] = {}

    candidates: dict[str, list[Any]] = {
        "name": [normalized.get("full_name")],
        "full name": [normalized.get("full_name")],
        "first name": [normalized.get("first_name")],
        "last name": [normalized.get("last_name")],
        "email": [normalized.get("email")],
        "phone": [normalized.get("phone")],
        "mobile": [normalized.get("phone")],
        "product": [normalized.get("product")],
        "product interest": [normalized.get("product")],
        "offer": [normalized.get("product")],
        "message": [normalized.get("message")],
        "notes": [normalized.get("message")],
        "source": [normalized.get("source")],
        "lead source": [normalized.get("source")],
        "channel": [normalized.get("source")],
        "status": ["New"],
        "session id": [normalized.get("session_id")],
        "landbot session id": [normalized.get("session_id")],
        "marketing opt in": [normalized.get("marketing_opt_in")],
        "raw payload": [json.dumps(normalized.get("raw_payload", {}), ensure_ascii=True)],
    }

    for logical_name, values in candidates.items():
        actual = available.get(logical_name)
        value = next((item for item in values if item not in (None, "")), None)
        if actual and value is not None:
            mapped[actual] = value

    return mapped


def push_to_airtable(normalized: dict[str, Any]) -> tuple[bool, str | None, str | None]:
    token = _airtable_token()
    base_id = _airtable_base_id()
    table_name = _airtable_table_name()
    if not token or not base_id or not table_name:
        return False, None, "Airtable configuration is incomplete"

    with httpx.Client(headers=_airtable_headers(), timeout=_HTTP_TIMEOUT) as client:
        field_names = _fetch_airtable_field_names(client)
        fields = _airtable_field_map(normalized, field_names)
        if not fields:
            fields = {
                "Name": normalized.get("full_name") or "Landbot Lead",
                "Email": normalized.get("email"),
                "Lead Source": normalized.get("source") or "landbot",
                "Status": "New",
            }
            fields = {key: value for key, value in fields.items() if value not in (None, "")}

        payload = {"records": [{"fields": fields}]}
        resp = client.post(f"https://api.airtable.com/v0/{base_id}/{table_name}", json=payload)
        if resp.status_code >= 400:
            return False, None, f"Airtable error {resp.status_code}"
        data = resp.json()
        records = data.get("records", [])
        record_id = records[0].get("id") if records else None
        return True, str(record_id) if record_id else None, None


def _shopify_search_customer(client: httpx.Client, *, base_url: str, email: str | None, phone: str | None) -> dict[str, Any] | None:
    query = None
    if email:
        query = f"email:{email}"
    elif phone:
        query = f"phone:{phone}"
    if not query:
        return None
    resp = client.get(f"{base_url}/customers/search.json", params={"query": query})
    if resp.status_code >= 400:
        return None
    try:
        payload = resp.json()
    except ValueError:
        return None
    customers = payload.get("customers", []) if isinstance(payload, dict) else []
    return customers[0] if customers else None


def sync_to_shopify(normalized: dict[str, Any], *, airtable_record_id: str | None = None) -> tuple[bool, str | None, str | None]:
    token = _shopify_access_token()
    email = normalized.get("email")
    phone = normalized.get("phone")
    base_urls = _shopify_base_urls()
    if not base_urls or not token:
        return False, None, "Shopify configuration is incomplete"
    if not email and not phone:
        return False, None, "Shopify sync requires email or phone"

    note_parts = [
        "Captured from Landbot on dailyviralgoods.com",
        f"Source: {normalized.get('source') or 'landbot'}",
    ]
    if normalized.get("product"):
        note_parts.append(f"Product: {normalized['product']}")
    if normalized.get("message"):
        note_parts.append(f"Message: {normalized['message']}")
    if airtable_record_id:
        note_parts.append(f"Airtable Record: {airtable_record_id}")

    customer_payload = {
        "first_name": normalized.get("first_name"),
        "last_name": normalized.get("last_name"),
        "email": email,
        "phone": phone,
        "tags": "dailyviralgoods,landbot-lead",
        "note": "\n".join(note_parts),
    }
    customer_payload = {key: value for key, value in customer_payload.items() if value not in (None, "")}

    headers = _shopify_headers()
    with httpx.Client(headers=headers, timeout=_HTTP_TIMEOUT) as client:
        last_error = "Shopify sync failed"
        for base_url in base_urls:
            existing = _shopify_search_customer(client, base_url=base_url, email=email, phone=phone)
            if existing and existing.get("id"):
                resp = client.put(
                    f"{base_url}/customers/{existing['id']}.json",
                    json={"customer": {"id": existing["id"], **customer_payload}},
                )
            else:
                resp = client.post(f"{base_url}/customers.json", json={"customer": customer_payload})
            if resp.status_code < 400:
                try:
                    payload = resp.json()
                except ValueError:
                    return False, None, "Shopify returned a non-JSON success response"
                customer = payload.get("customer") or {} if isinstance(payload, dict) else {}
                customer_id = customer.get("id")
                return True, str(customer_id) if customer_id else None, None
            last_error = f"Shopify error {resp.status_code}"
            if resp.status_code not in {401, 403, 404}:
                break
        return False, None, last_error


def healthcheck() -> dict[str, Any]:
    landbot_configured = bool(_landbot_token())
    airtable_configured = bool(_airtable_token() and _airtable_base_id() and _airtable_table_name())
    shopify_configured = bool(_shopify_candidate_domains() and _shopify_access_token())
    airtable_reachable = False
    shopify_reachable = False
    notes: list[str] = []

    if airtable_configured:
        try:
            with httpx.Client(headers=_airtable_headers(), timeout=_HTTP_TIMEOUT) as client:
                resp = client.get(f"https://api.airtable.com/v0/{_airtable_base_id()}/{_airtable_table_name()}", params={"maxRecords": 1})
                airtable_reachable = 200 <= resp.status_code < 300
                if not airtable_reachable:
                    notes.append(f"Airtable returned {resp.status_code}")
        except Exception as exc:
            notes.append(f"Airtable connectivity issue: {type(exc).__name__}")

    if shopify_configured:
        try:
            with httpx.Client(headers=_shopify_headers(), timeout=_HTTP_TIMEOUT) as client:
                for base_url in _shopify_base_urls():
                    resp = client.get(f"{base_url}/shop.json")
                    if 200 <= resp.status_code < 300:
                        shopify_reachable = True
                        break
                    notes.append(f"Shopify returned {resp.status_code} for shop endpoint")
        except Exception as exc:
            notes.append(f"Shopify connectivity issue: {type(exc).__name__}")

    ok = landbot_configured and airtable_configured and shopify_configured and airtable_reachable and shopify_reachable
    return {
        "ok": ok,
        "landbot_configured": landbot_configured,
        "airtable_configured": airtable_configured,
        "shopify_configured": shopify_configured,
        "airtable_reachable": airtable_reachable,
        "shopify_reachable": shopify_reachable,
        "airtable_table": _airtable_table_name() or None,
        "shopify_store_domain": _shopify_candidate_domains()[0] if _shopify_candidate_domains() else None,
        "notes": notes,
    }
