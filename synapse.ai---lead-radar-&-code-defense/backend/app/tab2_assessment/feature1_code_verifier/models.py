"""
PostgreSQL ORM Models for Code Verifier & LLM Grader (Tab 2, Feature 1)
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

class CandidateRepo(Base):
    __tablename__ = "candidate_repos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    candidate_name: Mapped[str] = mapped_column(String(255), index=True)
    candidate_github_handle: Mapped[str] = mapped_column(String(120), index=True)
    candidate_avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    repo_url: Mapped[str] = mapped_column(String(512), index=True)
    repo_name: Mapped[str] = mapped_column(String(255))
    target_role: Mapped[str] = mapped_column(String(150), default="Staff Distributed Systems Engineer")
    branch: Mapped[str] = mapped_column(String(100), default="main")
    commit_sha: Mapped[str] = mapped_column(String(64), default="HEAD")
    language: Mapped[str] = mapped_column(String(80), default="Rust / Go")
    status: Mapped[str] = mapped_column(String(50), default="analyzed", index=True)  # 'pending', 'benchmarking', 'analyzed', 'flagged'
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    benchmark: Mapped[Optional["BenchmarkSuite"]] = relationship(
        "BenchmarkSuite", back_populates="repo", uselist=False, cascade="all, delete-orphan"
    )
    evaluation: Mapped[Optional["CodeEvaluationResult"]] = relationship(
        "CodeEvaluationResult", back_populates="repo", uselist=False, cascade="all, delete-orphan"
    )
    voice_sessions: Mapped[List["VoiceSession"]] = relationship(
        "VoiceSession", back_populates="repo", cascade="all, delete-orphan"
    )

class BenchmarkSuite(Base):
    __tablename__ = "benchmark_suites"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_repos.id", ondelete="CASCADE"), unique=True
    )
    test_coverage_pct: Mapped[float] = mapped_column(Float, default=94.2)
    cyclomatic_complexity: Mapped[float] = mapped_column(Float, default=4.1)
    sec_vulnerabilities_count: Mapped[int] = mapped_column(Integer, default=0)
    ai_generated_probability: Mapped[float] = mapped_column(Float, default=12.4)  # AST anomaly detection %
    execution_time_ms: Mapped[int] = mapped_column(Integer, default=420)
    suite_log_output: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship
    repo: Mapped["CandidateRepo"] = relationship("CandidateRepo", back_populates="benchmark")

class CodeEvaluationResult(Base):
    __tablename__ = "code_evaluation_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_repos.id", ondelete="CASCADE"), unique=True
    )
    composite_health_score: Mapped[float] = mapped_column(Float, default=94.0)  # e.g., 94 / 100
    architecture_score: Mapped[float] = mapped_column(Float, default=92.0)
    concurrency_safety_score: Mapped[float] = mapped_column(Float, default=96.0)
    maintainability_score: Mapped[float] = mapped_column(Float, default=94.0)
    anti_cheat_confidence: Mapped[float] = mapped_column(Float, default=98.1)
    
    summary_verdict: Mapped[str] = mapped_column(Text)
    rubric_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    flagged_anomalies: Mapped[List[dict]] = mapped_column(JSON, default=list)
    recommended_defense_topics: Mapped[List[str]] = mapped_column(JSON, default=list)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship
    repo: Mapped["CandidateRepo"] = relationship("CandidateRepo", back_populates="evaluation")
