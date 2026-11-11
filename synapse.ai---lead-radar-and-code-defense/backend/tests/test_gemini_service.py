"""
Comprehensive tests for GeminiService and dynamic Gemini model configuration.

All tests run completely offline with mocked responses; no live Gemini API key is required.
Verifies:
1. Centralized model configuration in app/core/config.py
2. Dynamic model selection via .env without code modification
3. Missing or invalid model handling with safe logging and no silent fallback
4. Pydantic validation of structured data for job analysis, classification, and matching
5. Safe handling of API errors, rate limits (429), timeouts, and malformed responses
6. Normal keyword search remaining fully functional when Gemini is unavailable
7. Public API responses containing no secret keys or internal model names
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.genai import errors

from app.core.config import (
    ModelConfigurationError,
    get_gemini_api_key,
    get_gemini_model,
    is_gemini_configured,
    settings,
    validate_gemini_model,
)
from app.services.gemini_service import (
    GeminiService,
    JobAnalysisData,
    JobClassificationData,
    JobMatchData,
    OutreachDraftData,
)


# ============================================================================
# 1. Flexible Model Configuration & Centralization Tests
# ============================================================================

def test_centralized_model_reads_from_settings(monkeypatch):
    """Changing GEMINI_MODEL in settings updates model configuration dynamically."""
    monkeypatch.setattr(settings, "GEMINI_MODEL", "gemini-1.5-pro")
    assert get_gemini_model() == "gemini-1.5-pro"

    monkeypatch.setattr(settings, "GEMINI_MODEL", "gemini-2.0-flash-exp")
    assert get_gemini_model() == "gemini-2.0-flash-exp"


def test_missing_model_raises_clear_error_and_does_not_silently_fallback(monkeypatch):
    """Empty or whitespace model raises ModelConfigurationError without silent switching."""
    monkeypatch.setattr(settings, "GEMINI_MODEL", "")
    with pytest.raises(ModelConfigurationError) as exc_info:
        get_gemini_model()
    assert "missing or empty" in str(exc_info.value).lower()

    monkeypatch.setattr(settings, "GEMINI_MODEL", "   ")
    with pytest.raises(ModelConfigurationError):
        get_gemini_model()


def test_invalid_model_name_raises_clear_error(monkeypatch):
    """Model names with invalid/dangerous characters are rejected."""
    monkeypatch.setattr(settings, "GEMINI_MODEL", "invalid model with spaces; rm -rf")
    with pytest.raises(ModelConfigurationError) as exc_info:
        validate_gemini_model()
    assert "invalid characters" in str(exc_info.value).lower()


def test_is_gemini_configured_checks_both_key_and_model(monkeypatch):
    """Both key and valid model are required for configured status."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
    assert is_gemini_configured() is False

    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(settings, "GEMINI_MODEL", "")
    assert is_gemini_configured() is False

    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
    assert is_gemini_configured() is True


def test_api_key_not_logged_when_missing(monkeypatch, caplog):
    """Diagnostics do not expose secrets."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    with pytest.raises(ModelConfigurationError):
        get_gemini_api_key()
    for record in caplog.records:
        assert "GEMINI_API_KEY" in record.message or "unavailable" in record.message
        assert "test-key" not in record.message


# ============================================================================
# 2. Mock Helpers for Google GenAI SDK
# ============================================================================

def make_mock_client(response_text: str, usage=None):
    """Creates a mock google-genai Client that returns response_text."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = response_text
    if usage:
        mock_response.usage_metadata = usage
    else:
        mock_response.usage_metadata = MagicMock(prompt_token_count=10, candidates_token_count=20)

    mock_client.aio = MagicMock()
    mock_client.aio.models = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
    return mock_client


# ============================================================================
# 3. Job Analysis & Information Extraction Tests
# ============================================================================

