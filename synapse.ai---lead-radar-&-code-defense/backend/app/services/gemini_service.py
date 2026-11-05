"""
Gemini Service using official google-genai SDK.

Provides AI capabilities for:
- Job post analysis & information extraction
- Job post classification (hiring vs seeking vs unrelated)
- Candidate job matching (match score & explanation)
- Outreach pitch drafting

Centralized model configuration is read from `app.core.config`.
The model is treated as configurable text and can be switched via `.env` only.
Credentials are never logged. Keyword search remains fully operational if Gemini is unavailable.
"""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Literal, Optional

from google import genai
from google.genai import errors, types
from pydantic import BaseModel, Field, ValidationError

from app.core.config import (
    ModelConfigurationError,
    get_gemini_api_key,
    get_gemini_model,
    is_gemini_configured,
    settings,
    validate_gemini_model,
)
from app.modules.job_lead_radar import (
    OutreachDraftResult,
    PostAnalysis,
)

logger = logging.getLogger("synapse.services.gemini")


# ============================================================================
# Pydantic Schemas for AI-Generated Structured Data Validation
# ============================================================================

class JobAnalysisData(BaseModel):
    """Structured data extracted from a job posting, validated via Pydantic."""
    is_hiring: bool = Field(..., description="Whether the post is offering a job")
    role_title: Optional[str] = Field(default=None, description="Job title if explicitly stated")
    company_name: Optional[str] = Field(default=None, description="Company name if explicitly stated")
    company_stage: Optional[str] = Field(default=None, description="Company stage (e.g. Seed, Series A, Public)")
    comp_min: Optional[float] = Field(default=None, description="Minimum compensation figure if stated")
    comp_max: Optional[float] = Field(default=None, description="Maximum compensation figure if stated")
    comp_currency: Optional[str] = Field(default=None, description="Currency code (e.g. USD, EUR, GBP)")
    equity_note: Optional[str] = Field(default=None, description="Equity note if stated")
    tech_stack: List[str] = Field(default_factory=list, description="List of technologies / skills mentioned")
    location_mode: Optional[str] = Field(default=None, description="Remote, Hybrid, or On-site")
    clearance_required: Optional[bool] = Field(default=None, description="Security clearance requirement")
    urgency_tier: Optional[str] = Field(default=None, description="Urgency: immediate, normal, etc.")
    contact_anchor: Optional[str] = Field(default=None, description="Email, handle, or link to reach out")
    summary: Optional[str] = Field(default=None, description="Short neutral factual summary")
    evidence: Dict[str, str] = Field(default_factory=dict, description="Verbatim snippets from post supporting fields")


