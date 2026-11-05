"""
Evidence-backed repository analysis.

Deterministic `facts` come straight from the supplied files. The model may add a summary, findings
and interview topics, but each finding must quote text that really occurs in the cited file and each
summary path must be a supplied file; anything else is discarded. No coverage, vulnerability
confirmation or authorship claim is ever produced here.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..errors import AIServiceError, InvalidProviderResponse, ProviderNotConfigured
from ..prompts import REPOSITORY_SUMMARY
from ..providers.base import LLMProvider, Usage, parse_model
from ..shared.text import contains_quote
from .evidence import RepositoryEvidence, render_for_prompt

logger = logging.getLogger("aiservice.code")


class _Finding(BaseModel):
    model_config = ConfigDict(extra="ignore")
    statement: str
    path: str
    quote: str


class _RawSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")
    summary: str
    summary_paths: List[str] = Field(default_factory=list)
    findings: List[_Finding] = Field(default_factory=list)
    interview_topics: List[str] = Field(default_factory=list)


@dataclass
class CodeFinding:
    statement: str
    path: str
    quote: str       # verified to occur in `path`


@dataclass
class CodeAnalysis:
    status: Literal["analyzed", "unavailable", "invalid_response"]
    reason: Optional[str] = None
    facts: Dict[str, object] = field(default_factory=dict)      # deterministic, always present when files exist
    summary: Optional[str] = None                                # AI interpretation, cited
    summary_paths: List[str] = field(default_factory=list)
    findings: List[CodeFinding] = field(default_factory=list)
    interview_topics: List[str] = field(default_factory=list)
    discarded_claims: int = 0
    model: Optional[str] = None
    prompt_version: Optional[str] = None
    usage: Usage = Usage()


class CodeIntelligence:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    async def analyze(self, evidence: RepositoryEvidence) -> CodeAnalysis:
        if not evidence.files:
            # e.g. only GitHub metadata was fetched: there is nothing to analyse, and nothing is invented
            return CodeAnalysis(status="unavailable", reason="repository_content_not_available")
        facts = evidence.facts()
        if not self._provider.is_configured():
            return CodeAnalysis(status="unavailable", reason=ProviderNotConfigured.code, facts=facts)
        by_path = {f.path: f.content for f in evidence.files}
        try:
            generation = await self._provider.generate_json(
                prompt=render_for_prompt(evidence), system=REPOSITORY_SUMMARY.system, temperature=0.1
            )
            raw = parse_model(generation, _RawSummary)
        except InvalidProviderResponse as exc:
            return CodeAnalysis(status="invalid_response", reason=exc.code, facts=facts, prompt_version=REPOSITORY_SUMMARY.version)
        except AIServiceError as exc:
            logger.warning("Code analysis unavailable: %s", exc.code)
            return CodeAnalysis(status="unavailable", reason=exc.code, facts=facts, prompt_version=REPOSITORY_SUMMARY.version)

        discarded = 0
        findings: List[CodeFinding] = []
        for f in raw.findings:
            if f.path in by_path and contains_quote(by_path[f.path], f.quote):
                findings.append(CodeFinding(f.statement.strip(), f.path, f.quote))
            else:
                discarded += 1
        paths = [p for p in raw.summary_paths if p in by_path]
        summary = raw.summary.strip() if raw.summary.strip() and paths else None
        if raw.summary.strip() and not paths:
            discarded += 1
        return CodeAnalysis(
            status="analyzed",
            facts=facts,
            summary=summary,
            summary_paths=paths,
            findings=findings,
            interview_topics=[t.strip() for t in raw.interview_topics if t.strip()][:10],
            discarded_claims=discarded,
            model=generation.model,
            prompt_version=REPOSITORY_SUMMARY.version,
            usage=generation.usage,
        )
