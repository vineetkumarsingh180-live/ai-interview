"""
Pydantic v2 Schemas for Code Verifier & LLM Grader (Tab 2, Feature 1)
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

class RepoSubmissionRequest(BaseModel):
    candidate_name: str = Field(..., example="Alex Vance")
    candidate_github_handle: str = Field(..., example="alexvance")
    candidate_avatar_url: Optional[str] = Field(default=None)
    repo_url: str = Field(..., example="https://github.com/alexvance/distributed-raft-kv")
    target_role: str = Field(default="Staff Distributed Systems Engineer")
    branch: str = Field(default="main")

class BenchmarkSuiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    repo_id: UUID
    test_coverage_pct: float
    cyclomatic_complexity: float
    sec_vulnerabilities_count: int
    ai_generated_probability: float
    execution_time_ms: int
    suite_log_output: str
    created_at: datetime

class AnomalyFlag(BaseModel):
    type: str
    severity: str  # 'info', 'warning', 'critical'
    description: str
    line_reference: Optional[str] = None

class CodeEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    repo_id: UUID
    composite_health_score: float
    architecture_score: float
    concurrency_safety_score: float
    maintainability_score: float
    anti_cheat_confidence: float
    summary_verdict: str
    rubric_breakdown: Dict[str, Any]
    flagged_anomalies: List[Dict[str, Any]]
    recommended_defense_topics: List[str]
    evaluated_at: datetime

class CandidateRepoDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    candidate_name: str
    candidate_github_handle: str
    candidate_avatar_url: Optional[str]
    repo_url: str
    repo_name: str
    target_role: str
    branch: str
    commit_sha: str
    language: str
    status: str
    submitted_at: datetime
    benchmark: Optional[BenchmarkSuiteResponse] = None
    evaluation: Optional[CodeEvaluationResponse] = None
