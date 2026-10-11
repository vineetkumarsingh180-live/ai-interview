"""
Code Verifier module: repository submission and results.

This build does not clone, run or analyse repositories. A submission is therefore stored as
`awaiting_analysis` with NO benchmark and NO evaluation. Those appear only when a real analysis
engine writes them. Nothing here may invent scores, languages, commit ids or verdicts.
"""

import uuid
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.errors import Conflict, NotFound
from app.shared.ingestion_log import DUPLICATE, REJECTED, IngestContext

from . import repository
from .ingestion import RepoRecord, register_repository_url
from .interfaces import RepositoryAnalysis, RepositoryAnalyzer
from .models import CandidateRepo
from .schemas import RepoSubmissionRequest


class CodeVerifierService:
    @staticmethod
    async def submit_repository(db: AsyncSession, submission: RepoSubmissionRequest) -> CandidateRepo:
        """Registers the URL through the same ingestion function DbIngestion uses (dedup + provenance)."""
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
            await db.rollback()
            raise Conflict("This repository URL was already submitted.", code="duplicate_repository")
        if result.status == REJECTED:
            await db.rollback()
            raise Conflict(result.message or "The repository was rejected.", code=result.code or "rejected")
        repo: CandidateRepo = result.obj
        # operator-typed fields the URL alone cannot provide
        repo.candidate_github_handle = submission.candidate_github_handle.strip().lstrip("@")
        repo.candidate_avatar_url = submission.candidate_avatar_url
        repo.branch = submission.branch
        await db.commit()   # expire_on_commit is off: ids/defaults are already on the instance
        return repo

    @staticmethod
    async def get_repo_details(db: AsyncSession, repo_id: uuid.UUID) -> Optional[CandidateRepo]:
        return await repository.get_repo(db, repo_id)

    @staticmethod
    async def list_recent_repos(db: AsyncSession, limit: int = 20, include_demo: bool = True) -> List[CandidateRepo]:
        return await repository.list_repos(db, limit=limit, include_demo=include_demo)

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
