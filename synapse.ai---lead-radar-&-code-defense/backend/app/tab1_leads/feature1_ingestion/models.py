"""
PostgreSQL ORM Models for Social Ingestion & AI Parser (Tab 1, Feature 1)
"""

import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    String,
    Text,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from app.core.database import Base

class RawPost(Base):
    __tablename__ = "raw_posts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    platform: Mapped[str] = mapped_column(String(50), index=True)  # 'twitter', 'linkedin', 'reddit', 'telegram'
    external_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    author_handle: Mapped[str] = mapped_column(String(120), index=True)
    author_name: Mapped[str] = mapped_column(String(255))
    author_avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    raw_content: Mapped[str] = mapped_column(Text)
    source_channel: Mapped[str] = mapped_column(String(120))  # e.g., 'X Core API', 'r/forhire'
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Relationship to parsed structured lead
    parsed_lead: Mapped[Optional["JobLead"]] = relationship(
        "JobLead", back_populates="raw_post", uselist=False, cascade="all, delete-orphan"
    )

class JobLead(Base):
    __tablename__ = "job_leads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    raw_post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("raw_posts.id", ondelete="CASCADE"), unique=True
    )
    role_title: Mapped[str] = mapped_column(String(255), index=True)
    company_name: Mapped[str] = mapped_column(String(255), index=True)
    company_stage: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 'Tier-1 VC Backed', 'Seed'
    
    # Financial compensation breakdown
    comp_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    comp_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    comp_currency: Mapped[str] = mapped_column(String(10), default="USD")
    equity_note: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)  # '+ 0.25%', '+ Tokens'
    
    # Skills & tech tags
    tech_stack: Mapped[List[str]] = mapped_column(JSON, default=list)  # stored as JSON or ARRAY
    location_mode: Mapped[str] = mapped_column(String(50), default="Remote")  # 'Remote', 'Hybrid', 'Onsite'
    clearance_required: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # AI Filtering & Classification
    is_hiring: Mapped[bool] = mapped_column(Boolean, default=True, index=True)  # False if "Seeking Job"
    match_score: Mapped[float] = mapped_column(Float, default=90.0)  # e.g., 99.4%
    urgency_tier: Mapped[str] = mapped_column(String(50), default="Normal")  # 'Immediate', 'High', 'Normal'
    contact_anchor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Enrichment and metadata (sentiment, AST keywords, extracted contacts)
    enrichment_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    raw_post: Mapped["RawPost"] = relationship("RawPost", back_populates="parsed_lead")
    outreach_drafts: Mapped[List["OutreachDraft"]] = relationship(
        "OutreachDraft", back_populates="lead", cascade="all, delete-orphan"
    )
