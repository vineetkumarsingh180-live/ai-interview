"""
FastAPI Modular Router for Semantic Search & Cold Outreach (Tab 1, Feature 2)
"""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.tab1_leads.feature2_outreach.models import OutreachDraft
from app.tab1_leads.feature2_outreach.schemas import (
    OutreachDraftRequest,
    OutreachDraftResponse,
    SemanticLeadSearchQuery,
    SemanticSearchHit,
)
from app.tab1_leads.feature2_outreach.service import OutreachService

router = APIRouter(prefix="/leads", tags=["Tab 1 - Outreach & Semantic Search"])

@router.post(
    "/outreach/generate",
    response_model=OutreachDraftResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate personalized cold outreach pitch using Gemini"
)
async def generate_outreach(
    request: OutreachDraftRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        draft = await OutreachService.generate_outreach_pitch(db=db, request=request)
        return draft
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Outreach generation failed: {str(e)}")

@router.post(
    "/search",
    response_model=List[SemanticSearchHit],
    summary="Semantic vector search across parsed job leads"
)
async def search_leads(
    query: SemanticLeadSearchQuery,
    db: AsyncSession = Depends(get_db)
):
    hits = await OutreachService.semantic_search_leads(
        db=db, query_text=query.query_text, top_k=query.top_k
    )
    return hits

@router.get(
    "/outreach/history",
    response_model=List[OutreachDraftResponse],
    summary="Retrieve generated outreach drafts"
)
async def get_outreach_history(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(OutreachDraft).order_by(desc(OutreachDraft.created_at)).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())
