"""
Pydantic v2 Schemas for Semantic Search & Cold Outreach (Tab 1, Feature 2)
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from app.tab1_leads.feature1_ingestion.schemas import JobLeadResponse

class OutreachDraftRequest(BaseModel):
    lead_id: UUID = Field(..., description="ID of the JobLead to target")
    tone: str = Field(default="Direct Technical", example="Direct Technical")  # 'Direct Technical', 'Executive', 'Casual Founder'
    candidate_profile_context: Optional[str] = Field(
        default=None,
        example="Principal engineer with 9 yrs experience building distributed consensus engines and raft clusters in Rust."
    )

class OutreachDraftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID
    tone: str
    pitch_subject: str
    generated_pitch: str
    candidate_profile_context: Optional[str]
    status: str
    model_version: str
    prompt_tokens: int
    completion_tokens: int
    created_at: datetime

class SemanticLeadSearchQuery(BaseModel):
    query_text: str = Field(..., example="Rust distributed systems raft consensus low latency")
    top_k: int = Field(default=10, ge=1, le=50)
    min_similarity: float = Field(default=0.70, ge=0.0, le=1.0)

class SemanticSearchHit(BaseModel):
    lead: JobLeadResponse
    similarity_score: float
