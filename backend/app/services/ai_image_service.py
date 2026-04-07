from __future__ import annotations

import os
from dataclasses import dataclass

import httpx


_OPENAI_IMAGES_URL = "https://api.openai.com/v1/images/generations"
_ALLOWED_SIZES = {"1024x1024", "1536x1024", "1024x1536"}
_ALLOWED_QUALITY = {"low", "medium", "high"}
_DEFAULT_MODEL = "gpt-image-1"


@dataclass(frozen=True)
class GeneratedMarketingImage:
    model: str
    mime_type: str
    image_base64: str
    revised_prompt: str | None


def generate_marketing_image(*, prompt: str, size: str = "1024x1024", quality: str = "high") -> GeneratedMarketingImage:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    normalized_size = size.strip().lower()
    if normalized_size not in _ALLOWED_SIZES:
        raise ValueError("size must be one of 1024x1024, 1536x1024, or 1024x1536")

    normalized_quality = quality.strip().lower()
    if normalized_quality not in _ALLOWED_QUALITY:
        raise ValueError("quality must be one of low, medium, or high")

    model = os.getenv("OPENAI_IMAGE_MODEL", _DEFAULT_MODEL).strip() or _DEFAULT_MODEL

    payload = {
        "model": model,
        "prompt": prompt,
        "size": normalized_size,
        "quality": normalized_quality,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=90.0) as client:
        response = client.post(_OPENAI_IMAGES_URL, headers=headers, json=payload)

    if response.status_code >= 400:
        detail = response.text or f"HTTP {response.status_code}"
        raise RuntimeError(f"OpenAI image generation failed: {detail}")

    body = response.json()
    data = body.get("data") if isinstance(body, dict) else None
    if not data or not isinstance(data, list):
        raise RuntimeError("OpenAI image generation returned an unexpected payload")

    first = data[0] if data else None
    if not isinstance(first, dict):
        raise RuntimeError("OpenAI image generation returned invalid image data")

    image_base64 = first.get("b64_json")
    if not image_base64 or not isinstance(image_base64, str):
        raise RuntimeError("OpenAI image generation did not return base64 image data")

    revised_prompt = first.get("revised_prompt")

    return GeneratedMarketingImage(
        model=model,
        mime_type="image/png",
        image_base64=image_base64,
        revised_prompt=revised_prompt if isinstance(revised_prompt, str) else None,
    )
