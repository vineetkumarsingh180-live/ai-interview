"""
AI provider construction (infrastructure only).

The one place the backend turns configuration into an AIService provider. Business modules never
import this or `aiservice`: they declare ports, and the composition root (`app/core`) binds adapters
that call AIService with the provider built here.

A new provider object is built per call from the current settings, so configuration changes (and
test overrides) take effect immediately; construction is cheap and holds no connection state.
"""

from aiservice import GeminiProvider

from .config import settings


def get_provider() -> GeminiProvider:
    return GeminiProvider(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)


def get_provider_1() -> GeminiProvider:
    if not (settings.GEMINI_API_KEY or "").strip() and not (settings.GEMINI_API_KEY_VOICE_DEFENSE or "").strip():
        return GeminiProvider(api_key="", model=settings.GEMINI_MODEL)
    if not (settings.GEMINI_API_KEY or "").strip():
        return GeminiProvider(api_key="", model=settings.GEMINI_MODEL)
    api_key = (
        (settings.GEMINI_API_KEY_VOICE_DEFENSE or "").strip()
        or (settings.GEMINI_API_KEY_1 or "").strip()
        or (settings.GEMINI_API_KEY or "").strip()
    )
    return GeminiProvider(api_key=api_key, model=settings.GEMINI_MODEL)


def get_provider_voice_defense() -> GeminiProvider:
    return get_provider_1()


def is_configured() -> bool:
    return bool(settings.GEMINI_API_KEY and settings.GEMINI_MODEL and settings.GEMINI_MODEL.strip())


def is_configured_1() -> bool:
    if not (settings.GEMINI_API_KEY or "").strip():
        return False
    key = (
        (settings.GEMINI_API_KEY_VOICE_DEFENSE or "").strip()
        or (settings.GEMINI_API_KEY_1 or "").strip()
        or (settings.GEMINI_API_KEY or "").strip()
    )
    return bool(key and settings.GEMINI_MODEL and settings.GEMINI_MODEL.strip())


def is_configured_voice_defense() -> bool:
    return is_configured_1()

