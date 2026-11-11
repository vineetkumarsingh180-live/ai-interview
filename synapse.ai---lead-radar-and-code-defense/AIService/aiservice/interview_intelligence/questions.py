"""
Interview intelligence: follow-up questions from real answers and repository-specific questions.

Nothing here scores an answer or produces a hire/reject view. If the provider is unavailable the
result says so; generic questions are never passed off as repository-specific output.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Literal, Optional, Sequence

from pydantic import BaseModel, ConfigDict, Field

from ..code_intelligence.evidence import RepositoryEvidence, render_for_prompt
from ..errors import AIServiceError, InvalidProviderResponse, ProviderNotConfigured
from ..prompts import INTERVIEW_FOLLOW_UP, REPOSITORY_QUESTIONS
from ..providers.base import LLMProvider, Usage, parse_model

logger = logging.getLogger("aiservice.interview")

_MAX_TURNS = 6


@dataclass(frozen=True)
class Turn:
    speaker: str      # "ai_interviewer" | "candidate"
    text: str


@dataclass
class FollowUp:
    status: Literal["generated", "unavailable", "invalid_response"]
    question: Optional[str] = None
    reason: Optional[str] = None
    model: Optional[str] = None
    usage: Usage = Usage()


@dataclass
class RepositoryQuestion:
    question: str
    paths: List[str]          # files the question is based on (all verified to be in the evidence)


@dataclass
class RepositoryQuestions:
    status: Literal["generated", "unavailable", "invalid_response"]
    questions: List[RepositoryQuestion] = field(default_factory=list)
    reason: Optional[str] = None
    discarded: int = 0
    model: Optional[str] = None
    usage: Usage = Usage()


class _RawQuestion(BaseModel):
    model_config = ConfigDict(extra="ignore")
    question: str
    paths: List[str] = Field(default_factory=list)


class _RawQuestions(BaseModel):
    model_config = ConfigDict(extra="ignore")
    questions: List[_RawQuestion] = Field(default_factory=list)


class InterviewIntelligence:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    async def follow_up_question(self, turns: Sequence[Turn]) -> FollowUp:
        if not self._provider.is_configured():
            return FollowUp(status="unavailable", reason=ProviderNotConfigured.code)
        if not any(t.speaker == "candidate" for t in turns):
            return FollowUp(status="invalid_response", reason="no_candidate_answer")
        history = "\n".join(f"{t.speaker}: {t.text}" for t in list(turns)[-_MAX_TURNS:])
        try:
            generation = await self._provider.generate_text(
                prompt=f"Dialogue:\n{history}\n\nNext interviewer question:",
                system=INTERVIEW_FOLLOW_UP.system, temperature=0.4, max_output_tokens=160,
            )
        except AIServiceError as exc:
            logger.warning("Follow-up unavailable: %s", exc.code)
            status = "invalid_response" if isinstance(exc, InvalidProviderResponse) else "unavailable"
            return FollowUp(status=status, reason=exc.code)  # type: ignore[arg-type]
        question = generation.text.strip()
        if not question:
            return FollowUp(status="invalid_response", reason="empty_response")
        return FollowUp(status="generated", question=question, model=generation.model, usage=generation.usage)

    async def repository_questions(self, evidence: RepositoryEvidence) -> RepositoryQuestions:
        if not evidence.files:
            return RepositoryQuestions(status="unavailable", reason="repository_content_not_available")
        if not self._provider.is_configured():
            return RepositoryQuestions(status="unavailable", reason=ProviderNotConfigured.code)
        try:
            generation = await self._provider.generate_json(
                prompt=render_for_prompt(evidence), system=REPOSITORY_QUESTIONS.system, temperature=0.3
            )
            raw = parse_model(generation, _RawQuestions)
        except InvalidProviderResponse as exc:
            return RepositoryQuestions(status="invalid_response", reason=exc.code)
        except AIServiceError as exc:
            return RepositoryQuestions(status="unavailable", reason=exc.code)
        known = set(evidence.paths)
        kept: List[RepositoryQuestion] = []
        discarded = 0
        for q in raw.questions:
            paths = [p for p in q.paths if p in known]
            if q.question.strip() and paths and len(paths) == len(q.paths):
                kept.append(RepositoryQuestion(q.question.strip(), paths))
            else:
                discarded += 1
        return RepositoryQuestions(
            status="generated" if kept else "invalid_response",
            questions=kept, discarded=discarded, reason=None if kept else "no_question_cited_a_supplied_file",
            model=generation.model, usage=generation.usage,
        )
