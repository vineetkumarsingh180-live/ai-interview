"""
Code Verifier module: repository submission and results.

This build does not clone, run or analyse repositories. A submission is therefore stored as
`awaiting_analysis` with NO benchmark and NO evaluation. Those appear only when a real analysis
engine writes them. Nothing here may invent scores, languages, commit ids or verdicts.
"""

import uuid
from typing import List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import CandidateRepo
from .schemas import RepoSubmissionRequest


class CodeVerifierService:
    @staticmethod
    async def submit_repository(db: AsyncSession, submission: RepoSubmissionRequest) -> CandidateRepo:
        repo_name = submission.repo_url.rstrip("/").split("/")[-1]
        repo = CandidateRepo(
            candidate_name=submission.candidate_name.strip(),
            candidate_github_handle=submission.candidate_github_handle.strip().lstrip("@"),
            candidate_avatar_url=submission.candidate_avatar_url,
            repo_url=submission.repo_url,
            repo_name=repo_name,
            target_role=submission.target_role,
            branch=submission.branch,
            commit_sha=None,
            language=None,
            status="awaiting_analysis",
            benchmark=None,       # no analysis has run: explicit "nothing measured", no lazy load later
            evaluation=None,
        )
        db.add(repo)
        await db.commit()   # expire_on_commit is off: ids/defaults are already on the instance
        return repo

    @staticmethod
    async def get_repo_details(db: AsyncSession, repo_id: uuid.UUID) -> Optional[CandidateRepo]:
        stmt = (
            select(CandidateRepo)
            .options(selectinload(CandidateRepo.benchmark), selectinload(CandidateRepo.evaluation))
            .where(CandidateRepo.id == repo_id)
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    @staticmethod
    async def list_recent_repos(db: AsyncSession, limit: int = 20) -> List[CandidateRepo]:
        stmt = (
            select(CandidateRepo)
            .options(selectinload(CandidateRepo.benchmark), selectinload(CandidateRepo.evaluation))
            .order_by(desc(CandidateRepo.submitted_at))
            .limit(limit)
        )
        return list((await db.execute(stmt)).scalars().all())
