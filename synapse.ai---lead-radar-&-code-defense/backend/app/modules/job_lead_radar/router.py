"""
Job Lead Radar module: HTTP routes (URLs unchanged).
Errors are raised as ApiError subclasses and converted by app.shared.errors.
"""

from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database import get_db

from .models import OutreachDraft
from .schemas import (
    IngestionTelemetryResponse,
    IngestOutcome,
    JobLeadResponse,
    LeadSearchHit,
    LeadSearchQuery,
    OutreachDraftRequest,
    OutreachDraftResponse,
    ParsedLeadExtraction,
    RawPostCreate,
)
from .service import AI_UNAVAILABLE, OutreachService, SocialIngestionService
from app.shared.errors import ServiceUnavailable

ingestion_router = APIRouter(prefix="/leads/ingest", tags=["Job Lead Radar"])
outreach_router = APIRouter(prefix="/leads", tags=["Job Lead Radar"])


@ingestion_router.post(
    "/trigger",
    response_model=IngestOutcome,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a social post; it is stored, then analysed (see `status`)",
)
async def trigger_ingestion(post: RawPostCreate, db: AsyncSession = Depends(get_db)):
    outcome, _ = await SocialIngestionService.ingest_post(db=db, post_data=post)
    return outcome


@ingestion_router.post(
    "/parse-text",
    response_model=ParsedLeadExtraction,
    summary="Run the AI extraction on arbitrary text without storing anything",
)
async def parse_raw_text(
    text_content: str = Query(..., min_length=1, max_length=20000),
    platform: Literal["twitter", "linkedin", "reddit", "telegram"] = "twitter",
):
    parsed = await SocialIngestionService.parse_with_gemini(text_content, platform)
    if parsed is None:
        raise ServiceUnavailable(AI_UNAVAILABLE, code="ai_unavailable")
    return parsed


@ingestion_router.get(
    "/recent",
    response_model=List[JobLeadResponse],
    summary="Recent analysed leads (newest first)",
)
async def get_recent_leads(
    limit: int = Query(25, ge=1, le=100),
    platform: Optional[Literal["twitter", "linkedin", "reddit", "telegram"]] = None,
    min_score: Optional[float] = Query(None, ge=0.0, le=100.0),
    db: AsyncSession = Depends(get_db),
):
    return await SocialIngestionService.list_recent_leads(db=db, limit=limit, platform=platform, min_score=min_score)


@ingestion_router.get(
    "/telemetry",
    response_model=IngestionTelemetryResponse,
    summary="Ingestion counts over the last 24 hours, computed from stored posts",
)
async def get_telemetry(db: AsyncSession = Depends(get_db)):
    return await SocialIngestionService.get_telemetry(db=db)


@outreach_router.post(
    "/outreach/generate",
    response_model=OutreachDraftResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Draft an outreach message with the AI provider (503 when unavailable)",
)
async def generate_outreach(request: OutreachDraftRequest, db: AsyncSession = Depends(get_db)):
    return await OutreachService.generate_outreach_pitch(db=db, request=request)


@outreach_router.post(
    "/search",
    response_model=List[LeadSearchHit],
    summary="Keyword search over leads (semantic search is not available yet)",
)
async def search_leads(query: LeadSearchQuery, db: AsyncSession = Depends(get_db)):
    return await OutreachService.search_leads(db=db, query_text=query.query_text, top_k=query.top_k)


@outreach_router.get(
    "/outreach/history",
    response_model=List[OutreachDraftResponse],
    summary="Previously generated drafts (newest first)",
)
async def get_outreach_history(limit: int = Query(20, ge=1, le=100), db: AsyncSession = Depends(get_db)):
    stmt = select(OutreachDraft).order_by(desc(OutreachDraft.created_at)).limit(limit)
    return list((await db.execute(stmt)).scalars().all())


# One router for the whole module (ingestion + outreach); URLs are unchanged.
router = APIRouter()
router.include_router(ingestion_router)
router.include_router(outreach_router)
