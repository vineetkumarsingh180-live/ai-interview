"""
Job Lead Radar module: ingestion, AI parsing, search and outreach drafting.

Honesty rules: nothing is invented. If the AI provider is unavailable a post is stored as
"awaiting analysis"; outreach drafting then reports 503 instead of returning template text.
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from pydantic import ValidationError
from sqlalchemy import String, cast, desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.shared.config import settings
from app.shared.errors import Conflict, NotFound, ServiceUnavailable
from app.shared.gemini import extract_text, generate_content, is_configured, usage_tokens

from .models import JobLead, OutreachDraft, RawPost
from .schemas import (
    IngestOutcome,
    JobLeadResponse,
    LeadSearchHit,
    OutreachDraftRequest,
    ParsedLeadExtraction,
    RawPostCreate,
)

logger = logging.getLogger("synapse.lead_radar")

AI_UNAVAILABLE = "AI analysis is unavailable (GEMINI_API_KEY is not configured or the provider did not answer)."

_EXTRACTION_INSTRUCTION = (
    "You extract structured data from a social media post for a recruiting tool. "
    "Decide whether the author is HIRING (offering a job) or is a JOB SEEKER / unrelated. "
    "Extract only what the post explicitly states. If a field is not stated, use null (or an empty "
    "array for tech_stack). Never guess company names, compensation, or contacts. "
    "Return JSON with keys: is_hiring (boolean), role_title, company_name, company_stage, comp_min, "
    "comp_max, comp_currency, equity_note, tech_stack (array of strings), location_mode "
    "('Remote'|'Hybrid'|'Onsite'|null), clearance_required (boolean|null), urgency_tier "
    "('Immediate'|'High'|'Normal'|null), contact_anchor, extracted_summary."
)


class SocialIngestionService:
    @staticmethod
    async def parse_with_gemini(raw_text: str, platform: str) -> Optional[ParsedLeadExtraction]:
        """Returns the extraction, or None when the AI provider is unavailable or answered garbage."""
        if not is_configured():
            return None
        payload = {
            "contents": [{"parts": [{"text": f"Platform: {platform}\nPost text:\n\"\"\"{raw_text}\"\"\""}]}],
            "systemInstruction": {"parts": [{"text": _EXTRACTION_INSTRUCTION}]},
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1},
        }
        try:
            data = await generate_content(payload, timeout=20.0)
            text = extract_text(data)
            if text is None:
                return None
            return ParsedLeadExtraction(**json.loads(text))
        except (ValidationError, ValueError, KeyError, TypeError) as exc:
            logger.warning("Unusable AI extraction: %s", type(exc).__name__)
            return None
        except Exception as exc:  # network / provider failure
            logger.error("AI extraction failed: %s", type(exc).__name__)
            return None

    @staticmethod
    async def ingest_post(db: AsyncSession, post_data: RawPostCreate) -> Tuple[IngestOutcome, Optional[JobLead]]:
        """Stores the raw post, then analyses it. See IngestOutcome.status for what happened."""
        raw_post = RawPost(
            platform=post_data.platform,
            external_id=post_data.external_id or f"manual-{uuid.uuid4().hex[:16]}",
            author_handle=post_data.author_handle or "unknown",
            author_name=post_data.author_name or "Unknown",
            author_avatar_url=post_data.author_avatar_url,
            raw_content=post_data.raw_content,
            source_channel=post_data.source_channel,
            is_processed=False,
            classification=None,
        )
        db.add(raw_post)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            raise Conflict("A post with this externalId was already submitted.", code="duplicate_post")

        parsed = await SocialIngestionService.parse_with_gemini(post_data.raw_content, post_data.platform)

        if parsed is None:
            await db.commit()
            return IngestOutcome(status="awaiting_analysis", raw_post_id=raw_post.id, reason=AI_UNAVAILABLE), None

        if not parsed.is_hiring:
            raw_post.classification = "seeking"
            raw_post.is_processed = True
            await db.commit()
            return (
                IngestOutcome(
                    status="discarded",
                    raw_post_id=raw_post.id,
                    reason="Classified as a job seeker or unrelated post; no lead was created.",
                ),
                None,
            )

        raw_post.classification = "hiring"
        if not parsed.role_title or not parsed.company_name:
            await db.commit()
            return (
                IngestOutcome(
                    status="needs_review",
                    raw_post_id=raw_post.id,
                    reason="Classified as hiring, but the role or company is not stated in the post.",
                ),
                None,
            )

        lead = JobLead(
            raw_post_id=raw_post.id,
            role_title=parsed.role_title,
            company_name=parsed.company_name,
            company_stage=parsed.company_stage,
            comp_min=parsed.comp_min,
            comp_max=parsed.comp_max,
            comp_currency=parsed.comp_currency,
            equity_note=parsed.equity_note,
            tech_stack=parsed.tech_stack,
            location_mode=parsed.location_mode,
            clearance_required=parsed.clearance_required,
            is_hiring=True,
            match_score=None,
            urgency_tier=parsed.urgency_tier,
            contact_anchor=parsed.contact_anchor,
            enrichment_metadata={"summary": parsed.extracted_summary} if parsed.extracted_summary else {},
        )
        raw_post.is_processed = True
        db.add(lead)
        await db.commit()
        await db.refresh(lead)
        lead.raw_post = raw_post
        return IngestOutcome(status="created", raw_post_id=raw_post.id, lead=JobLeadResponse.model_validate(lead)), lead

    @staticmethod
    async def list_recent_leads(
        db: AsyncSession, limit: int = 25, platform: Optional[str] = None, min_score: Optional[float] = None
    ) -> List[JobLead]:
        stmt = select(JobLead).options(selectinload(JobLead.raw_post)).order_by(desc(JobLead.created_at)).limit(limit)
        if platform:
            stmt = stmt.join(RawPost, JobLead.raw_post_id == RawPost.id).where(RawPost.platform == platform)
        if min_score is not None:
            stmt = stmt.where(JobLead.match_score >= min_score)
        return list((await db.execute(stmt)).scalars().all())

    @staticmethod
    async def get_telemetry(db: AsyncSession) -> dict:
        """Counts over the last 24 hours, straight from the tables. Latency is not measured."""
        since = datetime.utcnow() - timedelta(hours=24)

        async def count(stmt) -> int:
            return int((await db.execute(stmt)).scalar() or 0)

        scanned = await count(select(func.count(RawPost.id)).where(RawPost.ingested_at >= since))
        qualified = await count(
            select(func.count(JobLead.id)).where(JobLead.created_at >= since, JobLead.is_hiring.is_(True))
        )
        discarded = await count(
            select(func.count(RawPost.id)).where(RawPost.ingested_at >= since, RawPost.classification == "seeking")
        )
        awaiting = await count(
            select(func.count(RawPost.id)).where(RawPost.ingested_at >= since, RawPost.is_processed.is_(False))
        )
        channels = (await db.execute(select(RawPost.source_channel).distinct().order_by(RawPost.source_channel))).scalars().all()
        return {
            "total_scanned_24h": scanned,
            "qualified_leads_count": qualified,
            "seeking_discarded_count": discarded,
            "awaiting_analysis_count": awaiting,
            "channels_monitored": list(channels),
            "avg_latency_ms": None,
        }


class OutreachService:
    @staticmethod
    async def generate_outreach_pitch(db: AsyncSession, request: OutreachDraftRequest) -> OutreachDraft:
        """Drafts a message with the AI provider. Never returns template text as if it were AI output."""
        lead = await db.get(JobLead, request.lead_id)
        if not lead:
            raise NotFound(f"Lead {request.lead_id} was not found.")
        if not is_configured():
            raise ServiceUnavailable(
                "Outreach drafting needs the AI provider, which is not configured (GEMINI_API_KEY).",
                code="ai_unavailable",
            )

        background = request.candidate_profile_context or (
            "(none provided; do not invent any experience, employers or achievements)"
        )
        comp = ""
        if lead.comp_min is not None and lead.comp_max is not None:
            comp = f"- Compensation stated: {lead.comp_min:,.0f}-{lead.comp_max:,.0f} {lead.comp_currency or ''}\n"
        prompt = (
            "Write a concise cold outreach message from a candidate to a hiring contact. "
            "Use only the facts below; never invent experience, numbers or employers.\n\n"
            f"ROLE: {lead.role_title}\nCOMPANY: {lead.company_name}\n"
            f"TECH STACK: {', '.join(lead.tech_stack or []) or 'not stated'}\n{comp}"
            f"CANDIDATE BACKGROUND: {background}\nTONE: {request.tone}\n\n"
            'Return JSON: {"pitch_subject": string, "generated_pitch": string}'
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.4},
        }
        try:
            data = await generate_content(payload, timeout=25.0)
            text = extract_text(data)
            parsed = json.loads(text) if text else None
            subject, pitch = parsed["pitch_subject"], parsed["generated_pitch"]
            if not isinstance(subject, str) or not isinstance(pitch, str) or not pitch.strip():
                raise ValueError("empty draft")
        except Exception as exc:
            logger.error("Outreach generation failed: %s", type(exc).__name__)
            raise ServiceUnavailable("The AI provider did not return a usable draft. Try again.", code="ai_unavailable")

        prompt_tokens, completion_tokens = usage_tokens(data)
        draft = OutreachDraft(
            lead_id=lead.id,
            tone=request.tone,
            pitch_subject=subject.strip()[:255],
            generated_pitch=pitch,
            candidate_profile_context=request.candidate_profile_context,
            status="draft",
            model_version=settings.GEMINI_MODEL,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        db.add(draft)
        await db.commit()
        await db.refresh(draft)
        return draft

    @staticmethod
    async def search_leads(db: AsyncSession, query_text: str, top_k: int = 10) -> List[LeadSearchHit]:
        """Plain keyword search (title, company, stack). Semantic search needs embeddings that do not exist yet."""
        terms = [t for t in query_text.lower().split() if t][:8]
        stmt = select(JobLead).options(selectinload(JobLead.raw_post))
        for term in terms:
            like = f"%{term}%"
            stmt = stmt.where(
                or_(
                    JobLead.role_title.ilike(like),
                    JobLead.company_name.ilike(like),
                    cast(JobLead.tech_stack, String).ilike(like),
                )
            )
        leads = (await db.execute(stmt.order_by(desc(JobLead.created_at)).limit(top_k))).scalars().all()
        return [LeadSearchHit(lead=JobLeadResponse.model_validate(lead)) for lead in leads]
