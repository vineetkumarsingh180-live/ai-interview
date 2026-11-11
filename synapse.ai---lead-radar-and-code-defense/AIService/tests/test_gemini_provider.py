"""Gemini transport behaviour against a mocked HTTP layer (no network, no key). NOT live verification."""
import httpx
import pytest

from aiservice import (
    GeminiProvider,
    InvalidProviderResponse,
    ProviderNotConfigured,
    ProviderRateLimited,
    ProviderRejected,
    ProviderTimeout,
    ProviderUnavailable,
)

pytestmark = pytest.mark.anyio

OK = {"candidates": [{"content": {"parts": [{"text": "hello"}]}}], "usageMetadata": {"promptTokenCount": 3, "candidatesTokenCount": 2}}


def provider(handler, **kw):
    sleeps = []

    async def sleep(s):
        sleeps.append(s)

    p = GeminiProvider(api_key="test-key", transport=httpx.MockTransport(handler), sleep=sleep, **kw)
    return p, sleeps


async def test_missing_key_is_not_configured_and_sends_nothing():
    calls = []
    p = GeminiProvider(api_key="", transport=httpx.MockTransport(lambda r: calls.append(r) or httpx.Response(200, json=OK)))
    assert p.is_configured() is False
    with pytest.raises(ProviderNotConfigured):
        await p.generate_text(prompt="x")
    assert calls == []


async def test_success_reports_provider_usage_only():
    p, _ = provider(lambda r: httpx.Response(200, json=OK))
    g = await p.generate_text(prompt="x", system="s")
    assert (g.text, g.model) == ("hello", "gemini-2.5-flash")
    assert (g.usage.prompt_tokens, g.usage.completion_tokens) == (3, 2)


async def test_usage_is_none_when_the_provider_does_not_report_it():
    body = {"candidates": [{"content": {"parts": [{"text": "hi"}]}}]}
    p, _ = provider(lambda r: httpx.Response(200, json=body))
    g = await p.generate_json(prompt="x")
    assert g.usage.prompt_tokens is None and g.usage.completion_tokens is None


async def test_key_is_sent_in_header_not_url_and_json_mode_is_requested():
    seen = {}

    def handler(r: httpx.Request):
        seen["url"], seen["key"], seen["body"] = str(r.url), r.headers.get("x-goog-api-key"), r.read().decode()
        return httpx.Response(200, json=OK)

    p, _ = provider(handler)
    await p.generate_json(prompt="x")
    assert "test-key" not in seen["url"] and seen["key"] == "test-key"
    assert "application/json" in seen["body"]


async def test_key_never_appears_in_repr_or_error_messages():
    p, _ = provider(lambda r: httpx.Response(403, json={}))
    assert "test-key" not in repr(p)
    with pytest.raises(ProviderRejected) as e:
        await p.generate_text(prompt="x")
    assert "test-key" not in str(e.value)


async def test_transient_errors_are_retried_with_backoff_then_succeed():
    answers = [httpx.Response(503), httpx.Response(429, headers={"retry-after": "2"}), httpx.Response(200, json=OK)]
    p, sleeps = provider(lambda r: answers.pop(0), max_retries=2, backoff_base=0.5)
    g = await p.generate_text(prompt="x")
    assert g.text == "hello"
    assert sleeps == [0.5, 2.0]          # exponential backoff; the 429 honoured Retry-After


async def test_retries_are_bounded_and_the_last_error_surfaces():
    n = []
    p, sleeps = provider(lambda r: n.append(1) or httpx.Response(500), max_retries=2)
    with pytest.raises(ProviderUnavailable):
        await p.generate_text(prompt="x")
    assert len(n) == 3 and len(sleeps) == 2


async def test_rate_limit_after_retries_is_reported_as_rate_limited():
    p, _ = provider(lambda r: httpx.Response(429), max_retries=1)
    with pytest.raises(ProviderRateLimited):
        await p.generate_text(prompt="x")


async def test_timeout_is_a_provider_timeout():
    def handler(r):
        raise httpx.ReadTimeout("slow", request=r)

    p, _ = provider(handler, max_retries=0)
    with pytest.raises(ProviderTimeout):
        await p.generate_text(prompt="x")


async def test_network_failure_is_provider_unavailable():
    def handler(r):
        raise httpx.ConnectError("down", request=r)

    p, _ = provider(handler, max_retries=0)
    with pytest.raises(ProviderUnavailable):
        await p.generate_text(prompt="x")


@pytest.mark.parametrize("status", [400, 401, 403, 404])
async def test_permanent_errors_are_not_retried(status):
    n = []
    p, sleeps = provider(lambda r: n.append(1) or httpx.Response(status), max_retries=3)
    with pytest.raises(ProviderRejected):
        await p.generate_text(prompt="x")
    assert len(n) == 1 and sleeps == []


@pytest.mark.parametrize("body", [{}, {"candidates": []}, {"candidates": [{"content": {"parts": [{"text": "  "}]}}]},
                                  {"promptFeedback": {"blockReason": "SAFETY"}}])
async def test_unusable_200_answers_are_invalid_responses(body):
    p, _ = provider(lambda r: httpx.Response(200, json=body))
    with pytest.raises(InvalidProviderResponse):
        await p.generate_text(prompt="x")


async def test_non_json_body_is_an_invalid_response():
    p, _ = provider(lambda r: httpx.Response(200, text="<html>"))
    with pytest.raises(InvalidProviderResponse):
        await p.generate_text(prompt="x")


def test_invalid_construction_is_rejected():
    with pytest.raises(ValueError):
        GeminiProvider(api_key="k", max_retries=-1)
