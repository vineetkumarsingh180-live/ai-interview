"""
Code Verifier: public ingestion interface used by DbIngestion.

It turns a GitHub metadata snapshot (exactly what GitHub returned) into a `candidate_repos` row.
No analysis happens: status stays `awaiting_analysis`, benchmark/evaluation stay absent. Flushes but
does not commit: the caller owns the transaction.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.github import GitHubRepoSnapshot
from app.shared.ingestion_log import (
    CREATED,
    DUPLICATE,
    REJECTED,
    UPDATED,
    IngestContext,
    IngestionResult,
)

from .models import CandidateRepo

_URL = re.compile(r"^https?://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<name>[A-Za-z0-9_.-]+?)(?:\.git)?/?$")


def parse_github_url(url: str) -> Optional[Tuple[str, str]]:
    """(owner, repo) for a plain GitHub repository URL, else None."""
    m = _URL.match((url or "").strip())
    return (m.group("owner"), m.group("name")) if m else None


@dataclass
class RepoRecord:
    """What the operator provides for one repository."""

    repo_url: str
    candidate_name: Optional[str] = None
    target_role: Optional[str] = None


def _metadata(snapshot: GitHubRepoSnapshot) -> dict:
    """Exactly the fields GitHub returned; nothing computed or inferred."""
    return {
        "full_name": snapshot.full_name,
        "description": snapshot.description,
        "topics": snapshot.topics,
        "languages_bytes": snapshot.languages_bytes,
        "stars": snapshot.stars,
        "forks": snapshot.forks,
        "open_issues": snapshot.open_issues,
        "license": snapshot.license_spdx,
        "visibility": snapshot.visibility,
        "archived": snapshot.archived,
        "fork": snapshot.is_fork,
        "size_kb": snapshot.size_kb,
        "created_at": snapshot.created_at,
        "pushed_at": snapshot.pushed_at,
        "updated_at": snapshot.updated_at,
    }


async def register_github_repository(
    db: AsyncSession,
    snapshot: GitHubRepoSnapshot,
    ctx: IngestContext,
    *,
    candidate_name: Optional[str] = None,
    target_role: Optional[str] = None,
) -> IngestionResult:
    metadata = _metadata(snapshot)

    row = (await db.execute(select(CandidateRepo).where(CandidateRepo.github_repo_id == snapshot.github_id))).scalar_one_or_none()
    if row is None:   # a row typed in by hand earlier (same URL, no GitHub facts yet)
        row = (
            await db.execute(select(CandidateRepo).where(func.lower(CandidateRepo.repo_url) == snapshot.html_url.lower()))
        ).scalar_one_or_none()

    if row is not None:
        unchanged = (
            row.github_repo_id == snapshot.github_id
            and row.github_metadata == metadata
            and row.commit_sha == snapshot.head_sha
            and row.language == snapshot.language
            and row.branch == snapshot.default_branch
        )
        if unchanged:
            return IngestionResult(status=DUPLICATE, entity="repository", entity_id=row.id, code="unchanged", obj=row,
                                   message="GitHub reports the same metadata as already stored")
        row.github_repo_id = snapshot.github_id
        row.github_metadata = metadata
        row.metadata_fetched_at = snapshot.fetched_at
        row.commit_sha = snapshot.head_sha
        row.language = snapshot.language
        row.branch = snapshot.default_branch
        row.repo_name = snapshot.name
        row.repo_url = snapshot.html_url
        row.source_type = "github_api" if not ctx.is_demo else row.source_type
        row.verification_status = "github_metadata"
        await db.flush()
        return IngestionResult(status=UPDATED, entity="repository", entity_id=row.id, code="metadata_refreshed")

    repo = CandidateRepo(
        candidate_name=(candidate_name or snapshot.owner_login).strip()[:255],
        candidate_github_handle=snapshot.owner_login[:120],
        candidate_avatar_url=snapshot.owner_avatar_url,
        repo_url=snapshot.html_url,
        repo_name=snapshot.name,
        target_role=target_role,
        branch=snapshot.default_branch,
        commit_sha=snapshot.head_sha,
        language=snapshot.language,
        status="awaiting_analysis",
        is_demo=ctx.is_demo,
        source_type="demo_fixture" if ctx.is_demo else "github_api",
        verification_status="demo_fixture" if ctx.is_demo else "github_metadata",
        github_repo_id=snapshot.github_id,
        github_metadata=metadata,
        metadata_fetched_at=snapshot.fetched_at,
        ingestion_run_id=ctx.run_id,
        benchmark=None,
        evaluation=None,
    )
    try:
        async with db.begin_nested():
            db.add(repo)
            await db.flush()
    except IntegrityError:
        return IngestionResult(status=DUPLICATE, entity="repository", code="duplicate_race",
                               message="the repository was inserted concurrently by another process")
    return IngestionResult(status=CREATED, entity="repository", entity_id=repo.id, obj=repo)


def reject_repo_url(url: str) -> IngestionResult:
    return IngestionResult(status=REJECTED, entity="repository", code="invalid_github_url",
                           message=f"not a plain GitHub repository URL: {url!r}")


async def register_repository_url(db: AsyncSession, record: RepoRecord, ctx: IngestContext) -> IngestionResult:
    """
    Register a repository by URL alone (no GitHub call): used for operator-typed submissions and
    labelled demo fixtures. No language/commit/avatar is invented: they stay NULL.
    """
    parsed = parse_github_url(record.repo_url)
    if parsed is None:
        return reject_repo_url(record.repo_url)
    owner, name = parsed
    url = f"https://github.com/{owner}/{name}"
    existing = (await db.execute(select(CandidateRepo).where(func.lower(CandidateRepo.repo_url) == url.lower()))).scalar_one_or_none()
    if existing is not None:
        return IngestionResult(status=DUPLICATE, entity="repository", entity_id=existing.id, code="duplicate_url",
                               message="this repository URL is already stored", obj=existing)
    repo = CandidateRepo(
        candidate_name=(record.candidate_name or owner).strip()[:255],
        candidate_github_handle=owner[:120],
        repo_url=url,
        repo_name=name,
        target_role=record.target_role,
        status="awaiting_analysis",
        is_demo=ctx.is_demo,
        source_type="demo_fixture" if ctx.is_demo else "api_manual",
        verification_status="demo_fixture" if ctx.is_demo else "unverified",
        ingestion_run_id=ctx.run_id,
        benchmark=None,
        evaluation=None,
    )
    try:
        async with db.begin_nested():
            db.add(repo)
            await db.flush()
    except IntegrityError:
        return IngestionResult(status=DUPLICATE, entity="repository", code="duplicate_race")
    return IngestionResult(status=CREATED, entity="repository", entity_id=repo.id, obj=repo)


async def delete_repositories(db: AsyncSession, *, run_id=None, demo_only: bool = False) -> int:
    """Delete repositories created by one ingestion run, or all labelled demo rows. Never anything else."""
    from sqlalchemy import delete

    if run_id is None and not demo_only:
        raise ValueError("refusing to delete without a run id or demo_only=True")
    cond = CandidateRepo.ingestion_run_id == run_id if run_id is not None else CandidateRepo.is_demo.is_(True)
    result = await db.execute(delete(CandidateRepo).where(cond))
    return int(result.rowcount or 0)


@dataclass
class DemoAnalysis:
    """
    Fixture values for a labelled demo repository. They are NOT measurements: nothing in this
    product analyses code yet, so these are accepted only when the ingestion context is a demo.
    """

    repo_url: str
    candidate_name: str
    candidate_handle: str
    repo_name: str
    avatar_url: Optional[str] = None
    submitted_at: Optional[datetime] = None
    github_metadata: Optional[dict] = None   # fixture values; never labelled as fetched (metadata_fetched_at stays NULL)
    target_role: Optional[str] = None
    branch: Optional[str] = None
    commit_sha: Optional[str] = None
    language: Optional[str] = None
    benchmark: Optional[dict] = None     # test_coverage_pct, cyclomatic_complexity, sec_vulnerabilities_count, execution_time_ms, suite_log_output
    evaluation: Optional[dict] = None    # composite_health_score, architecture_score, concurrency_safety_score, maintainability_score, summary_verdict, rubric_breakdown, flagged_anomalies, recommended_defense_topics


async def register_demo_analysed_repository(db: AsyncSession, record: DemoAnalysis, ctx: IngestContext) -> IngestionResult:
    """Register a labelled showcase repository together with its fixture benchmark/evaluation rows."""
    from .models import BenchmarkSuite, CodeEvaluationResult

    if not ctx.is_demo:
        return IngestionResult(status=REJECTED, entity="repository", code="demo_only",
                               message="analysis values can only be ingested as labelled demo fixtures")
    parsed = parse_github_url(record.repo_url)
    if parsed is None:
        return reject_repo_url(record.repo_url)
    owner, name = parsed
    url = f"https://github.com/{owner}/{name}"
    existing = (await db.execute(select(CandidateRepo).where(func.lower(CandidateRepo.repo_url) == url.lower()))).scalar_one_or_none()
    if existing is not None:
        return IngestionResult(status=DUPLICATE, entity="repository", entity_id=existing.id, code="duplicate_url",
                               message="this repository URL is already stored", obj=existing)
    now = datetime.utcnow()
    repo = CandidateRepo(
        candidate_name=record.candidate_name.strip()[:255],
        candidate_github_handle=record.candidate_handle.strip()[:120],
        candidate_avatar_url=record.avatar_url,
        repo_url=url,
        repo_name=record.repo_name or name,
        target_role=record.target_role,
        branch=record.branch,
        commit_sha=record.commit_sha,
        language=record.language,
        status="analyzed" if record.evaluation else "awaiting_analysis",
        is_demo=True,
        source_type="demo_fixture",
        verification_status="demo_fixture",
        ingestion_run_id=ctx.run_id,
        submitted_at=record.submitted_at or now,
        github_metadata=record.github_metadata,
    )
    if record.benchmark:
        repo.benchmark = BenchmarkSuite(created_at=now, **record.benchmark)
    if record.evaluation:
        repo.evaluation = CodeEvaluationResult(evaluated_at=now, **record.evaluation)
    try:
        async with db.begin_nested():
            db.add(repo)
            await db.flush()
    except IntegrityError:
        return IngestionResult(status=DUPLICATE, entity="repository", code="duplicate_race")
    return IngestionResult(status=CREATED, entity="repository", entity_id=repo.id, obj=repo)
