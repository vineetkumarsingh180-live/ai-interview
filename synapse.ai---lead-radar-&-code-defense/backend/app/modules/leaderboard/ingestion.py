"""
Leaderboard: public ingestion interface used by DbIngestion (labelled showcase rows only).

Values are fixture values flagged `is_demo`; the review state is always `needs_human_review`,
never a hiring recommendation. Flushes but does not commit.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.ingestion_log import CREATED, REJECTED, IngestContext, IngestionResult

from .models import LeaderboardScore


@dataclass
class DemoScore:
    session_id: uuid.UUID
    candidate_name: str
    candidate_handle: Optional[str] = None
    candidate_avatar_url: Optional[str] = None
    target_role: Optional[str] = None
    repo_name: Optional[str] = None
    code_health_score: Optional[float] = None
    voice_defense_score: Optional[float] = None
    composite_percentile: Optional[float] = None
    rank_tier: Optional[str] = None
    recorded_at: Optional[datetime] = None


async def ingest_demo_score(db: AsyncSession, record: DemoScore, ctx: IngestContext) -> IngestionResult:
    if not ctx.is_demo:
        return IngestionResult(status=REJECTED, entity="leaderboard_score", code="demo_only",
                               message="leaderboard values can only be ingested as labelled demo fixtures")
    row = LeaderboardScore(
        session_id=record.session_id,
        candidate_name=record.candidate_name,
        candidate_handle=record.candidate_handle,
        candidate_avatar_url=record.candidate_avatar_url,
        target_role=record.target_role,
        repo_name=record.repo_name,
        code_health_score=record.code_health_score,
        voice_defense_score=record.voice_defense_score,
        composite_percentile=record.composite_percentile,
        rank_tier=record.rank_tier,
        status_tag="needs_human_review",
        is_demo=True,
        recorded_at=record.recorded_at or datetime.utcnow(),
    )
    db.add(row)
    await db.flush()
    return IngestionResult(status=CREATED, entity="leaderboard_score", entity_id=row.id, obj=row)


async def delete_demo_scores(db: AsyncSession) -> int:
    result = await db.execute(delete(LeaderboardScore).where(LeaderboardScore.is_demo.is_(True)))
    return int(result.rowcount or 0)
