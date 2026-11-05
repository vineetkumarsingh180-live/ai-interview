"""
Job Lead Radar: public ingestion interface used by DbIngestion and the API route.

`ingest_post_record` validates a post, deduplicates it, stores the original text with its
provenance and, only when the operator supplied structured fields, creates a lead from them. It
never calls an AI provider and never labels user-provided text as verified. It flushes but does not
commit: the caller owns the transaction.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.ingestion_log import (
    CREATED,
    DUPLICATE,
    REJECTED,
    IngestContext,
    IngestionResult,
)

from .models import JobLead, RawPost
from .provenance import content_hash, normalize_post_text

PLATFORMS = ("twitter", "linkedin", "reddit", "telegram")
MAX_TEXT = 20000


@dataclass
class StructuredLead:
    """Fields an operator entered by hand. Nothing here is inferred."""

    role_title: str
    company_name: str
    company_stage: Optional[str] = None
    comp_min: Optional[float] = None
    comp_max: Optional[float] = None
    comp_currency: Optional[str] = None
    equity_note: Optional[str] = None
    tech_stack: List[str] = field(default_factory=list)
    location_mode: Optional[str] = None
    contact_anchor: Optional[str] = None
    # Showcase-only fields. Nothing in the product measures these yet, so they are accepted ONLY for
    # labelled demo fixtures (ctx.is_demo) and refused for any genuine record.
    match_score: Optional[float] = None
    urgency_tier: Optional[str] = None
    summary: Optional[str] = None


@dataclass
class PostRecord:
    platform: str
    raw_content: str
    external_id: Optional[str] = None
    author_handle: Optional[str] = None
    author_name: Optional[str] = None
    source_url: Optional[str] = None
    posted_at: Optional[datetime] = None
    source_channel: str = "Manual import"
    note: Optional[str] = None
    structured: Optional[StructuredLead] = None
    # Showcase-only: mark a demo post as a job seeker (discarded). Refused for genuine records.
    demo_classification: Optional[str] = None


def _reject(code: str, message: str) -> IngestionResult:
    return IngestionResult(status=REJECTED, entity="raw_post", code=code, message=message)


async def ingest_post_record(db: AsyncSession, record: PostRecord, ctx: IngestContext) -> IngestionResult:
    platform = (record.platform or "").strip().lower()
    if platform not in PLATFORMS:
        return _reject("invalid_platform", f"platform must be one of {', '.join(PLATFORMS)}")
    text = record.raw_content or ""
    if not text.strip():
        return _reject("empty_text", "the post text is empty")
    if len(text) > MAX_TEXT:
        return _reject("text_too_long", f"the post text exceeds {MAX_TEXT} characters")
    if record.source_url and not record.source_url.lower().startswith(("http://", "https://")):
        return _reject("invalid_source_url", "source_url must start with http:// or https://")
    s = record.structured
    if s is not None and not (s.role_title and s.role_title.strip() and s.company_name and s.company_name.strip()):
        return _reject("incomplete_structured_fields", "structured fields need both role_title and company_name")
    if s is not None and not ctx.is_demo and (s.match_score is not None or s.urgency_tier or s.summary):
        return _reject("unmeasured_fields_not_allowed",
                       "match_score, urgency_tier and summary are only accepted for labelled demo fixtures")

    if record.demo_classification is not None:
        if not ctx.is_demo:
            return _reject("unmeasured_fields_not_allowed", "demo_classification is only accepted for labelled demo fixtures")
        if record.demo_classification != "seeking" or s is not None:
            return _reject("invalid_demo_classification", "demo_classification must be 'seeking' and cannot carry structured fields")

    digest = content_hash(platform, text)
    existing = (await db.execute(select(RawPost).where(RawPost.content_hash == digest))).scalar_one_or_none()
    if existing is None and record.external_id:
        existing = (await db.execute(select(RawPost).where(RawPost.external_id == record.external_id))).scalar_one_or_none()
        if existing is not None and existing.content_hash != digest:
            return IngestionResult(
                status=REJECTED, entity="raw_post", entity_id=existing.id, code="external_id_conflict",
                message="this external_id already exists with different text",
            )
    if existing is not None:
        return IngestionResult(
            status=DUPLICATE, entity="raw_post", entity_id=existing.id, code="duplicate_content", obj=existing,
            message="an identical post (same platform and text) is already stored",
        )

    external_id = record.external_id or f"{ctx.source_type}-{digest[:20]}"
    post = RawPost(
        platform=platform,
        external_id=external_id,
        author_handle=(record.author_handle or "unknown").strip()[:120],
        author_name=(record.author_name or "Unknown").strip()[:255],
        raw_content=text,                       # original text, unmodified
        source_channel=(record.source_channel or "Manual import")[:120],
        source_type=ctx.source_type,
        verification_status="demo_fixture" if ctx.is_demo else "unverified",
        source_url=record.source_url,
        posted_at=record.posted_at,
        content_hash=digest,
        provenance={"note": record.note, "normalised_length": len(normalize_post_text(text))},
        is_demo=ctx.is_demo,
        ingestion_run_id=ctx.run_id,
        is_processed=record.demo_classification is not None,
        classification=record.demo_classification,
    )
    try:
        async with db.begin_nested():
            db.add(post)
            await db.flush()
            lead_id: Optional[uuid.UUID] = None
            if s is not None:
                lead = JobLead(
                    raw_post_id=post.id,
                    role_title=s.role_title.strip(),
                    company_name=s.company_name.strip(),
                    company_stage=s.company_stage,
                    comp_min=s.comp_min,
                    comp_max=s.comp_max,
                    comp_currency=s.comp_currency,
                    equity_note=s.equity_note,
                    tech_stack=list(s.tech_stack),
                    location_mode=s.location_mode,
                    contact_anchor=s.contact_anchor,
                    is_hiring=True,
                    match_score=s.match_score if ctx.is_demo else None,
                    urgency_tier=s.urgency_tier if ctx.is_demo else None,
                    entry_source="demo_fixture" if ctx.is_demo else "operator_entered",
                    is_demo=ctx.is_demo,
                    enrichment_metadata=({"summary": s.summary, "demo_fixture": True} if ctx.is_demo and s.summary else {}),
                )
                db.add(lead)
                post.classification = "hiring"
                post.is_processed = True
                await db.flush()
                lead_id = lead.id
    except IntegrityError:
        return IngestionResult(status=DUPLICATE, entity="raw_post", code="duplicate_race",
                               message="the post was inserted concurrently by another process")
    return IngestionResult(
        status=CREATED, entity="raw_post", entity_id=post.id, obj=post,
        detail={"lead_id": str(lead_id) if lead_id else None, "awaiting_analysis": lead_id is None},
    )


async def delete_posts(db: AsyncSession, *, run_id=None, demo_only: bool = False) -> int:
    """
    Delete posts (and, by cascade, their leads) created by one ingestion run, or all labelled demo
    rows. Never anything else.
    """
    from sqlalchemy import delete

    if run_id is None and not demo_only:
        raise ValueError("refusing to delete without a run id or demo_only=True")
    cond = RawPost.ingestion_run_id == run_id if run_id is not None else RawPost.is_demo.is_(True)
    result = await db.execute(delete(RawPost).where(cond))
    return int(result.rowcount or 0)
