"""
Job Lead Radar module: HTTP routes (URLs unchanged).
Errors are raised as ApiError subclasses and converted by app.shared.errors.
"""

from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database import get_db

from . import repository
from .interfaces import LeadAnalyzer, OutreachDrafter, get_lead_analyzer, get_outreach_drafter
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
async def trigger_ingestion(
    post: RawPostCreate,
    db: AsyncSession = Depends(get_db),
    analyzer: LeadAnalyzer = Depends(get_lead_analyzer),
):
    outcome, _ = await SocialIngestionService.ingest_post(db=db, post_data=post, analyzer=analyzer)
    return outcome


@ingestion_router.post(
    "/parse-text",
    response_model=ParsedLeadExtraction,
    summary="Run the AI extraction on arbitrary text without storing anything",
)
async def parse_raw_text(
    text_content: str = Query(..., min_length=1, max_length=20000),
    platform: Literal["twitter", "linkedin", "reddit", "telegram"] = "twitter",
    analyzer: LeadAnalyzer = Depends(get_lead_analyzer),
):
    parsed = await analyzer.analyze_post(text_content, platform)
    if parsed.status != "analyzed" or parsed.is_hiring is None:
        raise ServiceUnavailable(AI_UNAVAILABLE, code="ai_unavailable")
    return ParsedLeadExtraction(
        is_hiring=parsed.is_hiring, role_title=parsed.role_title, company_name=parsed.company_name,
        company_stage=parsed.company_stage, comp_min=parsed.comp_min, comp_max=parsed.comp_max,
        comp_currency=parsed.comp_currency, equity_note=parsed.equity_note, tech_stack=parsed.tech_stack,
        location_mode=parsed.location_mode, clearance_required=parsed.clearance_required,
        urgency_tier=parsed.urgency_tier, contact_anchor=parsed.contact_anchor, extracted_summary=parsed.summary,
    )


@ingestion_router.get(
    "/recent",
    response_model=List[JobLeadResponse],
    summary="Recent analysed leads (newest first)",
)
async def get_recent_leads(
    limit: int = Query(25, ge=1, le=100),
    platform: Optional[Literal["twitter", "linkedin", "reddit", "telegram"]] = None,
    min_score: Optional[float] = Query(None, ge=0.0, le=100.0),
    include_demo: bool = Query(True, alias="includeDemo", description="Include labelled demo fixtures"),
    db: AsyncSession = Depends(get_db),
):
    return await SocialIngestionService.list_recent_leads(
        db=db, limit=limit, platform=platform, min_score=min_score, include_demo=include_demo
    )


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
async def generate_outreach(
    request: OutreachDraftRequest,
    db: AsyncSession = Depends(get_db),
    drafter: OutreachDrafter = Depends(get_outreach_drafter),
):
    return await OutreachService.generate_outreach_pitch(db=db, request=request, drafter=drafter)


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
    return await repository.recent_drafts(db, limit)


# One router for the whole module (ingestion + outreach); URLs are unchanged.
router = APIRouter()
router.include_router(ingestion_router)
router.include_router(outreach_router)
