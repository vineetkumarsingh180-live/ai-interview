"""
Error taxonomy of the provider layer.

Every failure of an AI provider is one of these, so callers can map them to their own states
(unavailable, retry later, bad answer) without parsing messages. Messages never contain secrets.
"""

from typing import Optional


class AIServiceError(Exception):
    """Base class. `code` is a stable machine-readable identifier."""

    code = "ai_error"
    retryable = False

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


class ProviderNotConfigured(AIServiceError):
    """No credentials are available. Nothing was sent anywhere."""

    code = "not_configured"


class ProviderTimeout(AIServiceError):
    code = "timeout"
    retryable = True


class ProviderRateLimited(AIServiceError):
    code = "rate_limited"
    retryable = True

    def __init__(self, message: str, *, retry_after: Optional[float] = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class ProviderUnavailable(AIServiceError):
    """Network failure or a 5xx answer."""

    code = "provider_unavailable"
    retryable = True


class ProviderRejected(AIServiceError):
    """The provider refused the request (bad key, bad model, blocked content). Not retried."""

    code = "provider_rejected"


class InvalidProviderResponse(AIServiceError):
    """The provider answered, but not with a usable, schema-valid payload."""

    code = "invalid_response"
