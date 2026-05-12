from __future__ import annotations

import base64
import hashlib
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

_PREFIX = "enc:v1:"


def _fernet() -> Fernet:
    raw_key = os.getenv("CRM_TOKEN_ENCRYPTION_KEY", "").strip()
    if raw_key:
        key = raw_key.encode("utf-8")
    else:
        # Deterministic fallback from SECRET_KEY so dev/test still work.
        secret = os.getenv("SECRET_KEY", "dev-secret-change-me").encode("utf-8")
        key = base64.urlsafe_b64encode(hashlib.sha256(secret).digest())
    return Fernet(key)


def encrypt_secret(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    plain = str(value)
    if not plain:
        return plain
    if plain.startswith(_PREFIX):
        return plain
    token = _fernet().encrypt(plain.encode("utf-8")).decode("utf-8")
    return f"{_PREFIX}{token}"


def decrypt_secret(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    token = str(value)
    if not token:
        return token
    if not token.startswith(_PREFIX):
        # Backward compatibility for existing plain-text tokens.
        return token
    payload = token[len(_PREFIX):]
    try:
        return _fernet().decrypt(payload.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return None

