"""
Code Verifier module: persistence models.
Owns `candidate_repos`, `benchmark_suites`, `code_evaluation_results`.

A submission starts as `awaiting_analysis` with no benchmark or evaluation rows. Those rows are
created only by a real analysis; every measured value is nullable (NULL = not measured).
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database import Base


class CandidateRepo(Base):
    __tablename__ = "candidate_repos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    candidate_name: Mapped[str] = mapped_column(String(255), index=True)
    candidate_github_handle: Mapped[str] = mapped_column(String(120), index=True)
    candidate_avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    repo_url: Mapped[str] = mapped_column(String(512), index=True)
    repo_name: Mapped[str] = mapped_column(String(255))
    target_role: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    branch: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    commit_sha: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    # awaiting_analysis | analyzing | analyzed | failed
    status: Mapped[str] = mapped_column(String(50), default="awaiting_analysis", index=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", index=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    benchmark: Mapped[Optional["BenchmarkSuite"]] = relationship(
        "BenchmarkSuite", back_populates="repo", uselist=False, cascade="all, delete-orphan"
    )
    evaluation: Mapped[Optional["CodeEvaluationResult"]] = relationship(
        "CodeEvaluationResult", back_populates="repo", uselist=False, cascade="all, delete-orphan"
    )


class BenchmarkSuite(Base):
    __tablename__ = "benchmark_suites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_repos.id", ondelete="CASCADE"), unique=True
    )
    test_coverage_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cyclomatic_complexity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sec_vulnerabilities_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    execution_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    suite_log_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    repo: Mapped["CandidateRepo"] = relationship("CandidateRepo", back_populates="benchmark")


class CodeEvaluationResult(Base):
    __tablename__ = "code_evaluation_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_repos.id", ondelete="CASCADE"), unique=True
    )
    composite_health_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    architecture_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    concurrency_safety_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    maintainability_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    summary_verdict: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rubric_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    flagged_anomalies: Mapped[list] = mapped_column(JSON, default=list)
    recommended_defense_topics: Mapped[list] = mapped_column(JSON, default=list)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    repo: Mapped["CandidateRepo"] = relationship("CandidateRepo", back_populates="evaluation")
