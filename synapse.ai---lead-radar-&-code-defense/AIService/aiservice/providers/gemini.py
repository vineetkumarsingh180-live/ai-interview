"""
Gemini provider (Google Generative Language REST API).

The only module in the project that knows the Gemini wire format. The API key is sent in the
`x-goog-api-key` header (never in the URL) and is never logged. Transient failures (timeouts,
429, 5xx, network errors) are retried a bounded number of times with exponential backoff; permanent
failures are raised immediately.
"""

import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, Optional

import httpx

from ..errors import (
    InvalidProviderResponse,
    ProviderNotConfigured,
    ProviderRateLimited,
    ProviderRejected,
    ProviderTimeout,
    ProviderUnavailable,
)
from .base import Generation, Usage

logger = logging.getLogger("aiservice.gemini")

DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = "gemini-2.5-flash"
_MAX_RETRY_AFTER = 10.0


class GeminiProvider:
    name = "gemini"

    def __init__(
        self,
        *,
        api_key: str = "",
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 20.0,
        max_retries: int = 2,
        backoff_base: float = 0.5,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if max_retries < 0 or timeout <= 0:
            raise ValueError("max_retries must be >= 0 and timeout > 0")
        self._api_key = (api_key or "").strip()
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._transport = transport
        self._sleep = sleep

    # ---- identity ------------------------------------------------------------------------
    @property
    def model(self) -> str:
        return self._model

    def is_configured(self) -> bool:
        return bool(self._api_key)

    def __repr__(self) -> str:  # the key must never appear in logs or tracebacks
        return f"GeminiProvider(model={self._model!r}, configured={self.is_configured()})"

    # ---- public generation API -----------------------------------------------------------
    async def generate_text(
        self,
        *,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.3,
        max_output_tokens: Optional[int] = None,
    ) -> Generation:
        config: Dict[str, Any] = {"temperature": temperature}
        if max_output_tokens:
            config["maxOutputTokens"] = max_output_tokens
        return await self._generate(prompt, system, config)

    async def generate_json(
        self, *, prompt: str, system: Optional[str] = None, temperature: float = 0.1
    ) -> Generation:
        return await self._generate(prompt, system, {"temperature": temperature, "responseMimeType": "application/json"})

    # ---- internals -----------------------------------------------------------------------
    async def _generate(self, prompt: str, system: Optional[str], config: Dict[str, Any]) -> Generation:
        if not self.is_configured():
            raise ProviderNotConfigured("GEMINI_API_KEY is not configured.")
        body: Dict[str, Any] = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": config}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        data = await self._post_with_retries(body)
        return self._to_generation(data)

    async def _post_with_retries(self, body: Dict[str, Any]) -> Dict[str, Any]:
        last: Exception = ProviderUnavailable("The provider could not be reached.")
        for attempt in range(self._max_retries + 1):
            try:
                return await self._post_once(body)
            except (ProviderTimeout, ProviderRateLimited, ProviderUnavailable) as exc:
                last = exc
                if attempt == self._max_retries:
                    break
                delay = self._backoff_base * (2**attempt)
                if isinstance(exc, ProviderRateLimited) and exc.retry_after is not None:
                    delay = max(delay, min(exc.retry_after, _MAX_RETRY_AFTER))
                logger.warning("Gemini call failed (%s); retry %d/%d in %.1fs", exc.code, attempt + 1, self._max_retries, delay)
                await self._sleep(delay)
        raise last

    async def _post_once(self, body: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self._base_url}/{self._model}:generateContent"
        try:
            async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
                resp = await client.post(url, json=body, headers={"x-goog-api-key": self._api_key})
        except httpx.TimeoutException as exc:
            raise ProviderTimeout("The provider did not answer in time.") from exc
        except httpx.TransportError as exc:
            raise ProviderUnavailable("The provider could not be reached.") from exc

        status = resp.status_code
        if status == 200:
            try:
                data = resp.json()
            except ValueError as exc:
                raise InvalidProviderResponse("The provider answered with a non-JSON body.") from exc
            if not isinstance(data, dict):
                raise InvalidProviderResponse("The provider answered with an unexpected body.")
            return data
        if status == 429:
            raise ProviderRateLimited("The provider rate limit was hit.", retry_after=_retry_after(resp))
        if status >= 500:
            raise ProviderUnavailable(f"The provider failed with HTTP {status}.")
        raise ProviderRejected(f"The provider rejected the request (HTTP {status}).")

    def _to_generation(self, data: Dict[str, Any]) -> Generation:
        block = (data.get("promptFeedback") or {}).get("blockReason")
        if block:
            raise InvalidProviderResponse(f"The provider blocked the prompt ({block}).")
        try:
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
        except (KeyError, IndexError, TypeError) as exc:
            raise InvalidProviderResponse("The provider answered without any text.") from exc
        if not text.strip():
            raise InvalidProviderResponse("The provider answered with empty text.")
        usage = data.get("usageMetadata") or {}
        return Generation(
            text=text,
            model=self._model,
            usage=Usage(usage.get("promptTokenCount"), usage.get("candidatesTokenCount")),
        )


def _retry_after(resp: httpx.Response) -> Optional[float]:
    raw = resp.headers.get("retry-after")
    try:
        return float(raw) if raw is not None else None
    except ValueError:
        return None
