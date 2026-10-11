"""Outreach drafting. Only facts the caller supplies are put in the prompt; the draft is AI output."""

import logging
from dataclasses import dataclass, field
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict

from ..errors import AIServiceError, InvalidProviderResponse, ProviderNotConfigured
from ..prompts import OUTREACH_DRAFT
from ..providers.base import LLMProvider, Usage, parse_model

logger = logging.getLogger("aiservice.outreach")


@dataclass
class OutreachRequest:
    role_title: str
    company_name: str
    tone: str = "Direct Technical"
    tech_stack: List[str] = field(default_factory=list)
    comp_min: Optional[float] = None
    comp_max: Optional[float] = None
    comp_currency: Optional[str] = None
    candidate_background: Optional[str] = None


@dataclass
class OutreachResult:
    status: Literal["generated", "unavailable", "invalid_response"]
    reason: Optional[str] = None
    subject: Optional[str] = None
    pitch: Optional[str] = None
    model: Optional[str] = None
    usage: Usage = Usage()


class _Draft(BaseModel):
    model_config = ConfigDict(extra="ignore")
    pitch_subject: str
    generated_pitch: str


async def draft_outreach(provider: LLMProvider, request: OutreachRequest) -> OutreachResult:
    if not provider.is_configured():
        return OutreachResult(status="unavailable", reason=ProviderNotConfigured.code)
    comp = ""
    if request.comp_min is not None and request.comp_max is not None:
        comp = f"- Compensation stated: {request.comp_min:,.0f}-{request.comp_max:,.0f} {request.comp_currency or ''}\n"
    background = request.candidate_background or "(none provided; do not invent any experience, employers or achievements)"
    prompt = (
        f"ROLE: {request.role_title}\nCOMPANY: {request.company_name}\n"
        f"TECH STACK: {', '.join(request.tech_stack) or 'not stated'}\n{comp}"
        f"CANDIDATE BACKGROUND: {background}\nTONE: {request.tone}"
    )
    try:
        generation = await provider.generate_json(prompt=prompt, system=OUTREACH_DRAFT.system, temperature=0.4)
        draft = parse_model(generation, _Draft)
        if not draft.generated_pitch.strip():
            raise InvalidProviderResponse("The provider returned an empty draft.")
    except InvalidProviderResponse as exc:
        return OutreachResult(status="invalid_response", reason=exc.code)
    except AIServiceError as exc:
        logger.warning("Outreach unavailable: %s", exc.code)
        return OutreachResult(status="unavailable", reason=exc.code)
    return OutreachResult(
        status="generated", subject=draft.pitch_subject.strip(), pitch=draft.generated_pitch,
        model=generation.model, usage=generation.usage,
    )
