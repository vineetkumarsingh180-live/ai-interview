"""
Leaderboard module: persistence models.
Owns `leaderboard_scores`: one row per assessed interview session.

Every score is nullable: NULL means "not measured". `status_tag` is a review state, not a
recommendation.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database import Base


class LeaderboardScore(Base):
    __tablename__ = "leaderboard_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    # References voice_sessions.id (Voice Defense module) at database level only.
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("voice_sessions.id", ondelete="CASCADE"), unique=True
    )
    candidate_name: Mapped[str] = mapped_column(String(255), index=True)
    candidate_avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    candidate_handle: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    target_role: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    repo_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    code_health_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    voice_defense_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    composite_percentile: Mapped[Optional[float]] = mapped_column(Float, nullable=True, index=True)
    rank_tier: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)

    status_tag: Mapped[str] = mapped_column(String(50), default="needs_human_review")
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
