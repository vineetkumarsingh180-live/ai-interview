"""
Code Verifier module: request/response contract (camelCase on the wire).
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field, field_validator

from app.shared.schemas import ApiModel

_GITHUB_REPO_URL = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?$")


class RepoSubmissionRequest(ApiModel):
    candidate_name: str = Field(..., min_length=1, max_length=255)
    candidate_github_handle: str = Field(..., min_length=1, max_length=120)
    candidate_avatar_url: Optional[str] = Field(default=None, max_length=512)
    repo_url: str = Field(..., max_length=512, description="https://github.com/<owner>/<repo>")
    target_role: Optional[str] = Field(default=None, max_length=150)
    branch: Optional[str] = Field(default=None, max_length=100, description="Null = repository default branch")

    @field_validator("repo_url")
    @classmethod
    def _github_url(cls, v: str) -> str:
        if not _GITHUB_REPO_URL.match(v.strip()):
            raise ValueError("must look like https://github.com/<owner>/<repo>")
        return v.strip().rstrip("/")


class BenchmarkSuiteResponse(ApiModel):
    """Measured benchmark facts. Any value that was not measured is null."""

    id: UUID
    repo_id: UUID
    test_coverage_pct: Optional[float] = None
    cyclomatic_complexity: Optional[float] = None
    sec_vulnerabilities_count: Optional[int] = None
    execution_time_ms: Optional[int] = None
    suite_log_output: Optional[str] = None
    created_at: datetime


class CodeEvaluationResponse(ApiModel):
    """A written/scored evaluation. Scores are optional model/analyst opinions, never verdicts."""

    id: UUID
    repo_id: UUID
    composite_health_score: Optional[float] = None
    architecture_score: Optional[float] = None
    concurrency_safety_score: Optional[float] = None
    maintainability_score: Optional[float] = None
    summary_verdict: Optional[str] = None
    rubric_breakdown: Dict[str, Any] = Field(default_factory=dict)
    flagged_anomalies: List[Dict[str, Any]] = Field(default_factory=list)
    recommended_defense_topics: List[str] = Field(default_factory=list)
    evaluated_at: datetime


class CandidateRepoDetailResponse(ApiModel):
    id: UUID
    candidate_name: str
    candidate_github_handle: str
    candidate_avatar_url: Optional[str] = None
    repo_url: str
    repo_name: str
    target_role: Optional[str] = None
    branch: Optional[str] = None
    commit_sha: Optional[str] = None
    language: Optional[str] = None
    status: str = Field(description="awaiting_analysis | analyzing | analyzed | failed")
    is_demo: bool = Field(default=False, description="True for clearly labelled development fixtures")
    submitted_at: datetime
    benchmark: Optional[BenchmarkSuiteResponse] = None
    evaluation: Optional[CodeEvaluationResponse] = None
