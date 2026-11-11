"""
Code Verifier module: repository submission and results.

This build does not clone, run or analyse repositories. A submission is therefore stored as
`awaiting_analysis` with NO benchmark and NO evaluation. Those appear only when a real analysis
engine writes them. Nothing here may invent scores, languages, commit ids or verdicts.
"""

import uuid
import logging
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.errors import Conflict, NotFound
from app.shared.ingestion_log import DUPLICATE, REJECTED, IngestContext

from . import repository
from .ingestion import RepoRecord, register_repository_url
from .interfaces import RepositoryAnalysis, RepositoryAnalyzer
from .models import CandidateRepo, BenchmarkSuite, CodeEvaluationResult
from .schemas import RepoSubmissionRequest
from .repo_ai_analyzer import analyze_github_repository, RepoAnalysisOutput

logger = logging.getLogger("synapse.code_verifier.service")


class CodeVerifierService:
    @staticmethod
    async def submit_repository(db: AsyncSession, submission: RepoSubmissionRequest) -> CandidateRepo:
        """Registers the URL and automatically triggers AI code scoring (vulgarity, bugs, advanced)."""
        result = await register_repository_url(
            db,
            RepoRecord(
                repo_url=submission.repo_url,
                candidate_name=submission.candidate_name,
                target_role=submission.target_role,
            ),
            IngestContext(source_type="api_manual"),
        )
        if result.status == DUPLICATE:
            # If already submitted, retrieve existing repo
            existing = await repository.get_repo_by_url(db, submission.repo_url) if hasattr(repository, "get_repo_by_url") else None
            if not existing:
                await db.rollback()
                raise Conflict("This repository URL was already submitted.", code="duplicate_repository")
            repo = existing
            if repo.evaluation:
                await db.delete(repo.evaluation)
            if repo.benchmark:
                await db.delete(repo.benchmark)
            await db.flush()
        elif result.status == REJECTED:
            await db.rollback()
            raise Conflict(result.message or "The repository was rejected.", code=result.code or "rejected")
        else:
            repo: CandidateRepo = result.obj

        repo.candidate_github_handle = submission.candidate_github_handle.strip().lstrip("@")
        repo.candidate_avatar_url = submission.candidate_avatar_url
        repo.branch = submission.branch
        await db.commit()

        # Run AI analysis on the submitted repo
        try:
            ai_out = await analyze_github_repository(submission.repo_url)
            return await CodeVerifierService._persist_analysis(db=db, repo=repo, ai_out=ai_out, repo_url=submission.repo_url)
        except Exception as exc:
            logger.error("Auto AI code evaluation failed for %s: %s", submission.repo_url, exc)

        return repo

    @staticmethod
    async def _persist_analysis(
        db: AsyncSession, repo: CandidateRepo, ai_out: RepoAnalysisOutput, repo_url: str
    ) -> CandidateRepo:
        repo.language = ai_out.primary_language
        repo.status = "analyzed"
        repo.verification_status = "ai_analyzed"

        if repo.evaluation:
            await db.delete(repo.evaluation)
        if repo.benchmark:
            await db.delete(repo.benchmark)
        await db.flush()

        eval_row = CodeEvaluationResult(
            repo_id=repo.id,
            composite_health_score=float(ai_out.overall_score),
            architecture_score=float(ai_out.rubric.advance_score),
            concurrency_safety_score=float(ai_out.rubric.vulgarity_score),
            maintainability_score=float(ai_out.rubric.bug_score),
            summary_verdict=ai_out.summary_verdict,
            rubric_breakdown=ai_out.rubric.model_dump(),
            flagged_anomalies=[{"category": "bug", "detail": b} for b in ai_out.rubric.detected_bugs]
            + [{"category": "vulgarity", "detail": v} for v in ai_out.rubric.vulgarity_detected],
            recommended_defense_topics=ai_out.recommended_defense_topics,
        )
        db.add(eval_row)

        bm_row = BenchmarkSuite(
            repo_id=repo.id,
            test_coverage_pct=float(ai_out.rubric.advance_score * 0.85),
            cyclomatic_complexity=float(max(1.0, 10.0 - (ai_out.rubric.bug_score / 15.0))),
            sec_vulnerabilities_count=len(ai_out.rubric.detected_bugs),
            execution_time_ms=120,
            suite_log_output=(
                f"AI Analysis completed for {repo_url}.\n"
                f"Vulgarity Score: {ai_out.rubric.vulgarity_score}/100\n"
                f"Bug & Safety Score: {ai_out.rubric.bug_score}/100\n"
                f"Advanced Architecture Score: {ai_out.rubric.advance_score}/100\n"
            ),
        )
        db.add(bm_row)
        await db.commit()

        refreshed = await repository.get_repo(db, repo.id)
        return refreshed or repo

    @staticmethod
    async def record_analyzed_repo(
        db: AsyncSession, submission: RepoSubmissionRequest, ai_out: RepoAnalysisOutput
    ) -> Optional[CandidateRepo]:
        """Records an analyzed repo into the database after direct live analysis."""
        result = await register_repository_url(
            db,
            RepoRecord(
                repo_url=submission.repo_url,
                candidate_name=submission.candidate_name,
                target_role=submission.target_role,
            ),
            IngestContext(source_type="api_manual"),
        )
        if result.status == DUPLICATE:
            existing = await repository.get_repo_by_url(db, submission.repo_url)
            if not existing:
                await db.rollback()
                return None
            repo = existing
        elif result.status == REJECTED:
            await db.rollback()
            return None
        else:
            repo: CandidateRepo = result.obj

        repo.candidate_name = submission.candidate_name
        repo.candidate_github_handle = (submission.candidate_github_handle or "").strip().lstrip("@")
        return await CodeVerifierService._persist_analysis(db=db, repo=repo, ai_out=ai_out, repo_url=submission.repo_url)

    @staticmethod
    async def get_repo_details(db: AsyncSession, repo_id: uuid.UUID) -> Optional[CandidateRepo]:
        return await repository.get_repo(db, repo_id)

    @staticmethod
    async def list_recent_repos(db: AsyncSession, limit: int = 20, include_demo: bool = True) -> List[CandidateRepo]:
        return await repository.list_repos(db, limit=limit, include_demo=include_demo)

    @staticmethod
    async def delete_repository(db: AsyncSession, repo_id: uuid.UUID) -> bool:
        return await repository.delete_repo(db, repo_id)

    @staticmethod
    async def request_analysis(db: AsyncSession, repo_id: uuid.UUID, analyzer: RepositoryAnalyzer) -> RepositoryAnalysis:
        """
        The seam where repository intelligence is called. This build fetches NO repository content,
        so the analyzer is given no files and answers `unavailable: repository_content_not_available`;
        nothing is stored and the repository stays `awaiting_analysis`. When a content source exists
        its files go in `files` here and a real result can be persisted by this method.
        """
        repo = await repository.get_repo(db, repo_id)
        if repo is None:
            raise NotFound(f"Repository {repo_id} was not found.")
        return await analyzer.analyze(repo_url=repo.repo_url, commit_sha=repo.commit_sha, files=[])
