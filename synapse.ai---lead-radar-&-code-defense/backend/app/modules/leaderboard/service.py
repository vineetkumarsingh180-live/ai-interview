"""
Leaderboard module: result recording and listing.

Rows come only from interview sessions. Scores that were not measured stay NULL; there are no
percentiles, tiers or hiring tags unless a real evaluator provides them.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import LeaderboardScore

REVIEW_STATE = "needs_human_review"


class LeaderboardService:
    @staticmethod
    async def record_voice_result(
        db: AsyncSession,
        *,
        session_id: UUID,
        candidate_name: str,
        candidate_handle: Optional[str],
        repo_name: Optional[str],
        target_role: Optional[str],
        composite_score: Optional[float],
    ) -> None:
        stmt = select(LeaderboardScore).where(LeaderboardScore.session_id == session_id)
        row = (await db.execute(stmt)).scalar_one_or_none()
        if row is None:
            row = LeaderboardScore(
                session_id=session_id,
                candidate_name=candidate_name,
                candidate_handle=candidate_handle,
                repo_name=repo_name,
                target_role=target_role,
                voice_defense_score=composite_score,
                status_tag=REVIEW_STATE,
            )
            db.add(row)
        else:
            row.voice_defense_score = composite_score
            row.candidate_handle = candidate_handle or row.candidate_handle
            row.repo_name = repo_name or row.repo_name
            row.target_role = target_role or row.target_role
        await db.commit()

    @staticmethod
    async def list_leaderboard(db: AsyncSession, limit: int = 20) -> List[LeaderboardScore]:
        stmt = select(LeaderboardScore).order_by(desc(LeaderboardScore.recorded_at)).limit(limit)
        return list((await db.execute(stmt)).scalars().all())