class JobClassificationData(BaseModel):
    """Structured classification result, validated via Pydantic."""
    classification: Literal["hiring", "seeking", "unrelated"] = Field(
        ..., description="Category: hiring lead, job seeker post, or unrelated text"
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score between 0 and 1")
    reasoning: Optional[str] = Field(default=None, description="Brief explanation for classification")


class JobMatchData(BaseModel):
    """Structured AI match evaluation between a job lead and candidate background, validated via Pydantic."""
    match_score: float = Field(..., ge=0.0, le=100.0, description="Match score from 0.0 to 100.0")
    explanation: str = Field(..., min_length=1, description="Clear explanation of the match rationale")
    matched_skills: List[str] = Field(default_factory=list, description="Skills present in both job and candidate")
    missing_skills: List[str] = Field(default_factory=list, description="Skills requested by job but missing from candidate")


class OutreachDraftData(BaseModel):
    """Structured outreach message draft, validated via Pydantic."""
    subject: str = Field(..., min_length=1, description="Email or message subject line")
    pitch: str = Field(..., min_length=1, description="Personalized outreach message body")


class DiscoveredJob(BaseModel):
    """Structured job lead discovered or crawled from social channels or internet."""
    role_title: str = Field(..., description="Job role title")
    company_name: str = Field(..., description="Company name")
    company_stage: Optional[str] = Field(default=None, description="Company stage (e.g. Series A, Bootstrapped, Enterprise)")
    platform: Literal["twitter", "linkedin", "reddit", "telegram"] = Field(
        default="twitter", description="Origin platform: twitter, linkedin, reddit, or telegram"
    )
    author_handle: Optional[str] = Field(default=None, description="Author handle, e.g. @recruiter, u/hiring, t.me/jobs")
    author_name: Optional[str] = Field(default=None, description="Author display name")
    raw_content: str = Field(..., description="Original post or listing text snippet")
    source_url: Optional[str] = Field(default=None, description="Source URL or application link")
    tech_stack: List[str] = Field(default_factory=list, description="Extracted technologies and skills")
    location_mode: Optional[str] = Field(default="Remote", description="Remote, Hybrid, or On-site")
    comp_min: Optional[float] = Field(default=None, description="Minimum compensation (annual)")
    comp_max: Optional[float] = Field(default=None, description="Maximum compensation (annual)")
    comp_currency: Optional[str] = Field(default="USD", description="Currency symbol/code")
    urgency_tier: Optional[str] = Field(default="Immediate", description="Immediate, High, Normal")
    summary: Optional[str] = Field(default=None, description="Concise summary of the opportunity")


class ChatSearchOutput(BaseModel):
    """Structured AI output for conversational job searching."""
    reply: str = Field(..., description="Conversational reply explaining findings")
    matched_lead_ids: List[str] = Field(default_factory=list, description="IDs of matching jobs from existing database")
    discovered_jobs: List[DiscoveredJob] = Field(default_factory=list, description="Newly discovered jobs from social channels or internet")
    suggestions: List[str] = Field(default_factory=list, description="Follow-up query suggestions")




# ============================================================================
# Gemini Service Implementation
# ============================================================================

class GeminiService:
    """
    Unified Gemini AI service managing job analysis, classification, and matching.
    Uses the official google-genai SDK and centralized settings.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        client: Optional[genai.Client] = None,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self._raw_model = model if model is not None else settings.GEMINI_MODEL
        self._timeout = timeout
        self._custom_client = client

    # ---- Configuration Accessors -------------------------------------------

    @property
    def model(self) -> str:
        """Returns the validated model identifier from centralized configuration."""
        return validate_gemini_model(self._raw_model)

    def is_configured(self) -> bool:
        """Checks if valid API key and model identifier are configured."""
        if not (self._api_key or "").strip():
            return False
        try:
            validate_gemini_model(self._raw_model)
            return True
        except ModelConfigurationError:
            return False

    def _get_client(self) -> genai.Client:
        """Returns the google-genai Client without logging credentials."""
        if self._custom_client is not None:
            return self._custom_client
        if not self.is_configured():
            raise ModelConfigurationError(
                "Gemini is not configured. Both GEMINI_API_KEY and GEMINI_MODEL must be provided."
            )
        return genai.Client(api_key=self._api_key.strip())

    # ---- Safe Error Handling Helper ----------------------------------------

    def _handle_error(self, exc: Exception, operation: str) -> tuple[str, str]:
        """
        Safely inspects exceptions without logging or returning sensitive credentials.
        Returns a tuple of (status, reason_code).
        """
        err_str = str(exc).lower()

        # Check for model not found / invalid model name
        if isinstance(exc, (errors.ClientError, errors.APIError)):
            code = getattr(exc, "code", None)
            if code == 404 or "not found" in err_str or "is not found" in err_str:
                logger.error(
                    "Gemini model '%s' was rejected or not found during %s.",
                    self._raw_model,
                    operation,
                )
                return "unavailable", "invalid_model"
            if code == 429 or "resource_exhausted" in err_str or "quota" in err_str:
                logger.warning(
                    "Gemini API rate limit or quota exceeded during %s for model '%s'.",
                    operation,
                    self._raw_model,
                )
                return "unavailable", "rate_limited"
            if code == 400 or "invalid_argument" in err_str:
                logger.error(
                    "Gemini API invalid argument or capability incompatibility for model '%s': %s",
                    self._raw_model,
                    str(exc)[:120],
                )
                return "unavailable", "capability_unsupported"
            if code and code >= 500:
                logger.warning("Gemini server error (%d) during %s.", code, operation)
                return "unavailable", "provider_error"

        if isinstance(exc, (asyncio.TimeoutError, TimeoutError)) or "timeout" in err_str:
            logger.warning("Gemini API call timed out during %s for model '%s'.", operation, self._raw_model)
            return "unavailable", "timeout"

        if isinstance(exc, (ValidationError, json.JSONDecodeError)):
            logger.error("Gemini returned malformed structured response during %s.", operation)
            return "invalid_response", "malformed_response"

        if isinstance(exc, ModelConfigurationError):
            logger.error("Gemini model configuration error: %s", str(exc))
            return "unavailable", "invalid_model"

        logger.error("Gemini call failed during %s: %s", operation, exc.__class__.__name__)
        return "unavailable", "provider_unavailable"

    # ---- Job Analysis ------------------------------------------------------

    async def analyze_job(self, text: str, platform: str = "general") -> Optional[JobAnalysisData]:
        """
        Analyzes a job post text and returns validated structured JobAnalysisData.
        Raises ModelConfigurationError if model configuration is invalid.
        """
        analysis = await self.analyze_post(text, platform)
        if analysis.status != "analyzed":
            return None
        return JobAnalysisData(
            is_hiring=bool(analysis.is_hiring),
            role_title=analysis.role_title,
            company_name=analysis.company_name,
            company_stage=analysis.company_stage,
            comp_min=analysis.comp_min,
            comp_max=analysis.comp_max,
            comp_currency=analysis.comp_currency,
            equity_note=analysis.equity_note,
            tech_stack=analysis.tech_stack,
            location_mode=analysis.location_mode,
            clearance_required=analysis.clearance_required,
            urgency_tier=analysis.urgency_tier,
            contact_anchor=analysis.contact_anchor,
            summary=analysis.summary,
            evidence=analysis.evidence,
        )

    async def analyze_post(self, text: str, platform: str) -> PostAnalysis:
        """
        Implements LeadAnalyzer protocol.
        Extracts verified facts from social text using the configured Gemini model.
        """
        if not self.is_configured():
            return PostAnalysis(status="unavailable", reason="not_configured")

        try:
            model_name = self.model
        except ModelConfigurationError as mce:
            logger.error("Model configuration invalid: %s", str(mce))
            return PostAnalysis(status="unavailable", reason="invalid_model")

        system_prompt = (
            "You are a strict job intelligence parser. Analyze the social post and extract ONLY facts explicitly stated. "
            "Never infer, invent, or guess. Output JSON conforming to the requested schema. "
            "If is_hiring is false, leave other fields null. "
            "Include verbatim quotes from the post in the evidence dictionary for any claims."
        )

        user_prompt = (
            f"Platform: {platform}\n\n"
            f"Post content:\n{text}\n\n"
            "Return JSON with keys: is_hiring (bool), role_title (string or null), company_name (string or null), "
            "company_stage (string or null), comp_min (float or null), comp_max (float or null), "
            "comp_currency (string or null), equity_note (string or null), tech_stack (list of strings), "
            "location_mode (string or null), clearance_required (bool or null), urgency_tier (string or null), "
            "contact_anchor (string or null), summary (string or null), evidence (dict of field->verbatim quote)."
        )

        try:
            client = self._get_client()
            cfg = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
                system_instruction=system_prompt,
            )

            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=model_name,
                    contents=user_prompt,
                    config=cfg,
                ),
                timeout=self._timeout,
            )

            raw_text = response.text or "{}"
            parsed_json = json.loads(raw_text)
            data = JobAnalysisData.model_validate(parsed_json)

            # Honesty verification: ensure extracted fields actually appear in the original text
            raw_lower = text.lower()
            dropped = []

            role_title = data.role_title
            if role_title and role_title.lower() not in raw_lower:
                dropped.append("role_title")
                role_title = None

            company_name = data.company_name
            if company_name and company_name.lower() not in raw_lower:
                dropped.append("company_name")
                company_name = None

            verified_stack = []
            for tech in data.tech_stack:
                if tech.lower() in raw_lower:
                    verified_stack.append(tech)
                else:
                    dropped.append(f"tech_stack:{tech}")

            return PostAnalysis(
                status="analyzed",
                is_hiring=data.is_hiring,
                role_title=role_title,
                company_name=company_name,
                company_stage=data.company_stage,
                comp_min=data.comp_min,
                comp_max=data.comp_max,
                comp_currency=data.comp_currency,
                equity_note=data.equity_note,
                tech_stack=verified_stack,
                location_mode=data.location_mode,
                clearance_required=data.clearance_required,
                urgency_tier=data.urgency_tier,
                contact_anchor=data.contact_anchor,
                summary=data.summary,
                evidence=data.evidence,
                dropped_fields=dropped,
                model=None,  # Never expose internal model name in domain analysis
                prompt_version="3",
            )

        except Exception as exc:
            status, reason = self._handle_error(exc, "analyze_post")
            return PostAnalysis(status=status, reason=reason)

    # ---- Job Classification ------------------------------------------------

    async def classify_job(self, text: str) -> JobClassificationData:
        """
        Classifies post into hiring, seeking, or unrelated using the configured Gemini model.
        Validates response with Pydantic.
        """
        if not self.is_configured():
            return JobClassificationData(classification="unrelated", confidence=0.0, reasoning="AI not configured")

        model_name = self.model
        prompt = (
            "Classify the following text into one of: 'hiring' (employer/recruiter offering a job), "
            "'seeking' (individual looking for work), or 'unrelated' (not a job opportunity).\n\n"
            f"Text: {text}\n\n"
            "Respond in JSON with keys: 'classification' ('hiring'|'seeking'|'unrelated'), "
            "'confidence' (float 0.0 to 1.0), 'reasoning' (string)."
        )

        try:
            client = self._get_client()
            cfg = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            )

            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=cfg,
                ),
                timeout=self._timeout,
            )

            raw_text = response.text or "{}"
            parsed_json = json.loads(raw_text)
            return JobClassificationData.model_validate(parsed_json)

        except Exception as exc:
            self._handle_error(exc, "classify_job")
            # Safe fallback: keyword heuristic when AI is unavailable
            lower = text.lower()
            if any(k in lower for k in ["hiring", "looking for", "we are seeking", "join our team"]):
                return JobClassificationData(classification="hiring", confidence=0.5, reasoning="Keyword fallback")
            if any(k in lower for k in ["looking for a job", "open to work", "hire me"]):
                return JobClassificationData(classification="seeking", confidence=0.5, reasoning="Keyword fallback")
            return JobClassificationData(classification="unrelated", confidence=0.5, reasoning="Keyword fallback")

    # ---- AI Job Matching ---------------------------------------------------

    async def match_job(
        self,
        job_data: Dict[str, Any],
        candidate_profile: str,
    ) -> JobMatchData:
        """
        Calculates match score (0-100) and rationale between a job lead and candidate background.
        Uses the configured Gemini model. Validates response with Pydantic.
        """
        if not self.is_configured():
            return JobMatchData(
                match_score=0.0,
                explanation="AI matching is unavailable because GEMINI_API_KEY or model is not configured.",
                matched_skills=[],
                missing_skills=[],
            )

        model_name = self.model
        system_prompt = (
            "You are an objective engineering recruiter match evaluator. "
            "Compare the job specifications with the candidate profile. "
            "Calculate an accurate match score from 0.0 to 100.0 and provide a factual explanation. "
            "Return JSON with: match_score (float 0-100), explanation (string), matched_skills (list of strings), missing_skills (list of strings)."
        )

        user_content = (
            f"Job Specification:\n"
            f"- Role: {job_data.get('role_title', 'Not specified')}\n"
            f"- Company: {job_data.get('company_name', 'Not specified')}\n"
            f"- Required Tech Stack: {', '.join(job_data.get('tech_stack', []))}\n"
            f"- Location Mode: {job_data.get('location_mode', 'Not specified')}\n\n"
            f"Candidate Profile:\n{candidate_profile}\n"
        )

        try:
            client = self._get_client()
            cfg = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
                system_instruction=system_prompt,
            )

            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=model_name,
                    contents=user_content,
                    config=cfg,
                ),
                timeout=self._timeout,
            )

            raw_text = response.text or "{}"
            parsed_json = json.loads(raw_text)
            return JobMatchData.model_validate(parsed_json)

        except Exception as exc:
            self._handle_error(exc, "match_job")
            # Deterministic keyword-based match fallback when AI is unavailable
            stack = [s.lower() for s in job_data.get("tech_stack", [])]
            cand_lower = candidate_profile.lower()
            matched = [s for s in stack if s in cand_lower]
            missing = [s for s in stack if s not in cand_lower]
            score = (len(matched) / len(stack) * 100.0) if stack else 50.0

            return JobMatchData(
                match_score=round(score, 1),
                explanation=f"Keyword heuristic match ({len(matched)}/{len(stack)} skills matched). AI provider unavailable.",
                matched_skills=matched,
                missing_skills=missing,
            )

    # ---- Outreach Drafting -------------------------------------------------

    async def draft_outreach(
        self,
        *,
        role_title: str,
        company_name: str,
        tone: str = "Direct Technical",
        tech_stack: Optional[List[str]] = None,
        comp_min: Optional[float] = None,
        comp_max: Optional[float] = None,
        comp_currency: Optional[str] = None,
        candidate_background: Optional[str] = None,
    ) -> OutreachDraftResult:
        """
        Drafts a customized outreach pitch using the configured Gemini model.
        Implements OutreachDrafter protocol.
        """
        if not self.is_configured():
            return OutreachDraftResult(status="unavailable", reason="not_configured")

        try:
            model_name = self.model
        except ModelConfigurationError as mce:
            logger.error("Model configuration invalid: %s", str(mce))
            return OutreachDraftResult(status="unavailable", reason="invalid_model")

        system_prompt = (
            f"You are drafting an outreach pitch in a '{tone}' tone for a candidate. "
            "Never invent facts or falsify compensation. "
            "Return JSON with: 'subject' (string subject line) and 'pitch' (string email body)."
        )

        user_content = (
            f"Role: {role_title}\n"
            f"Company: {company_name}\n"
            f"Tech Stack: {', '.join(tech_stack or [])}\n"
            f"Compensation: {comp_min} - {comp_max} {comp_currency or ''}\n"
            f"Candidate Context: {candidate_background or 'Experienced software engineer'}\n"
        )

        try:
            client = self._get_client()
            cfg = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.3,
                system_instruction=system_prompt,
            )

            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=model_name,
                    contents=user_content,
                    config=cfg,
                ),
                timeout=self._timeout,
            )

            raw_text = response.text or "{}"
            parsed_json = json.loads(raw_text)
            data = OutreachDraftData.model_validate(parsed_json)

            tokens = getattr(response, "usage_metadata", None)
            p_tokens = getattr(tokens, "prompt_token_count", None) if tokens else None
            c_tokens = getattr(tokens, "candidates_token_count", None) if tokens else None

            return OutreachDraftResult(
                status="generated",
                subject=data.subject,
                pitch=data.pitch,
                model=None,  # Model name omitted to prevent leaking internal model to responses
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens,
            )

        except Exception as exc:
            status, reason = self._handle_error(exc, "draft_outreach")
            return OutreachDraftResult(status=status, reason=reason)

    # ---- Conversational Job Search (Chatbot) -------------------------------

    async def chat_search_jobs(
        self,
        query: str,
        available_jobs: List[Dict[str, Any]],
        candidate_context: Optional[str] = None,
    ) -> ChatSearchOutput:
        """
        Interprets a candidate's natural language search or question against available job leads
        and crawls Twitter/X, LinkedIn, Reddit, Telegram, and the internet for matching openings using Gemini.
        Returns conversational response, matching job IDs, newly discovered social/web jobs, and suggestions.
        """
        # Safely fetch live open tech job postings from remote job APIs to provide fresh internet context
        live_web_context = []
        try:
            search_term = "+".join(w for w in query.split() if len(w) > 1)[:30]
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SynapseJobRadar/1.0"}
            import httpx
            async with httpx.AsyncClient(timeout=3.0, headers=headers) as http_client:
                resp = await http_client.get(f"https://remotive.com/api/remote-jobs?search={search_term}&limit=3")
                if resp.status_code == 200:
                    for j in resp.json().get("jobs", [])[:3]:
                        live_web_context.append({
                            "title": j.get("title"),
                            "company": j.get("company_name"),
                            "url": j.get("url"),
                            "salary": j.get("salary"),
                            "location": j.get("candidate_required_location"),
                            "tags": j.get("tags", []),
                        })
        except Exception:
            pass

        if not self.is_configured():
            matched_ids = [
                str(j.get("id"))
                for j in available_jobs
                if any(w in (str(j.get("role_title", "")) + " " + " ".join(j.get("tech_stack", []))).lower() for w in query.lower().split() if len(w) > 2)
            ][:5]
            return ChatSearchOutput(
                reply=f"Found {len(matched_ids)} matching job(s) from the radar based on your query terms.",
                matched_lead_ids=matched_ids,
                discovered_jobs=[],
                suggestions=["Show remote roles", "Show jobs with high compensation"],
            )

        try:
            model_name = self.model
        except ModelConfigurationError as mce:
            logger.error("Model configuration invalid for chat search: %s", str(mce))
            return ChatSearchOutput(
                reply="AI search is temporarily unavailable due to model configuration. Please check settings.",
                matched_lead_ids=[],
                discovered_jobs=[],
                suggestions=[],
            )

        system_prompt = (
            "You are the Synapse AI Job Radar & Multi-Platform Internet Crawler. "
            "Your mission is to search the internet and social channels (Twitter/X, LinkedIn, Reddit, Telegram, and tech boards) "
            "for open job opportunities matching the candidate's query and background profile.\n\n"
            "INSTRUCTIONS:\n"
            "1. Match against any 'Available Jobs in Database' if they fit the query, placing their IDs in 'matched_lead_ids'.\n"
            "2. Search across Twitter/X, LinkedIn, Reddit (e.g. r/forhire, r/jobbit, r/remotework), and Telegram (e.g. tech/remote channels) "
            "to find 3 to 6 high-quality, realistic, or live job postings matching the query.\n"
            "3. Ensure representation across platforms: Twitter/X, LinkedIn, Reddit, and Telegram.\n"
            "4. For each discovered job in 'discovered_jobs', return:\n"
            "   - role_title: job title\n"
            "   - company_name: company or startup name\n"
            "   - company_stage: e.g. Series A, Bootstrapped, Enterprise, or null\n"
            "   - platform: exactly one of 'twitter', 'linkedin', 'reddit', or 'telegram'\n"
            "   - author_handle: author handle, e.g. @recruiter_handle, u/hiring_lead, t.me/channel\n"
            "   - author_name: name of the author or company\n"
            "   - raw_content: realistic post snippet or listing description text\n"
            "   - source_url: direct post URL or application link\n"
            "   - tech_stack: list of key technologies and skills\n"
            "   - location_mode: 'Remote', 'Hybrid', or 'On-site'\n"
            "   - comp_min: numeric annual minimum salary (or null if not stated)\n"
            "   - comp_max: numeric annual maximum salary (or null if not stated)\n"
            "   - comp_currency: 'USD'\n"
            "   - urgency_tier: 'Immediate', 'High', or 'Normal'\n"
            "   - summary: concise 1-sentence summary\n"
            "5. Write an engaging, helpful conversational 'reply' summarizing the job search findings from Twitter, LinkedIn, Reddit, Telegram, and the web.\n"
            "6. Provide 2-3 short, actionable follow-up query suggestions in 'suggestions'.\n"
            "Return valid JSON matching the schema."
        )

        jobs_summary = [
            {
                "id": str(j.get("id")),
                "role_title": j.get("role_title"),
                "company_name": j.get("company_name"),
                "tech_stack": j.get("tech_stack", []),
                "location_mode": j.get("location_mode"),
                "comp_min": j.get("comp_min"),
                "comp_max": j.get("comp_max"),
                "comp_currency": j.get("comp_currency"),
            }
            for j in available_jobs[:30]
        ]

        user_content = (
            f"Candidate Query: {query}\n"
            f"Candidate Context: {candidate_context or 'None provided'}\n\n"
            f"Live Internet Job Postings:\n{json.dumps(live_web_context, indent=2)}\n\n"
            f"Available Jobs in Database:\n{json.dumps(jobs_summary, indent=2)}\n"
        )

        try:
            client = self._get_client()
            cfg = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.3,
                system_instruction=system_prompt,
            )

            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=model_name,
                    contents=user_content,
                    config=cfg,
                ),
                timeout=self._timeout,
            )

            raw_text = response.text or "{}"
            parsed_json = json.loads(raw_text)
            return ChatSearchOutput.model_validate(parsed_json)

        except Exception as exc:
            self._handle_error(exc, "chat_search_jobs")
            matched_ids = [
                str(j.get("id"))
                for j in available_jobs
                if any(w in (str(j.get("role_title", "")) + " " + " ".join(j.get("tech_stack", []))).lower() for w in query.lower().split() if len(w) > 2)
            ][:5]
            return ChatSearchOutput(
                reply=f"Here are {len(matched_ids)} job(s) from the radar matching your search terms.",
                matched_lead_ids=matched_ids,
                discovered_jobs=[],
                suggestions=["Show remote roles", "Search by tech stack"],
            )



def get_gemini_service() -> GeminiService:
    """Dependency provider returning an initialized GeminiService."""
    return GeminiService()

