"""
Lead intelligence: classify a post and extract structured, evidence-checked fields.

The model is asked for a verbatim supporting quote per field. Every value is then checked against
the source text deterministically; a value without verifiable support is DROPPED (set to null and
named in `dropped_fields`), never kept on trust. The result is an interpretation of the post, not a
verified fact: persistence and review state are the caller's responsibility.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..errors import AIServiceError, InvalidProviderResponse, ProviderNotConfigured
from ..prompts import LEAD_EXTRACTION
from ..providers.base import LLMProvider, Usage, parse_model
from ..shared.text import contains_quote, contains_term, numbers_in
from .outreach import OutreachRequest, OutreachResult, draft_outreach

logger = logging.getLogger("aiservice.lead")

MAX_POST_CHARS = 20000
_LOCATION = {"remote": "Remote", "hybrid": "Hybrid", "onsite": "Onsite", "on-site": "Onsite", "on site": "Onsite"}
_URGENCY = {"immediate": "Immediate", "high": "High", "normal": "Normal"}


class _RawExtraction(BaseModel):
    """Exactly what the model is asked to return. Unknown keys are ignored, never trusted."""

    model_config = ConfigDict(extra="ignore")

    is_hiring: bool
    role_title: Optional[str] = None
    company_name: Optional[str] = None
    company_stage: Optional[str] = None
    comp_min: Optional[float] = None
    comp_max: Optional[float] = None
    comp_currency: Optional[str] = None
    equity_note: Optional[str] = None
    tech_stack: List[str] = Field(default_factory=list)
    location_mode: Optional[str] = None
    clearance_required: Optional[bool] = None
    urgency_tier: Optional[str] = None
    contact_anchor: Optional[str] = None
    summary: Optional[str] = None
    evidence: Dict[str, str] = Field(default_factory=dict)


@dataclass
class LeadFields:
    role_title: Optional[str] = None
    company_name: Optional[str] = None
    company_stage: Optional[str] = None
    comp_min: Optional[float] = None
    comp_max: Optional[float] = None
    comp_currency: Optional[str] = None
    equity_note: Optional[str] = None
    tech_stack: List[str] = field(default_factory=list)
    location_mode: Optional[str] = None
    clearance_required: Optional[bool] = None
    urgency_tier: Optional[str] = None
    contact_anchor: Optional[str] = None
    summary: Optional[str] = None


@dataclass
class LeadAnalysis:
    status: Literal["analyzed", "unavailable", "invalid_response"]
    reason: Optional[str] = None
    is_hiring: Optional[bool] = None
    fields: LeadFields = field(default_factory=LeadFields)
    evidence: Dict[str, str] = field(default_factory=dict)       # field -> quote verified to occur in the post
    dropped_fields: List[str] = field(default_factory=list)      # model claims that could not be verified
    model: Optional[str] = None
    prompt_version: Optional[str] = None
    usage: Usage = Usage()


_TEXT_FIELDS = ("role_title", "company_name", "company_stage", "equity_note", "contact_anchor", "comp_currency")


class LeadIntelligence:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def is_available(self) -> bool:
        return self._provider.is_configured()

    async def analyze_post(self, text: str, platform: str) -> LeadAnalysis:
        if not self._provider.is_configured():
            return LeadAnalysis(status="unavailable", reason=ProviderNotConfigured.code)
        if not (text or "").strip():
            return LeadAnalysis(status="invalid_response", reason="empty_post")
        prompt = f"Platform: {platform}\nPost text:\n\"\"\"{text[:MAX_POST_CHARS]}\"\"\""
        try:
            generation = await self._provider.generate_json(prompt=prompt, system=LEAD_EXTRACTION.system, temperature=0.1)
            raw = parse_model(generation, _RawExtraction)
        except InvalidProviderResponse as exc:
            logger.warning("Unusable extraction: %s", exc.message)
            return LeadAnalysis(status="invalid_response", reason=exc.code, prompt_version=LEAD_EXTRACTION.version)
        except AIServiceError as exc:
            logger.warning("Extraction unavailable: %s", exc.code)
            return LeadAnalysis(status="unavailable", reason=exc.code, prompt_version=LEAD_EXTRACTION.version)

        verified, evidence, dropped = _verify(raw, text)
        return LeadAnalysis(
            status="analyzed",
            is_hiring=raw.is_hiring,
            fields=verified,
            evidence=evidence,
            dropped_fields=dropped,
            model=generation.model,
            prompt_version=LEAD_EXTRACTION.version,
            usage=generation.usage,
        )

    async def draft_outreach(self, request: OutreachRequest) -> OutreachResult:
        return await draft_outreach(self._provider, request)


def _verify(raw: _RawExtraction, source: str):
    out = LeadFields()
    evidence: Dict[str, str] = {}
    dropped: List[str] = []

    def keep_text(name: str, value: Optional[str]) -> Optional[str]:
        if value is None or not str(value).strip():
            return None
        quote = raw.evidence.get(name, "")
        if contains_quote(source, quote) or contains_quote(source, value):
            evidence[name] = quote if contains_quote(source, quote) else value
            return str(value).strip()
        dropped.append(name)
        return None

    for name in _TEXT_FIELDS:
        setattr(out, name, keep_text(name, getattr(raw, name)))

    # numbers must literally appear in the post (k/m suffixes expanded)
    stated = numbers_in(source)
    for name in ("comp_min", "comp_max"):
        value = getattr(raw, name)
        if value is None:
            continue
        if value in stated:
            setattr(out, name, value)
            if raw.evidence.get(name) and contains_quote(source, raw.evidence[name]):
                evidence[name] = raw.evidence[name]
        else:
            dropped.append(name)
    if out.comp_min is not None and out.comp_max is not None and out.comp_min > out.comp_max:
        out.comp_min = out.comp_max = None
        dropped += ["comp_min", "comp_max"]
    if out.comp_min is None and out.comp_max is None and out.comp_currency is not None:
        dropped.append("comp_currency")
        out.comp_currency = None

    out.tech_stack = [t.strip() for t in raw.tech_stack if t and contains_term(source, t)]
    dropped += [f"tech_stack:{t}" for t in raw.tech_stack if t and not contains_term(source, t)]

    if raw.location_mode:
        canonical = _LOCATION.get(raw.location_mode.strip().lower())
        quote = raw.evidence.get("location_mode", "")
        if canonical and contains_quote(source, quote):
            out.location_mode, evidence["location_mode"] = canonical, quote
        else:
            dropped.append("location_mode")

    if raw.urgency_tier:
        canonical = _URGENCY.get(raw.urgency_tier.strip().lower())
        quote = raw.evidence.get("urgency_tier", "")
        if canonical and contains_quote(source, quote):
            out.urgency_tier, evidence["urgency_tier"] = canonical, quote
        else:
            dropped.append("urgency_tier")

    if raw.clearance_required is not None:
        quote = raw.evidence.get("clearance_required", "")
        if contains_quote(source, quote):
            out.clearance_required, evidence["clearance_required"] = raw.clearance_required, quote
        else:
            dropped.append("clearance_required")

    out.summary = raw.summary.strip() if raw.summary and raw.summary.strip() else None
    return out, evidence, dropped
