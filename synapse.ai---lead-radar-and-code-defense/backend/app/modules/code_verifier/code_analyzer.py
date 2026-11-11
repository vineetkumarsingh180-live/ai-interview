"""
Code Verifier — AI-powered code analysis service.

Accepts raw code snippets pasted by the user, calls Gemini with the
dedicated GEMINI_API_KEY_CODE_VERIFIER key, and returns a structured
AI score covering multiple quality dimensions.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from app.core.config import get_code_verifier_gemini_api_key, ModelConfigurationError
from app.shared.config import settings

logger = logging.getLogger("synapse.code_verifier.analyzer")

# ──────────────────────────────────────────────────────────────────────────────
# Pydantic schemas
# ──────────────────────────────────────────────────────────────────────────────


class CodeAnalysisRequest(BaseModel):
    code: str = Field(..., min_length=10, description="Raw code snippet to analyse")
    language: Optional[str] = Field(None, description="Programming language hint (e.g. Python, JavaScript)")
    context: Optional[str] = Field(None, description="Optional description of what the code is supposed to do")


class ScoreDimension(BaseModel):
    score: int = Field(..., ge=0, le=100, description="Score 0-100")
    label: str
    feedback: str


class CodeAnalysisResult(BaseModel):
    overall_score: int = Field(..., ge=0, le=100)
    grade: str  # A+, A, B+, B, C, D, F
    summary: str
    language_detected: str
    dimensions: list[ScoreDimension]
    issues: list[str]  # flagged problems
    suggestions: list[str]  # improvement tips
    interview_topics: list[str]  # topics an interviewer might probe


# ──────────────────────────────────────────────────────────────────────────────
# Service
# ──────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are an expert senior software engineer and code quality reviewer.
Analyse the provided code snippet and return a structured JSON evaluation.

Return ONLY valid JSON matching this exact schema (no markdown, no extra keys):
{
  "overall_score": <integer 0-100>,
  "grade": "<one of: A+, A, B+, B, C+, C, D, F>",
  "summary": "<2-3 sentence overall verdict>",
  "language_detected": "<detected programming language>",
  "dimensions": [
    {"score": <0-100>, "label": "Code Quality",        "feedback": "<concise feedback>"},
    {"score": <0-100>, "label": "Readability",         "feedback": "<concise feedback>"},
    {"score": <0-100>, "label": "Security",            "feedback": "<concise feedback>"},
    {"score": <0-100>, "label": "Performance",         "feedback": "<concise feedback>"},
    {"score": <0-100>, "label": "Maintainability",     "feedback": "<concise feedback>"},
    {"score": <0-100>, "label": "Best Practices",      "feedback": "<concise feedback>"}
  ],
  "issues": ["<issue 1>", "<issue 2>", ...],
  "suggestions": ["<tip 1>", "<tip 2>", "<tip 3>", ...],
  "interview_topics": ["<topic 1>", "<topic 2>", "<topic 3>"]
}

Scoring guidelines:
- 90-100: Excellent, production-ready code
- 75-89: Good code with minor improvements needed
- 60-74: Acceptable, notable improvements needed
- 45-59: Below standard, significant issues
- 0-44: Poor quality, major problems

Be honest and constructive. Do NOT fabricate issues that are not present.
"""


async def analyse_code(request: CodeAnalysisRequest) -> CodeAnalysisResult:
    """
    Calls Gemini using the dedicated Code Verifier API key and returns
    a structured quality score for the submitted code.
    """
    try:
        api_key = get_code_verifier_gemini_api_key()
    except ModelConfigurationError as exc:
        logger.warning("Code Verifier API key unavailable: %s", exc)
        return _fallback_result(request, str(exc))

    candidate_models = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.8-flash"]
    if settings.GEMINI_MODEL and settings.GEMINI_MODEL in candidate_models:
        candidate_models.remove(settings.GEMINI_MODEL)
        candidate_models.insert(0, settings.GEMINI_MODEL)

    client = genai.Client(api_key=api_key)
    cfg = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.2,
        system_instruction=_SYSTEM_PROMPT,
    )

    last_error: Optional[Exception] = None
    for model_name in candidate_models:
        try:
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=model_name,
                    contents=user_content,
                    config=cfg,
                ),
                timeout=30.0,
            )
            raw = response.text or "{}"
            parsed = json.loads(raw)
            return CodeAnalysisResult.model_validate(parsed)
        except Exception as exc:
            last_error = exc
            logger.warning("Code analysis model %s failed (%s), trying backup model...", model_name, exc)
            await asyncio.sleep(0.5)

    logger.error("All candidate models failed for code analysis: %s", last_error)
    return _fallback_result(request, f"AI analysis temporarily unavailable: {type(last_error).__name__}")


def _fallback_result(request: CodeAnalysisRequest, reason: str) -> CodeAnalysisResult:
    """Returns a minimal result when the AI call fails."""
    return CodeAnalysisResult(
        overall_score=0,
        grade="N/A",
        summary=f"AI scoring is currently unavailable. {reason}",
        language_detected=request.language or "Unknown",
        dimensions=[
            ScoreDimension(score=0, label="Code Quality",    feedback="Could not evaluate."),
            ScoreDimension(score=0, label="Readability",     feedback="Could not evaluate."),
            ScoreDimension(score=0, label="Security",        feedback="Could not evaluate."),
            ScoreDimension(score=0, label="Performance",     feedback="Could not evaluate."),
            ScoreDimension(score=0, label="Maintainability", feedback="Could not evaluate."),
            ScoreDimension(score=0, label="Best Practices",  feedback="Could not evaluate."),
        ],
        issues=["AI analysis could not be completed."],
        suggestions=["Ensure GEMINI_API_KEY_CODE_VERIFIER is set correctly in backend/.env"],
        interview_topics=[],
    )
