"""
Shared Gemini REST client.

Infrastructure only: it sends a prepared request body and returns the parsed response. Prompts,
response parsing and fallbacks stay in the owning module's service.
"""

import logging
from typing import Any, Dict, Optional

import httpx

from .config import settings

logger = logging.getLogger("synapse.gemini")

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


async def generate_content(
    payload: Dict[str, Any], *, timeout: float = 15.0, model: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    POST a generateContent request. Returns the parsed JSON body on HTTP 200, otherwise None.

    The API key is sent in the `x-goog-api-key` header (not the URL) so it cannot leak into
    request URLs captured by exception messages or logs. Network errors propagate to the caller,
    whose existing try/except handles the fallback.
    """
    url = f"{_BASE_URL}/{model or settings.GEMINI_MODEL}:generateContent"
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload, headers={"x-goog-api-key": settings.GEMINI_API_KEY})
    if resp.status_code != 200:
        logger.warning("Gemini API returned %s: %s", resp.status_code, resp.text[:300])
        return None
    return resp.json()


def extract_text(response: Optional[Dict[str, Any]]) -> Optional[str]:
    """First text part of a generateContent response, or None when the shape is unexpected."""
    try:
        return response["candidates"][0]["content"]["parts"][0]["text"]  # type: ignore[index]
    except (KeyError, IndexError, TypeError):
        return None


def usage_tokens(response: Optional[Dict[str, Any]]) -> "tuple[Optional[int], Optional[int]]":
    """(prompt_tokens, completion_tokens) as reported by the provider; None when not reported."""
    usage = (response or {}).get("usageMetadata") or {}
    return usage.get("promptTokenCount"), usage.get("candidatesTokenCount")


def is_configured() -> bool:
    return bool(settings.GEMINI_API_KEY)
