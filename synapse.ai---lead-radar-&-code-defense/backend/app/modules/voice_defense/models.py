"""
Voice Defense module: persistence models.
Owns `voice_sessions`.

Sessions are never auto-scored: score columns are NULL until a human or a real evaluator sets
them, and the verdict column holds a review state (never a hiring decision).
"""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database import Base


class VoiceSession(Base):
    __tablename__ = "voice_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    # References candidate_repos.id (Code Verifier module) at database level only.
    repo_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_repos.id", ondelete="SET NULL"), nullable=True, index=True
    )
    candidate_name: Mapped[str] = mapped_column(String(255), index=True)
    session_status: Mapped[str] = mapped_column(String(50), default="active", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)

    technical_depth_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    clarity_articulation_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    architecture_defense_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    final_composite_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Review state, e.g. 'needs_human_review'. Never a hire/reject decision.
    defense_verdict: Mapped[str] = mapped_column(String(50), default="needs_human_review", index=True)

    transcript_turns: Mapped[List[dict]] = mapped_column(JSON, default=list)
    key_takeaways: Mapped[List[str]] = mapped_column(JSON, default=list)
