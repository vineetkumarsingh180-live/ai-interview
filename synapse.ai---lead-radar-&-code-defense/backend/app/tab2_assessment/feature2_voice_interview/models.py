"""
PostgreSQL ORM Models for AI Voice Defense & Leaderboard (Tab 2, Feature 2)
"""

import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String,
    Text,
    Float,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class VoiceSession(Base):
    __tablename__ = "voice_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    repo_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_repos.id", ondelete="SET NULL"), nullable=True, index=True
    )
    candidate_name: Mapped[str] = mapped_column(String(255), index=True)
    session_status: Mapped[str] = mapped_column(String(50), default="active", index=True)  # 'active', 'completed', 'terminated'
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    
    # Quantitative AI Defense Metrics (0 - 100)
    technical_depth_score: Mapped[float] = mapped_column(Float, default=88.5)
    clarity_articulation_score: Mapped[float] = mapped_column(Float, default=92.0)
    architecture_defense_score: Mapped[float] = mapped_column(Float, default=90.0)
    final_composite_score: Mapped[float] = mapped_column(Float, default=90.1)
    
    # Verdict: 'AUTO_HIRE', 'HUMAN_REVIEW', 'FLAGGED_CHEAT', 'REJECT'
    defense_verdict: Mapped[str] = mapped_column(String(50), default="HUMAN_REVIEW", index=True)
    
    # Full chronological dialogue stream with timestamps and speech segments
    transcript_turns: Mapped[List[dict]] = mapped_column(JSON, default=list)
    key_takeaways: Mapped[List[str]] = mapped_column(JSON, default=list)

    # Relationship to candidate repo and leaderboard
    repo: Mapped[Optional["CandidateRepo"]] = relationship("CandidateRepo", back_populates="voice_sessions")
    leaderboard_entry: Mapped[Optional["LeaderboardScore"]] = relationship(
        "LeaderboardScore", back_populates="session", uselist=False, cascade="all, delete-orphan"
    )

class LeaderboardScore(Base):
    __tablename__ = "leaderboard_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("voice_sessions.id", ondelete="CASCADE"), unique=True
    )
    candidate_name: Mapped[str] = mapped_column(String(255), index=True)
    candidate_avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    candidate_handle: Mapped[str] = mapped_column(String(120), index=True)
    target_role: Mapped[str] = mapped_column(String(150), default="Staff Distributed Systems Engineer")
    repo_name: Mapped[str] = mapped_column(String(255))
    
    # Scores
    code_health_score: Mapped[float] = mapped_column(Float)
    voice_defense_score: Mapped[float] = mapped_column(Float)
    composite_percentile: Mapped[float] = mapped_column(Float, index=True)  # Top 1% = 99.0
    rank_tier: Mapped[str] = mapped_column(String(50), default="Top 1%", index=True)
    
    status_tag: Mapped[str] = mapped_column(String(50), default="Auto-Hire Candidate")
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # Relationship
    session: Mapped["VoiceSession"] = relationship("VoiceSession", back_populates="leaderboard_entry")
