"""
Job Lead Radar module: persistence models.
Owns the tables `raw_posts`, `job_leads`, `lead_embeddings`, `outreach_drafts`.

Nothing here has fabricated defaults: a value the post/AI did not provide is NULL.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database import Base

from .config import lead_radar_settings


class RawPost(Base):
    __tablename__ = "raw_posts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    platform: Mapped[str] = mapped_column(String(50), index=True)  # 'twitter', 'linkedin', 'reddit', 'telegram'
    external_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    author_handle: Mapped[str] = mapped_column(String(120), index=True)
    author_name: Mapped[str] = mapped_column(String(255))
    author_avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    raw_content: Mapped[str] = mapped_column(Text)
    source_channel: Mapped[str] = mapped_column(String(120))
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    # True once an analysis decision was made (hiring lead or discarded job seeker).
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    # 'hiring' | 'seeking' | NULL (not classified yet: awaiting analysis)
    classification: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)

    parsed_lead: Mapped[Optional["JobLead"]] = relationship(
        "JobLead", back_populates="raw_post", uselist=False, cascade="all, delete-orphan"
    )


class JobLead(Base):
    __tablename__ = "job_leads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    raw_post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("raw_posts.id", ondelete="CASCADE"), unique=True
    )
    role_title: Mapped[str] = mapped_column(String(255), index=True)
    company_name: Mapped[str] = mapped_column(String(255), index=True)
    company_stage: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    comp_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    comp_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    comp_currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    equity_note: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    tech_stack: Mapped[List[str]] = mapped_column(JSON, default=list)
    location_mode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    clearance_required: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    is_hiring: Mapped[bool] = mapped_column(Boolean, index=True)
    match_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # NULL: no matching model yet
    urgency_tier: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    contact_anchor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    enrichment_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    raw_post: Mapped["RawPost"] = relationship("RawPost", back_populates="parsed_lead")
    outreach_drafts: Mapped[List["OutreachDraft"]] = relationship(
        "OutreachDraft", back_populates="lead", cascade="all, delete-orphan"
    )


class LeadEmbedding(Base):
    __tablename__ = "lead_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_leads.id", ondelete="CASCADE"), unique=True, index=True
    )
    embedding: Mapped[Optional[List[float]]] = mapped_column(
        Vector(lead_radar_settings.EMBEDDING_DIMENSIONS), nullable=True
    )
    text_content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class OutreachDraft(Base):
    __tablename__ = "outreach_drafts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_leads.id", ondelete="CASCADE"), index=True
    )
    tone: Mapped[str] = mapped_column(String(50))
    pitch_subject: Mapped[str] = mapped_column(String(255))
    generated_pitch: Mapped[str] = mapped_column(Text)
    candidate_profile_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # 'draft', 'copied', 'sent'
    model_version: Mapped[str] = mapped_column(String(80))          # the model that really produced it
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    lead: Mapped["JobLead"] = relationship("JobLead", back_populates="outreach_drafts")
