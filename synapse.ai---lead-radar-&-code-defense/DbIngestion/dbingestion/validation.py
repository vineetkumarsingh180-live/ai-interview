"""
Input-shape validation for operator-provided records (types, required fields, sizes).

Business rules (platform list, deduplication, GitHub URL grammar) are NOT here: they belong to the
owning backend module and are enforced again there.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class StructuredInput(BaseModel):
    """Fields an operator typed by hand about a post (never inferred)."""

    model_config = ConfigDict(extra="forbid")

    role_title: str = Field(min_length=1, max_length=255)
    company_name: str = Field(min_length=1, max_length=255)
    company_stage: Optional[str] = Field(default=None, max_length=100)
    comp_min: Optional[float] = Field(default=None, ge=0)
    comp_max: Optional[float] = Field(default=None, ge=0)
    comp_currency: Optional[str] = Field(default=None, max_length=10)
    equity_note: Optional[str] = Field(default=None, max_length=120)
    tech_stack: List[str] = Field(default_factory=list, max_length=40)
    location_mode: Optional[str] = Field(default=None, pattern=r"^(Remote|Hybrid|Onsite)$")
    contact_anchor: Optional[str] = Field(default=None, max_length=255)
    # Showcase-only (the module refuses them outside labelled demo fixtures)
    match_score: Optional[float] = Field(default=None, ge=0, le=100)
    urgency_tier: Optional[str] = Field(default=None, max_length=50)
    summary: Optional[str] = Field(default=None, max_length=1000)


class ManualPostInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform: str = Field(min_length=1, max_length=50)
    text: str = Field(min_length=1, max_length=20000)
    external_id: Optional[str] = Field(default=None, max_length=255)
    author_handle: Optional[str] = Field(default=None, max_length=120)
    author_name: Optional[str] = Field(default=None, max_length=255)
    source_url: Optional[str] = Field(default=None, max_length=1024)
    posted_at: Optional[datetime] = None
    source_channel: str = Field(default="Manual import", max_length=120)
    note: Optional[str] = Field(default=None, max_length=1000)
    structured: Optional[StructuredInput] = None
    minutes_ago: Optional[int] = Field(default=None, ge=0, le=525600)   # showcase fixtures only: relative posted_at
    demo_classification: Optional[str] = Field(default=None, pattern=r"^seeking$")   # showcase fixtures only

    @field_validator("text")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be blank")
        return v


class GithubRepoInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repo_url: str = Field(min_length=1, max_length=512)
    candidate_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    target_role: Optional[str] = Field(default=None, max_length=150)


def describe(exc: ValidationError) -> str:
    """One readable line for a pydantic error."""
    parts = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"]) or "record"
        parts.append(f"{loc}: {err['msg']}")
    return "; ".join(parts)


class DemoCandidateInput(BaseModel):
    """One showcase candidate: repository + fixture analysis + fixture interview + fixture ranking."""

    model_config = ConfigDict(extra="forbid")

    candidate_name: str = Field(min_length=1, max_length=255)
    candidate_handle: str = Field(min_length=1, max_length=120)
    candidate_avatar_url: Optional[str] = Field(default=None, max_length=512)
    github_metadata: Optional[dict] = None
    submitted_minutes_ago: Optional[int] = Field(default=None, ge=0, le=525600)
    repo_url: str = Field(min_length=1, max_length=512)
    repo_name: str = Field(min_length=1, max_length=255)
    target_role: Optional[str] = Field(default=None, max_length=150)
    branch: Optional[str] = Field(default=None, max_length=100)
    commit_sha: Optional[str] = Field(default=None, max_length=64)
    language: Optional[str] = Field(default=None, max_length=80)
    benchmark: Optional[dict] = None
    evaluation: Optional[dict] = None
    interview: Optional[dict] = None
    leaderboard: Optional[dict] = None
