"""
PostgreSQL ORM Models for Semantic Search & Cold Outreach (Tab 1, Feature 2)
Includes pgvector Vector(768) embeddings for dense similarity search.
"""

import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String,
    Text,
    Float,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from app.core.database import Base
from app.core.config import settings

class LeadEmbedding(Base):
    __tablename__ = "lead_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_leads.id", ondelete="CASCADE"), unique=True, index=True
    )
    # Dense vector representation from Gemini embedding model (768 dimensions)
    embedding: Mapped[Optional[List[float]]] = mapped_column(
        Vector(settings.EMBEDDING_DIMENSIONS), nullable=True
    )
    text_content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class OutreachDraft(Base):
    __tablename__ = "outreach_drafts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_leads.id", ondelete="CASCADE"), index=True
    )
    tone: Mapped[str] = mapped_column(String(50), default="Direct Technical")  # 'Direct Technical', 'Executive', 'Casual Founder'
    pitch_subject: Mapped[str] = mapped_column(String(255))
    generated_pitch: Mapped[str] = mapped_column(Text)
    candidate_profile_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # 'draft', 'copied', 'sent'
    model_version: Mapped[str] = mapped_column(String(80), default="gemini-3.8-flash")
    prompt_tokens: Mapped[int] = mapped_column(default=0)
    completion_tokens: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # Relationship to lead
    lead: Mapped["JobLead"] = relationship("JobLead", back_populates="outreach_drafts")
