"""
Leaderboard module: public contract used by the composition root to satisfy other modules.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from .service import LeaderboardService


class LeaderboardRecorder:
    """Implements Voice Defense's `LeaderboardPublisher` port without importing that module."""

    async def publish_voice_result(
        self,
        db: AsyncSession,
        *,
        session_id: UUID,
        candidate_name: str,
        candidate_handle: Optional[str],
        repo_name: Optional[str],
        target_role: Optional[str],
        composite_score: Optional[float],
    ) -> None:
        await LeaderboardService.record_voice_result(
            db,
            session_id=session_id,
            candidate_name=candidate_name,
            candidate_handle=candidate_handle,
            repo_name=repo_name,
            target_role=target_role,
            composite_score=composite_score,
        )