@pytest.mark.anyio
async def test_job_analysis_uses_configured_model_and_validates_pydantic():
    """Analysis calls model from centralized settings and validates structured data."""
    extracted = {
        "is_hiring": True,
        "role_title": "Backend Engineer",
        "company_name": "Acme Corp",
        "company_stage": "Series B",
        "comp_min": 140000.0,
        "comp_max": 180000.0,
        "comp_currency": "USD",
        "equity_note": "0.1% equity",
        "tech_stack": ["Python", "FastAPI"],
        "location_mode": "Remote",
        "clearance_required": False,
        "urgency_tier": "Immediate",
        "contact_anchor": "jobs@acme.com",
        "summary": "Acme Corp is hiring a Backend Engineer.",
        "evidence": {"role_title": "Backend Engineer", "company_name": "Acme Corp"},
    }

    raw_post = "Acme Corp is hiring a Backend Engineer. We use Python and FastAPI. Remote. Apply at jobs@acme.com"
    client = make_mock_client(json.dumps(extracted))
    service = GeminiService(api_key="test-key", model="gemini-custom-model", client=client)

    result = await service.analyze_post(raw_post, "twitter")

    assert result.status == "analyzed"
    assert result.is_hiring is True
    assert result.role_title == "Backend Engineer"
    assert result.company_name == "Acme Corp"
    assert result.tech_stack == ["Python", "FastAPI"]
    assert result.location_mode == "Remote"
    # Ensure model used was the configured one
    client.aio.models.generate_content.assert_called_once()
    call_kwargs = client.aio.models.generate_content.call_args.kwargs
    assert call_kwargs["model"] == "gemini-custom-model"
    # Ensure model name is NOT exposed in the domain PostAnalysis result
    assert result.model is None


# ============================================================================
# 4. Job Classification Tests
# ============================================================================

@pytest.mark.anyio
async def test_job_classification_uses_configured_model():
    """Classification returns validated Pydantic JobClassificationData."""
    data = {
        "classification": "hiring",
        "confidence": 0.95,
        "reasoning": "Post mentions open engineering positions and application link.",
    }
    client = make_mock_client(json.dumps(data))
    service = GeminiService(api_key="test-key", model="gemini-2.0-flash", client=client)

    result = await service.classify_job("We are hiring 3 senior engineers!")

    assert isinstance(result, JobClassificationData)
    assert result.classification == "hiring"
    assert result.confidence == 0.95
    assert "open engineering" in result.reasoning


# ============================================================================
# 5. AI Job Matching Tests
# ============================================================================

@pytest.mark.anyio
async def test_job_matching_uses_configured_model_and_validates_score():
    """Job matching produces validated score (0-100) and rationale."""
    match_payload = {
        "match_score": 88.5,
        "explanation": "Strong match on Python and FastAPI with distributed systems experience.",
        "matched_skills": ["Python", "FastAPI", "Docker"],
        "missing_skills": ["Kubernetes"],
    }
    client = make_mock_client(json.dumps(match_payload))
    service = GeminiService(api_key="test-key", model="gemini-experimental", client=client)

    job_data = {
        "role_title": "Senior Python Developer",
        "company_name": "Tech Corp",
        "tech_stack": ["Python", "FastAPI", "Docker", "Kubernetes"],
        "location_mode": "Remote",
    }
    candidate = "5 years developing REST APIs with Python, FastAPI, and Docker."

    match_result = await service.match_job(job_data, candidate)

    assert isinstance(match_result, JobMatchData)
    assert match_result.match_score == 88.5
    assert "Strong match" in match_result.explanation
    assert "Python" in match_result.matched_skills
    assert "Kubernetes" in match_result.missing_skills


# ============================================================================
# 6. Error Handling Tests: Rate Limits, Timeouts, Invalid Models, Malformed
# ============================================================================

@pytest.mark.anyio
async def test_rate_limit_handled_safely():
    """429 ResourceExhausted returns status='unavailable' with reason='rate_limited'."""
    mock_client = MagicMock()
    mock_client.aio = MagicMock()
    mock_client.aio.models = MagicMock()

    api_err = errors.APIError(429, {"error": {"message": "Resource exhausted: quota exceeded"}})
    mock_client.aio.models.generate_content = AsyncMock(side_effect=api_err)

    service = GeminiService(api_key="test-key", model="gemini-2.5-flash", client=mock_client)
    res = await service.analyze_post("Acme is hiring", "twitter")

    assert res.status == "unavailable"
    assert res.reason == "rate_limited"


