"""
Job Lead Radar: read queries for this module's own tables (raw_posts, job_leads, outreach_drafts).
Writes for ingestion live in ingestion.py; business flow lives in service.py.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import String, cast, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import JobLead, OutreachDraft, RawPost


async def list_leads(
    db: AsyncSession,
    *,
    limit: int,
    platform: Optional[str] = None,
    min_score: Optional[float] = None,
    include_demo: bool = True,
) -> List[JobLead]:
    stmt = select(JobLead).options(selectinload(JobLead.raw_post)).order_by(desc(JobLead.created_at)).limit(limit)
    if platform:
        stmt = stmt.join(RawPost, JobLead.raw_post_id == RawPost.id).where(RawPost.platform == platform)
    if min_score is not None:
        stmt = stmt.where(JobLead.match_score >= min_score)
    if not include_demo:
        stmt = stmt.where(JobLead.is_demo.is_(False))
    return list((await db.execute(stmt)).scalars().all())


async def search_leads(db: AsyncSession, terms: List[str], limit: int) -> List[JobLead]:
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
    return list((await db.execute(stmt.order_by(desc(JobLead.created_at)).limit(limit))).scalars().all())


async def ingestion_counts(db: AsyncSession, *, hours: int = 24) -> dict:
    """Genuine (non-demo) activity over the last `hours`; labelled demo fixtures are not 'scanned posts'."""
    since = datetime.utcnow() - timedelta(hours=hours)

    async def count(stmt) -> int:
        return int((await db.execute(stmt)).scalar() or 0)

    return {
        "scanned": await count(select(func.count(RawPost.id)).where(RawPost.ingested_at >= since, RawPost.is_demo.is_(False))),
        "qualified": await count(
            select(func.count(JobLead.id)).where(JobLead.created_at >= since, JobLead.is_hiring.is_(True), JobLead.is_demo.is_(False))
        ),
        "discarded": await count(
            select(func.count(RawPost.id)).where(
                RawPost.ingested_at >= since, RawPost.classification == "seeking", RawPost.is_demo.is_(False)
            )
        ),
        "awaiting": await count(
            select(func.count(RawPost.id)).where(
                RawPost.ingested_at >= since, RawPost.is_processed.is_(False), RawPost.is_demo.is_(False)
            )
        ),
        "demo_posts": await count(select(func.count(RawPost.id)).where(RawPost.is_demo.is_(True))),
        # the same measures over labelled demo fixtures, reported separately and never mixed into the above
        "demo_scanned": await count(select(func.count(RawPost.id)).where(RawPost.ingested_at >= since, RawPost.is_demo.is_(True))),
        "demo_qualified": await count(
            select(func.count(JobLead.id)).where(JobLead.created_at >= since, JobLead.is_hiring.is_(True), JobLead.is_demo.is_(True))
        ),
        "demo_discarded": await count(
            select(func.count(RawPost.id)).where(
                RawPost.ingested_at >= since, RawPost.classification == "seeking", RawPost.is_demo.is_(True)
            )
        ),
        "demo_awaiting": await count(
            select(func.count(RawPost.id)).where(
                RawPost.ingested_at >= since, RawPost.is_processed.is_(False), RawPost.is_demo.is_(True)
            )
        ),
    }


async def source_channels(db: AsyncSession) -> List[str]:
    rows = await db.execute(select(RawPost.source_channel).where(RawPost.is_demo.is_(False)).distinct().order_by(RawPost.source_channel))
    return list(rows.scalars().all())


async def recent_drafts(db: AsyncSession, limit: int) -> List[OutreachDraft]:
    stmt = select(OutreachDraft).order_by(desc(OutreachDraft.created_at)).limit(limit)
    return list((await db.execute(stmt)).scalars().all())
