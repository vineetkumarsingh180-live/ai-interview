"""
Job Lead Radar module: ingestion, AI parsing, search and outreach drafting.

Honesty rules: nothing is invented. If the AI provider is unavailable a post is stored as
"awaiting analysis"; outreach drafting then reports 503 instead of returning template text.
"""

import logging
from typing import List, Optional, Tuple

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.errors import ApiError, Conflict, NotFound, ServiceUnavailable
from app.shared.ingestion_log import DUPLICATE, REJECTED, IngestContext

from . import repository
from .ingestion import PostRecord, ingest_post_record
from .interfaces import LeadAnalyzer, OutreachDrafter, PostAnalysis
from .models import JobLead, OutreachDraft, RawPost
from .schemas import (
    IngestOutcome,
    JobLeadResponse,
    LeadSearchHit,
    OutreachDraftRequest,
    RawPostCreate,
)

logger = logging.getLogger("synapse.lead_radar")

AI_UNAVAILABLE = "AI analysis is unavailable (GEMINI_API_KEY is not configured or the provider did not answer)."
AI_UNUSABLE = "The AI provider answered with an unusable result; the post is stored and can be analysed again."


def _enrichment(parsed: PostAnalysis) -> dict:
    """What the AI layer reported about its own result: summary, verified evidence, dropped claims."""
    meta: dict = {}
    if parsed.summary:
        meta["summary"] = parsed.summary
    if parsed.evidence:
        meta["evidence"] = parsed.evidence
    if parsed.dropped_fields:
        meta["unverified_fields_dropped"] = parsed.dropped_fields
    if parsed.model:
        meta["ai"] = {"model": parsed.model, "prompt_version": parsed.prompt_version}
    return meta

class SocialIngestionService:
    @staticmethod
    async def ingest_post(
        db: AsyncSession, post_data: RawPostCreate, analyzer: LeadAnalyzer
    ) -> Tuple[IngestOutcome, Optional[JobLead]]:
        """
        Stores the post through the same ingestion function DbIngestion uses (dedup + provenance),
        then asks the analyzer (AIService behind a port) to interpret it. See IngestOutcome.status.
        """
        record = PostRecord(
            platform=post_data.platform,
            raw_content=post_data.raw_content,
            external_id=post_data.external_id,
            author_handle=post_data.author_handle,
            author_name=post_data.author_name,
            source_channel=post_data.source_channel,
        )
        stored = await ingest_post_record(db, record, IngestContext(source_type="api_manual"))
        if stored.status == DUPLICATE:
            await db.rollback()
            raise Conflict("An identical post was already submitted.", code="duplicate_post")
        if stored.status == REJECTED:
            await db.rollback()
            raise ApiError(stored.message or "The post was rejected.", code=stored.code or "rejected", status_code=422)
        raw_post: RawPost = stored.obj
        if post_data.author_avatar_url:
            raw_post.author_avatar_url = post_data.author_avatar_url

        parsed = await analyzer.analyze_post(post_data.raw_content, post_data.platform)

        if parsed.status != "analyzed":
            # Stored for a later retry; nothing was inferred.
            await db.commit()
            reason = AI_UNAVAILABLE if parsed.status == "unavailable" else AI_UNUSABLE
            return IngestOutcome(status="awaiting_analysis", raw_post_id=raw_post.id, reason=reason), None

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
            entry_source="ai_extracted",
            enrichment_metadata=_enrichment(parsed),
        )
        raw_post.is_processed = True
        db.add(lead)
        await db.commit()
        await db.refresh(lead)
        lead.raw_post = raw_post
        return IngestOutcome(status="created", raw_post_id=raw_post.id, lead=JobLeadResponse.model_validate(lead)), lead

    @staticmethod
    async def list_recent_leads(
        db: AsyncSession, limit: int = 25, platform: Optional[str] = None, min_score: Optional[float] = None,
        include_demo: bool = True,
    ) -> List[JobLead]:
        return await repository.list_leads(db, limit=limit, platform=platform, min_score=min_score, include_demo=include_demo)

    @staticmethod
    async def get_telemetry(db: AsyncSession) -> dict:
        """Counts over the last 24 hours of genuine (non-demo) posts. Latency is not measured."""
        c = await repository.ingestion_counts(db)
        return {
            "total_scanned_24h": c["scanned"],
            "qualified_leads_count": c["qualified"],
            "seeking_discarded_count": c["discarded"],
            "awaiting_analysis_count": c["awaiting"],
            "demo_posts_count": c["demo_posts"],
            "demo_scanned_24h": c["demo_scanned"],
            "demo_qualified_leads_count": c["demo_qualified"],
            "demo_seeking_discarded_count": c["demo_discarded"],
            "demo_awaiting_analysis_count": c["demo_awaiting"],
            "channels_monitored": await repository.source_channels(db),
            "avg_latency_ms": None,
        }


class OutreachService:
    @staticmethod
    async def generate_outreach_pitch(
        db: AsyncSession, request: OutreachDraftRequest, drafter: OutreachDrafter
    ) -> OutreachDraft:
        """Drafts a message with the AI provider. Never returns template text as if it were AI output."""
        lead = await db.get(JobLead, request.lead_id)
        if not lead:
            raise NotFound(f"Lead {request.lead_id} was not found.")
        result = await drafter.draft(
            role_title=lead.role_title,
            company_name=lead.company_name,
            tone=request.tone,
            tech_stack=list(lead.tech_stack or []),
            comp_min=lead.comp_min,
            comp_max=lead.comp_max,
            comp_currency=lead.comp_currency,
            candidate_background=request.candidate_profile_context,
        )
        if result.status == "unavailable" and result.reason == "not_configured":
            raise ServiceUnavailable(
                "Outreach drafting needs the AI provider, which is not configured (GEMINI_API_KEY).",
                code="ai_unavailable",
            )
        if result.status != "generated" or not result.pitch:
            raise ServiceUnavailable("The AI provider did not return a usable draft. Try again.", code="ai_unavailable")

        draft = OutreachDraft(
            lead_id=lead.id,
            tone=request.tone,
            pitch_subject=(result.subject or "")[:255],
            generated_pitch=result.pitch,
            candidate_profile_context=request.candidate_profile_context,
            status="draft",
            model_version=result.model,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
        )
        db.add(draft)
        await db.commit()
        await db.refresh(draft)
        return draft

    @staticmethod
    async def search_leads(db: AsyncSession, query_text: str, top_k: int = 10) -> List[LeadSearchHit]:
        """Plain keyword search (title, company, stack). Semantic search needs embeddings that do not exist yet."""
        terms = [t for t in query_text.lower().split() if t][:8]
        leads = await repository.search_leads(db, terms, top_k)
        return [LeadSearchHit(lead=JobLeadResponse.model_validate(lead)) for lead in leads]
