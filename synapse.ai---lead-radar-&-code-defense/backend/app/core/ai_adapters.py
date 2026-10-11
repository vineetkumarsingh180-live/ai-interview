"""
Adapters from module-owned AI ports to AIService (composition root only).

Each adapter translates between a module's small domain dataclasses and AIService's result types.
Neither side imports the other: modules know ports, AIService knows nothing of modules.
"""

from typing import Callable, Dict, List, Optional, Tuple

from aiservice import (
    CodeIntelligence,
    InterviewIntelligence,
    LeadIntelligence,
    LLMProvider,
    OutreachRequest,
    Turn,
    prepare_evidence,
)

from app.modules import code_verifier, job_lead_radar, voice_defense

ProviderFactory = Callable[[], LLMProvider]


class AIServiceLeadAnalyzer:
    def __init__(self, provider: ProviderFactory) -> None:
        self._provider = provider

    async def analyze_post(self, text: str, platform: str) -> job_lead_radar.PostAnalysis:
        r = await LeadIntelligence(self._provider()).analyze_post(text, platform)
        f = r.fields
        return job_lead_radar.PostAnalysis(
            status=r.status, reason=r.reason, is_hiring=r.is_hiring,
            role_title=f.role_title, company_name=f.company_name, company_stage=f.company_stage,
            comp_min=f.comp_min, comp_max=f.comp_max, comp_currency=f.comp_currency, equity_note=f.equity_note,
            tech_stack=list(f.tech_stack), location_mode=f.location_mode, clearance_required=f.clearance_required,
            urgency_tier=f.urgency_tier, contact_anchor=f.contact_anchor, summary=f.summary,
            evidence=dict(r.evidence), dropped_fields=list(r.dropped_fields),
            model=r.model, prompt_version=r.prompt_version,
        )


class AIServiceOutreachDrafter:
    def __init__(self, provider: ProviderFactory) -> None:
        self._provider = provider

    async def draft(
        self, *, role_title: str, company_name: str, tone: str, tech_stack: List[str],
        comp_min: Optional[float], comp_max: Optional[float], comp_currency: Optional[str],
        candidate_background: Optional[str],
    ) -> job_lead_radar.OutreachDraftResult:
        r = await LeadIntelligence(self._provider()).draft_outreach(
            OutreachRequest(
                role_title=role_title, company_name=company_name, tone=tone, tech_stack=tech_stack,
                comp_min=comp_min, comp_max=comp_max, comp_currency=comp_currency,
                candidate_background=candidate_background,
            )
        )
        return job_lead_radar.OutreachDraftResult(
            status=r.status, reason=r.reason, subject=r.subject, pitch=r.pitch, model=r.model,
            prompt_tokens=r.usage.prompt_tokens, completion_tokens=r.usage.completion_tokens,
        )


class AIServiceInterviewer:
    def __init__(self, provider: ProviderFactory) -> None:
        self._provider = provider

    async def follow_up(self, turns: List[Dict[str, str]]) -> voice_defense.FollowUpQuestion:
        r = await InterviewIntelligence(self._provider()).follow_up_question(
            [Turn(t["speaker"], t["text"]) for t in turns]
        )
        return voice_defense.FollowUpQuestion(status=r.status, question=r.question, reason=r.reason)


class AIServiceRepositoryAnalyzer:
    def __init__(self, provider: ProviderFactory) -> None:
        self._provider = provider

    async def analyze(
        self, *, repo_url: str, commit_sha: Optional[str], files: List[Tuple[str, str]]
    ) -> code_verifier.RepositoryAnalysis:
        evidence = prepare_evidence(repo_url, files, commit_sha=commit_sha)
        r = await CodeIntelligence(self._provider()).analyze(evidence)
        return code_verifier.RepositoryAnalysis(
            status=r.status, reason=r.reason, facts=dict(r.facts), summary=r.summary,
            interview_topics=list(r.interview_topics), model=r.model,
        )
