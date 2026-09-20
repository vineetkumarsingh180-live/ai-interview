"""
Pydantic v2 Schemas for Social Ingestion & AI Parser (Tab 1, Feature 1)
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

class RawPostCreate(BaseModel):
    platform: str = Field(..., example="twitter")
    external_id: str = Field(..., example="176293819283")
    author_handle: str = Field(..., example="@founder_steve")
    author_name: str = Field(..., example="Steve Chen")
    author_avatar_url: Optional[str] = None
    raw_content: str = Field(..., example="Looking for a Staff Distributed Systems Engineer in Rust. Comp $220k-$280k + 0.25% equity. Remote. DM me.")
    source_channel: str = Field(default="X Core API")

class RawPostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    platform: str
    external_id: str
    author_handle: str
    author_name: str
    author_avatar_url: Optional[str]
    raw_content: str
    source_channel: str
    ingested_at: datetime
    is_processed: bool

class ParsedLeadExtraction(BaseModel):
    """Structured extraction output from Gemini parsing pipeline"""
    is_hiring: bool = Field(..., description="True if author is offering a job, False if job seeker")
    role_title: str = Field(..., example="Staff Distributed Systems Engineer")
    company_name: str = Field(..., example="Aura Labs")
    company_stage: Optional[str] = Field(default="Series A", example="Series A")
    comp_min: Optional[float] = Field(default=None, example=220000.0)
    comp_max: Optional[float] = Field(default=None, example=280000.0)
    comp_currency: str = Field(default="USD", example="USD")
    equity_note: Optional[str] = Field(default=None, example="+ 0.25% Equity")
    tech_stack: List[str] = Field(default_factory=list, example=["Rust", "Raft", "PostgreSQL", "Kafka"])
    location_mode: str = Field(default="Remote", example="Remote")
    clearance_required: bool = False
    match_score: float = Field(default=95.0, example=98.4)
    urgency_tier: str = Field(default="Immediate", example="Immediate")
    contact_anchor: Optional[str] = Field(default=None, example="DM or steve@auralabs.io")
    extracted_summary: Optional[str] = None

class JobLeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    raw_post_id: UUID
    role_title: str
    company_name: str
    company_stage: Optional[str]
    comp_min: Optional[float]
    comp_max: Optional[float]
    comp_currency: str
    equity_note: Optional[str]
    tech_stack: List[str]
    location_mode: str
    clearance_required: bool
    is_hiring: bool
    match_score: float
    urgency_tier: str
    contact_anchor: Optional[str]
    enrichment_metadata: Dict[str, Any]
    created_at: datetime
    raw_post: Optional[RawPostResponse] = None

class IngestionStreamFilter(BaseModel):
    platform: Optional[str] = None
    min_match_score: Optional[float] = None
    location_mode: Optional[str] = None
    tech_stack_query: Optional[str] = None

class IngestionTelemetryResponse(BaseModel):
    total_scanned_24h: int
    qualified_leads_count: int
    seeking_discarded_count: int
    channels_monitored: List[str]
    avg_latency_ms: float
