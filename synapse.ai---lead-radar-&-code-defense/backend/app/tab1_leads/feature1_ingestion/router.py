"""
FastAPI Modular Router for Social Ingestion & AI Parser (Tab 1, Feature 1)
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.tab1_leads.feature1_ingestion.schemas import (
    JobLeadResponse,
    RawPostCreate,
    ParsedLeadExtraction,
    IngestionTelemetryResponse,
)
from app.tab1_leads.feature1_ingestion.service import SocialIngestionService

router = APIRouter(prefix="/leads/ingest", tags=["Tab 1 - Lead Ingestion"])

@router.post(
    "/trigger",
    response_model=JobLeadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest and parse a new social post into a structured JobLead"
)
async def trigger_ingestion(
    post: RawPostCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        lead = await SocialIngestionService.ingest_post(db=db, post_data=post)
        return lead
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest post: {str(e)}"
        )

@router.post(
    "/parse-text",
    response_model=ParsedLeadExtraction,
    summary="Directly test Gemini binary filter and schema extraction on arbitrary text"
)
async def parse_raw_text(
    text_content: str = Query(..., description="Unstructured post text"),
    platform: str = Query("twitter", description="Origin platform")
):
    parsed = await SocialIngestionService.parse_with_gemini(text_content, platform)
    if not parsed:
        raise HTTPException(status_code=400, detail="Unable to extract structured lead")
    return parsed

@router.get(
    "/recent",
    response_model=List[JobLeadResponse],
    summary="Fetch the live stream of analyzed social leads"
)
async def get_recent_leads(
    limit: int = Query(25, ge=1, le=100),
    platform: Optional[str] = None,
    min_score: float = Query(0.0, ge=0.0, le=100.0),
    db: AsyncSession = Depends(get_db)
):
    leads = await SocialIngestionService.list_recent_leads(
        db=db, limit=limit, platform=platform, min_score=min_score
    )
    return leads

@router.get(
    "/telemetry",
    response_model=IngestionTelemetryResponse,
    summary="Retrieve real-time scanning radar telemetry"
)
async def get_telemetry(db: AsyncSession = Depends(get_db)):
    return await SocialIngestionService.get_telemetry(db=db)
