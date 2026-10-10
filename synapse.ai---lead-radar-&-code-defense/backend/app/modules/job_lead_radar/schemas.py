"""
Job Lead Radar module: request/response contract (camelCase on the wire).
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import Field

from app.shared.schemas import ApiModel

Platform = Literal["twitter", "linkedin", "reddit", "telegram"]
Tone = Literal["Direct Technical", "Executive", "Casual Founder"]


class RawPostCreate(ApiModel):
    platform: Platform
    external_id: Optional[str] = Field(default=None, max_length=255, description="Source post id; generated when omitted")
    author_handle: Optional[str] = Field(default=None, max_length=120)
    author_name: Optional[str] = Field(default=None, max_length=255)
    author_avatar_url: Optional[str] = Field(default=None, max_length=512)
    raw_content: str = Field(..., min_length=1, max_length=20000)
    source_channel: str = Field(default="Manual import", max_length=120)


class RawPostResponse(ApiModel):
    id: UUID
    platform: str
    external_id: str
    author_handle: str
    author_name: str
    author_avatar_url: Optional[str] = None
    raw_content: str
    source_channel: str
    ingested_at: datetime
    is_processed: bool


class ParsedLeadExtraction(ApiModel):
    """Structured output of the AI parsing step. Fields the post does not state stay null."""

    is_hiring: bool = Field(..., description="True if the author is offering a job, False if a job seeker")
    role_title: Optional[str] = None
    company_name: Optional[str] = None
    company_stage: Optional[str] = None
    comp_min: Optional[float] = None
    comp_max: Optional[float] = None
    comp_currency: Optional[str] = None
    equity_note: Optional[str] = None
    tech_stack: List[str] = Field(default_factory=list)
    location_mode: Optional[str] = None
    clearance_required: Optional[bool] = None
    urgency_tier: Optional[str] = None
    contact_anchor: Optional[str] = None
    extracted_summary: Optional[str] = None


class JobLeadResponse(ApiModel):
    id: UUID
    raw_post_id: UUID
    role_title: str
    company_name: str
    company_stage: Optional[str] = None
    comp_min: Optional[float] = None
    comp_max: Optional[float] = None
    comp_currency: Optional[str] = None
    equity_note: Optional[str] = None
    tech_stack: List[str]
    location_mode: Optional[str] = None
    clearance_required: Optional[bool] = None
    is_hiring: bool
    match_score: Optional[float] = Field(default=None, description="Null: no matching model exists yet")
    urgency_tier: Optional[str] = None
    contact_anchor: Optional[str] = None
    enrichment_metadata: Dict[str, Any] = Field(default_factory=dict)
    is_demo: bool = Field(default=False, description="True for clearly labelled development fixtures")
    created_at: datetime
    raw_post: Optional[RawPostResponse] = None


class IngestOutcome(ApiModel):
    """Result of submitting a post. The raw post is always stored; `status` says what happened next."""

    status: Literal["created", "discarded", "awaiting_analysis", "needs_review"]
    raw_post_id: UUID
    reason: Optional[str] = None
    lead: Optional[JobLeadResponse] = None


class IngestionTelemetryResponse(ApiModel):
    # explicit alias: the generator would produce "totalScanned24H"
    total_scanned_24h: int = Field(alias="totalScanned24h")
    qualified_leads_count: int
    seeking_discarded_count: int
    awaiting_analysis_count: int
    channels_monitored: List[str]
    avg_latency_ms: Optional[float] = Field(default=None, description="Null: latency is not measured")


class OutreachDraftRequest(ApiModel):
    lead_id: UUID
    tone: Tone = "Direct Technical"
    candidate_profile_context: Optional[str] = Field(default=None, max_length=4000)


class OutreachDraftResponse(ApiModel):
    id: UUID
    lead_id: UUID
    tone: str
    pitch_subject: str
    generated_pitch: str
    candidate_profile_context: Optional[str] = None
    status: str
    model_version: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    created_at: datetime


class LeadSearchQuery(ApiModel):
    query_text: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(default=10, ge=1, le=50)


class LeadSearchHit(ApiModel):
    lead: JobLeadResponse
    match_type: Literal["keyword"] = "keyword"
    similarity_score: Optional[float] = Field(default=None, description="Always null until embeddings exist")
