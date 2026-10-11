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


def is_configured() -> bool:
    return get_provider().is_configured()
