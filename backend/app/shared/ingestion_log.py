"""
Generic ingestion bookkeeping shared by DbIngestion and the API routes.

Infrastructure only: it records *that* a batch ran and what happened to each record. What a record
means (a post, a repository) is decided by the owning module, never here.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base

# Per-record outcomes
CREATED, UPDATED, DUPLICATE, REJECTED, FAILED = "created", "updated", "duplicate", "rejected", "failed"
OUTCOMES = (CREATED, UPDATED, DUPLICATE, REJECTED, FAILED)

# Run states
RUNNING, COMPLETED, COMPLETED_WITH_ERRORS, RUN_FAILED = "running", "completed", "completed_with_errors", "failed"


class IngestionRun(Base):
    """One execution of an ingestion workflow (audit trail and rollback handle)."""

    __tablename__ = "ingestion_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type: Mapped[str] = mapped_column(String(40), index=True)
    source_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # e.g. input file name
    status: Mapped[str] = mapped_column(String(30), default=RUNNING, index=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    triggered_by: Mapped[str] = mapped_column(String(80), default="cli")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    records_seen: Mapped[int] = mapped_column(Integer, default=0)
    records_created: Mapped[int] = mapped_column(Integer, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, default=0)
    records_duplicate: Mapped[int] = mapped_column(Integer, default=0)
    records_rejected: Mapped[int] = mapped_column(Integer, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list] = mapped_column(JSON, default=list)


@dataclass(frozen=True)
class IngestContext:
    """Passed to a module's ingestion function: where the record came from and whether it is demo."""

    source_type: str                       # e.g. manual_text, github_api, demo_fixture, api_manual
    run_id: Optional[uuid.UUID] = None
    is_demo: bool = False


@dataclass
class IngestionResult:
    status: str                            # one of OUTCOMES
    entity: str                            # what the record became, e.g. "raw_post", "repository"
    entity_id: Optional[uuid.UUID] = None
    code: Optional[str] = None             # machine-readable reason for non-created outcomes
    message: Optional[str] = None
    detail: Dict[str, Any] = field(default_factory=dict)
    obj: Any = field(default=None, repr=False)   # the stored ORM object, for in-process callers


async def start_run(
    db: AsyncSession, *, source_type: str, source_label: Optional[str], is_demo: bool, triggered_by: str = "cli"
) -> IngestionRun:
    run = IngestionRun(source_type=source_type, source_label=source_label, is_demo=is_demo, triggered_by=triggered_by)
    db.add(run)
    await db.commit()
    return run


async def finish_run(db: AsyncSession, run: IngestionRun, results: List[IngestionResult], *, aborted: Optional[str] = None) -> IngestionRun:
    counts = {k: sum(1 for r in results if r.status == k) for k in OUTCOMES}
    run.records_seen = len(results)
    run.records_created = counts[CREATED]
    run.records_updated = counts[UPDATED]
    run.records_duplicate = counts[DUPLICATE]
    run.records_rejected = counts[REJECTED]
    run.records_failed = counts[FAILED]
    run.errors = [
        {"index": i, "status": r.status, "code": r.code, "message": r.message}
        for i, r in enumerate(results)
        if r.status in (REJECTED, FAILED)
    ][:200]
    if aborted:
        run.status = RUN_FAILED
        run.errors = [{"index": None, "status": "aborted", "code": "run_aborted", "message": aborted}] + run.errors
    elif counts[REJECTED] or counts[FAILED]:
        run.status = COMPLETED_WITH_ERRORS
    else:
        run.status = COMPLETED
    run.finished_at = datetime.utcnow()
    await db.commit()
    return run
