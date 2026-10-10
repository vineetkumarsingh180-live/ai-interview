"""
Leaderboard module: HTTP routes.
The path stays under /assessment/voice for URL compatibility with existing clients.
"""

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database import get_db

from .schemas import LeaderboardScoreResponse
from .service import LeaderboardService

router = APIRouter(prefix="/assessment/voice", tags=["Leaderboard"])


@router.get(
    "/leaderboard",
    response_model=List[LeaderboardScoreResponse],
    summary="Assessed candidates (newest first); unmeasured scores are null",
)
async def get_leaderboard(limit: int = Query(20, ge=1, le=100), db: AsyncSession = Depends(get_db)):
    return await LeaderboardService.list_leaderboard(db=db, limit=limit)
