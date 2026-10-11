"""
Job Lead Radar module: ports for AI capabilities.

The module states what it needs; the composition root (app/core/wiring.py) binds an implementation
backed by AIService. This module therefore never imports `aiservice`, and the AI package never
imports this module. Results are data: persistence and review states stay in this module.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Protocol

AnalysisStatus = Literal["analyzed", "unavailable", "invalid_response"]


@dataclass(frozen=True)
class PostAnalysis:
    """Interpretation of a post. Values were verified against the text by the AI layer."""

    status: AnalysisStatus
    reason: Optional[str] = None
    is_hiring: Optional[bool] = None
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
    evidence: Dict[str, str] = field(default_factory=dict)
    dropped_fields: List[str] = field(default_factory=list)
    model: Optional[str] = None
    prompt_version: Optional[str] = None


class LeadAnalyzer(Protocol):
    async def analyze_post(self, text: str, platform: str) -> PostAnalysis: ...


@dataclass(frozen=True)
class OutreachDraftResult:
    status: Literal["generated", "unavailable", "invalid_response"]
    reason: Optional[str] = None
    subject: Optional[str] = None
    pitch: Optional[str] = None
    model: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


class OutreachDrafter(Protocol):
    async def draft(
        self,
        *,
        role_title: str,
        company_name: str,
        tone: str,
        tech_stack: List[str],
        comp_min: Optional[float],
        comp_max: Optional[float],
        comp_currency: Optional[str],
        candidate_background: Optional[str],
    ) -> OutreachDraftResult: ...


def get_lead_analyzer() -> LeadAnalyzer:
    raise RuntimeError("LeadAnalyzer is not wired; see app/core/wiring.py")


def get_outreach_drafter() -> OutreachDrafter:
    raise RuntimeError("OutreachDrafter is not wired; see app/core/wiring.py")
