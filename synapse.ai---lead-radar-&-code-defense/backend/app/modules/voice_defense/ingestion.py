"""
Voice Defense: public ingestion interface used by DbIngestion (labelled showcase sessions only).

No real interview is ever created here: rows are flagged `is_demo`, and the score columns hold
fixture values that are shown with a demo label. Flushes but does not commit.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.ingestion_log import CREATED, REJECTED, IngestContext, IngestionResult

from .models import VoiceSession


@dataclass
class DemoSession:
    candidate_name: str
    repo_id: Optional[uuid.UUID] = None
    technical_depth_score: Optional[float] = None
    clarity_articulation_score: Optional[float] = None
    architecture_defense_score: Optional[float] = None
    final_composite_score: Optional[float] = None
    duration_seconds: int = 0
    completed_at: Optional[datetime] = None
    transcript_turns: List[dict] = field(default_factory=list)
    key_takeaways: List[str] = field(default_factory=list)


async def ingest_demo_session(db: AsyncSession, record: DemoSession, ctx: IngestContext) -> IngestionResult:
    if not ctx.is_demo:
        return IngestionResult(status=REJECTED, entity="voice_session", code="demo_only",
                               message="interview sessions can only be ingested as labelled demo fixtures")
    session = VoiceSession(
        repo_id=record.repo_id,
        candidate_name=record.candidate_name,
        session_status="completed",
        completed_at=record.completed_at or datetime.utcnow(),
        duration_seconds=record.duration_seconds,
        technical_depth_score=record.technical_depth_score,
        clarity_articulation_score=record.clarity_articulation_score,
        architecture_defense_score=record.architecture_defense_score,
        final_composite_score=record.final_composite_score,
        defense_verdict="needs_human_review",
        transcript_turns=list(record.transcript_turns),
        key_takeaways=list(record.key_takeaways),
        is_demo=True,
    )
    db.add(session)
    await db.flush()
    return IngestionResult(status=CREATED, entity="voice_session", entity_id=session.id, obj=session)


async def delete_demo_sessions(db: AsyncSession) -> int:
    """Delete labelled demo sessions (their leaderboard rows go with them). Never anything else."""
    result = await db.execute(delete(VoiceSession).where(VoiceSession.is_demo.is_(True)))
    return int(result.rowcount or 0)
