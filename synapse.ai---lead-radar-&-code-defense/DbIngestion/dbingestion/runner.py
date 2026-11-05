"""
Run orchestration: one run = one audit row + one transaction per record.

* Each record is persisted atomically; a failing record rolls back alone and is reported with a
  structured code, the rest continue.
* `dry_run=True` executes the real module logic (so duplicates and rejections are exact) and then
  rolls back; nothing is written and no run row is created.
* Persistence happens only through each backend module's public ingestion interface.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Awaitable, Callable, List, Optional, Sequence

from app.modules import code_verifier, job_lead_radar, leaderboard, voice_defense
from app.shared.database import AsyncSessionLocal
from app.shared.github import GitHubClient, GitHubError
from app.shared.ingestion_log import (
    CREATED,
    FAILED,
    REJECTED,
    IngestContext,
    IngestionResult,
    IngestionRun,
    finish_run,
    start_run,
)

from .sources import SourceItem
from .validation import DemoCandidateInput, GithubRepoInput, ManualPostInput

SessionFactory = Callable[[], object]


class IngestionAborted(Exception):
    """The run could not start (e.g. the database is unreachable). Nothing was written."""


@dataclass
class RunSummary:
    run_id: Optional[str]
    source_type: str
    dry_run: bool
    results: List[IngestionResult] = field(default_factory=list)
    status: str = "completed"

    def counts(self) -> dict:
        out = {k: 0 for k in ("created", "updated", "duplicate", "rejected", "failed")}
        for r in self.results:
            out[r.status] += 1
        return out


def _to_post_record(v: ManualPostInput) -> job_lead_radar.PostRecord:
    s = v.structured
    return job_lead_radar.PostRecord(
        platform=v.platform,
        raw_content=v.text,
        external_id=v.external_id,
        author_handle=v.author_handle,
        author_name=v.author_name,
        source_url=v.source_url,
        posted_at=v.posted_at,
        source_channel=v.source_channel,
        note=v.note,
        demo_classification=v.demo_classification,
        structured=job_lead_radar.StructuredLead(**s.model_dump()) if s else None,
    )


async def _persist(
    factory: SessionFactory,
    work: Callable[[object], Awaitable[IngestionResult]],
    *,
    dry_run: bool,
) -> IngestionResult:
    """One record, one transaction. Any exception becomes a structured `failed` result."""
    try:
        async with factory() as db:          # type: ignore[attr-defined]
            try:
                result = await work(db)
            except Exception:
                await db.rollback()
                raise
            # Only a write that actually changed something is committed; everything else is rolled back.
            if dry_run or result.status not in ("created", "updated"):
                await db.rollback()
            else:
                await db.commit()
        return result
    except Exception as exc:  # database down, constraint bug, ...
        return IngestionResult(status=FAILED, entity="record", code="persistence_error",
                               message=f"{type(exc).__name__}: {str(exc).splitlines()[0][:160]}")


async def _open_run(factory: SessionFactory, *, source_type: str, label: Optional[str], is_demo: bool) -> IngestionRun:
    try:
        async with factory() as db:          # type: ignore[attr-defined]
            run = await start_run(db, source_type=source_type, source_label=label, is_demo=is_demo)
            db.expunge(run)
            return run
    except Exception as exc:
        raise IngestionAborted(f"could not start the ingestion run: {type(exc).__name__}: {str(exc).splitlines()[0][:160]}") from exc


async def _close_run(factory: SessionFactory, run: IngestionRun, results: Sequence[IngestionResult]) -> None:
    async with factory() as db:              # type: ignore[attr-defined]
        merged = await db.merge(run)
        await finish_run(db, merged, list(results))


async def run_posts(
    items: Sequence[SourceItem[ManualPostInput]],
    *,
    source_type: str = "manual_text",
    label: Optional[str] = None,
    is_demo: bool = False,
    dry_run: bool = False,
    session_factory: SessionFactory = AsyncSessionLocal,
) -> RunSummary:
    run = None if dry_run else await _open_run(session_factory, source_type=source_type, label=label, is_demo=is_demo)
    ctx = IngestContext(source_type=source_type, run_id=run.id if run else None, is_demo=is_demo)
    summary = RunSummary(run_id=str(run.id) if run else None, source_type=source_type, dry_run=dry_run)

    for item in items:
        if item.value is None:
            summary.results.append(IngestionResult(status=REJECTED, entity="raw_post", code=item.error_code, message=item.error_message))
            continue
        record = _to_post_record(item.value)
        summary.results.append(
            await _persist(session_factory, lambda db, r=record: job_lead_radar.ingest_post_record(db, r, ctx), dry_run=dry_run)
        )

    if run is not None:
        await _close_run(session_factory, run, summary.results)
    return summary


async def run_github(
    items: Sequence[SourceItem[GithubRepoInput]],
    *,
    client: Optional[GitHubClient] = None,
    label: Optional[str] = None,
    dry_run: bool = False,
    session_factory: SessionFactory = AsyncSessionLocal,
) -> RunSummary:
    client = client or GitHubClient()
    source_type = "github_api"
    run = None if dry_run else await _open_run(session_factory, source_type=source_type, label=label, is_demo=False)
    ctx = IngestContext(source_type=source_type, run_id=run.id if run else None, is_demo=False)
    summary = RunSummary(run_id=str(run.id) if run else None, source_type=source_type, dry_run=dry_run)

    for item in items:
        if item.value is None:
            summary.results.append(IngestionResult(status=REJECTED, entity="repository", code=item.error_code, message=item.error_message))
            continue
        v = item.value
        parsed = code_verifier.parse_github_url(v.repo_url)
        if parsed is None:
            summary.results.append(code_verifier.reject_repo_url(v.repo_url))
            continue
        try:
            snapshot = await client.fetch_repository(*parsed)
        except GitHubError as exc:
            # A missing/private repository is bad input; rate limits and outages are transient failures.
            status = REJECTED if exc.code in ("not_found", "forbidden") else FAILED
            summary.results.append(IngestionResult(status=status, entity="repository", code=f"github_{exc.code}", message=exc.message))
            continue
        summary.results.append(
            await _persist(
                session_factory,
                lambda db, s=snapshot, v=v: code_verifier.register_github_repository(
                    db, s, ctx, candidate_name=v.candidate_name, target_role=v.target_role),
                dry_run=dry_run,
            )
        )

    if run is not None:
        await _close_run(session_factory, run, summary.results)
    return summary


async def run_demo_candidates(
    items: Sequence[SourceItem[DemoCandidateInput]],
    *,
    dry_run: bool = False,
    session_factory: SessionFactory = AsyncSessionLocal,
) -> RunSummary:
    """
    Labelled showcase candidates. Each one is ONE transaction: repository (+ fixture benchmark and
    evaluation), fixture interview session, fixture leaderboard row. Every value is flagged demo.
    """
    run = None if dry_run else await _open_run(session_factory, source_type="demo_fixture", label="showcase.json", is_demo=True)
    ctx = IngestContext(source_type="demo_fixture", run_id=run.id if run else None, is_demo=True)
    summary = RunSummary(run_id=str(run.id) if run else None, source_type="demo_fixture", dry_run=dry_run)

    async def _one(db, v: DemoCandidateInput) -> IngestionResult:
        record = code_verifier.DemoAnalysis(
            repo_url=v.repo_url, candidate_name=v.candidate_name, candidate_handle=v.candidate_handle,
            repo_name=v.repo_name, target_role=v.target_role, branch=v.branch, avatar_url=v.candidate_avatar_url, github_metadata=v.github_metadata,
            submitted_at=(datetime.utcnow() - timedelta(minutes=v.submitted_minutes_ago)) if v.submitted_minutes_ago is not None else None, commit_sha=v.commit_sha,
            language=v.language, benchmark=v.benchmark, evaluation=v.evaluation,
        )
        repo = await code_verifier.register_demo_analysed_repository(db, record, ctx)
        if repo.status != CREATED:
            return repo
        iv = v.interview or {}
        session = await voice_defense.ingest_demo_session(
            db, voice_defense.DemoSession(candidate_name=v.candidate_name, repo_id=repo.entity_id, **iv), ctx)
        lb = dict(v.leaderboard) if v.leaderboard is not None else None
        if lb is not None:
            minutes = lb.pop("minutes_ago", None)
            if minutes is not None:
                lb["recorded_at"] = datetime.utcnow() - timedelta(minutes=minutes)
            await leaderboard.ingest_demo_score(
                db,
                leaderboard.DemoScore(**{
                    "session_id": session.entity_id, "candidate_name": v.candidate_name, "candidate_handle": v.candidate_handle,
                    "target_role": v.target_role, "repo_name": v.repo_name, "candidate_avatar_url": v.candidate_avatar_url, **lb}),
                ctx,
            )
        return repo

    for item in items:
        if item.value is None:
            summary.results.append(IngestionResult(status=REJECTED, entity="repository", code=item.error_code, message=item.error_message))
            continue
        summary.results.append(await _persist(session_factory, lambda db, v=item.value: _one(db, v), dry_run=dry_run))

    if run is not None:
        await _close_run(session_factory, run, summary.results)
    return summary


async def rollback_run(run_id, *, session_factory: SessionFactory = AsyncSessionLocal) -> dict:
    """Delete exactly the rows a run created (through each module's interface)."""
    async with session_factory() as db:      # type: ignore[attr-defined]
        async with db.begin():
            posts = await job_lead_radar.delete_posts(db, run_id=run_id)
            repos = await code_verifier.delete_repositories(db, run_id=run_id)
    return {"raw_posts_deleted": posts, "repositories_deleted": repos}


async def remove_demo(*, session_factory: SessionFactory = AsyncSessionLocal) -> dict:
    async with session_factory() as db:      # type: ignore[attr-defined]
        async with db.begin():
            scores = await leaderboard.delete_demo_scores(db)
            sessions = await voice_defense.delete_demo_sessions(db)
            posts = await job_lead_radar.delete_posts(db, demo_only=True)
            repos = await code_verifier.delete_repositories(db, demo_only=True)
    return {"raw_posts_deleted": posts, "repositories_deleted": repos,
            "interview_sessions_deleted": sessions, "leaderboard_rows_deleted": scores}
