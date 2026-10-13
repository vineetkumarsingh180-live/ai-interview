"""
Centralized Application and Gemini Model Configuration.

This module is the single source of truth for model and API configuration:
- API key is read from `GEMINI_API_KEY` in `.env`.
- Model name is read from `GEMINI_MODEL` in `.env`.
- Model name is treated as configurable text (not a fixed enum).
- No fallback or silent model switching is performed.
- If configured model is missing or invalid, a clear backend error is returned
  and a safe diagnostic message is logged without revealing credentials.
"""

import logging
import re
from typing import Optional

from app.shared.config import BACKEND_ROOT, Settings, settings

logger = logging.getLogger("synapse.core.config")


class ModelConfigurationError(Exception):
    """Raised when the configured Gemini model or API key is missing, invalid, or unsupported."""
    pass


def validate_gemini_model(model_name: Optional[str] = None) -> str:
    """
    Validates the configured Gemini model string.

    Ensures the model name:
    1. Is non-empty and non-whitespace.
    2. Does not contain illegal or unsafe characters.
    3. Is treated as configurable text, allowing any model supported by the API/SDK.

    Returns the validated model identifier string.
    Raises ModelConfigurationError if missing or invalid, with safe diagnostic logging.
    """
    raw_model = model_name if model_name is not None else settings.GEMINI_MODEL

    if not raw_model or not str(raw_model).strip():
        safe_msg = (
            "Configured GEMINI_MODEL is missing or empty in .env. "
            "Please configure a valid Gemini model (e.g. GEMINI_MODEL=gemini-2.5-flash)."
        )
        logger.error(safe_msg)
        raise ModelConfigurationError(safe_msg)

    cleaned = str(raw_model).strip()

    # Valid model identifiers: alphanumeric, hyphens, underscores, dots, slashes (e.g. tunedModels/...)
    if not re.match(r"^[a-zA-Z0-9_\-\./]+$", cleaned):
        safe_msg = (
            f"Configured GEMINI_MODEL contains invalid characters: '{cleaned}'. "
            "Expected a valid model identifier (e.g. 'gemini-2.5-flash', 'gemini-1.5-pro')."
        )
        logger.error(safe_msg)
        raise ModelConfigurationError(safe_msg)

    return cleaned


def get_gemini_model() -> str:
    """
    Returns the currently configured Gemini model name after validation.
    Does not silently switch or fallback to any hardcoded model.
    """
    return validate_gemini_model(settings.GEMINI_MODEL)


def get_gemini_api_key() -> str:
    """
    Returns the configured GEMINI_API_KEY.
    Ensures credentials are never logged.
    """
    key = (settings.GEMINI_API_KEY or "").strip()
    if not key:
        safe_msg = "GEMINI_API_KEY is not configured in .env; AI features will be unavailable."
        logger.warning(safe_msg)
        raise ModelConfigurationError(safe_msg)
    return key


def is_gemini_configured() -> bool:
    """
    Checks if both GEMINI_API_KEY and GEMINI_MODEL are configured and valid.
    Never logs secret keys.
    """
    if not (settings.GEMINI_API_KEY or "").strip():
        return False
    try:
        validate_gemini_model(settings.GEMINI_MODEL)
        return True
    except ModelConfigurationError:
        return False


__all__ = [
    "BACKEND_ROOT",
    "Settings",
    "settings",
    "ModelConfigurationError",
    "validate_gemini_model",
    "get_gemini_model",
    "get_gemini_api_key",
    "is_gemini_configured",
]