@pytest.mark.anyio
async def test_invalid_model_rejected_by_api_handled_safely():
    """404 or model not found returns status='unavailable' with reason='invalid_model'."""
    mock_client = MagicMock()
    mock_client.aio = MagicMock()
    mock_client.aio.models = MagicMock()

    api_err = errors.ClientError(404, {"error": {"message": "Model 'gemini-nonexistent' not found"}})
    mock_client.aio.models.generate_content = AsyncMock(side_effect=api_err)

    service = GeminiService(api_key="test-key", model="gemini-nonexistent", client=mock_client)
    res = await service.analyze_post("Acme is hiring", "twitter")

    assert res.status == "unavailable"
    assert res.reason == "invalid_model"


@pytest.mark.anyio
async def test_timeout_handled_safely():
    """Timeout returns status='unavailable' with reason='timeout'."""
    mock_client = MagicMock()
    mock_client.aio = MagicMock()
    mock_client.aio.models = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(side_effect=asyncio.TimeoutError())

    service = GeminiService(api_key="test-key", model="gemini-2.5-flash", client=mock_client)
    res = await service.analyze_post("Acme is hiring", "twitter")

    assert res.status == "unavailable"
    assert res.reason == "timeout"


@pytest.mark.anyio
async def test_malformed_response_handled_safely():
    """Non-JSON or invalid schema returns status='invalid_response'."""
    client = make_mock_client("This is not valid JSON at all")
    service = GeminiService(api_key="test-key", model="gemini-2.5-flash", client=client)

    res = await service.analyze_post("Acme is hiring", "twitter")

    assert res.status == "invalid_response"
    assert res.reason == "malformed_response"


# ============================================================================
# 7. Keyword-Based Search Works When Gemini is Unavailable
# ============================================================================

@pytest.mark.anyio
async def test_keyword_search_independent_of_gemini(monkeypatch):
    """Keyword search in OutreachService works even when Gemini is unconfigured or down."""
    import uuid
    from datetime import datetime
    from app.modules.job_lead_radar.models import JobLead
    from app.modules.job_lead_radar.service import OutreachService
    from tests.fakes import FakeDb, FakeResult

    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(settings, "GEMINI_MODEL", "")

    lead = JobLead(
        id=uuid.uuid4(),
        raw_post_id=uuid.uuid4(),
        role_title="Senior Rust Engineer",
        company_name="Solana Labs",
        tech_stack=["Rust", "Wasm"],
        is_hiring=True,
        enrichment_metadata={},
        entry_source="operator_entered",
        is_demo=False,
        created_at=datetime.utcnow(),
    )

    db = FakeDb()
    db.execute = AsyncMock(return_value=FakeResult(rows=[lead]))

    hits = await OutreachService.search_leads(db, query_text="rust engineer")
    assert len(hits) == 1
    assert hits[0].lead.role_title == "Senior Rust Engineer"


@pytest.mark.anyio
async def test_chat_search_jobs_with_mocked_gemini():
    """Chat search uses Gemini to return conversational reply and matched job IDs."""
    data = {
        "reply": "I found 1 great match for your Python backend requirements.",
        "matched_lead_ids": ["lead-123"],
        "suggestions": ["Show remote jobs only", "Filter by salary"],
    }
    client = make_mock_client(json.dumps(data))
    service = GeminiService(api_key="test-key", model="gemini-3.8-flash", client=client)

    jobs = [
        {"id": "lead-123", "role_title": "Python Lead", "company_name": "Acme", "tech_stack": ["Python"]}
    ]
    res = await service.chat_search_jobs(query="Need a senior python job", available_jobs=jobs)

    assert "Python backend" in res.reply
    assert res.matched_lead_ids == ["lead-123"]
    assert len(res.suggestions) == 2


# ============================================================================
# 8. Public API Response Security: No API Keys or Model Configurations
# ============================================================================

def test_public_schemas_contain_no_gemini_api_key_or_model_selector():
    """Swagger and public API schemas never expose GEMINI_API_KEY or model selector fields."""
    from app.main import app

    openapi_doc = app.openapi()
    schemas = openapi_doc.get("components", {}).get("schemas", {})

    for schema_name, schema in schemas.items():
        properties = schema.get("properties", {})
        assert "geminiApiKey" not in properties
        assert "apiKey" not in properties
        assert "gemini_api_key" not in properties
        assert "geminiModel" not in properties
        assert "modelSelector" not in properties
