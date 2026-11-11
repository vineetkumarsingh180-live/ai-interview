"""
Code Verifier: read queries for this module's own tables (candidate_repos, benchmark_suites,
code_evaluation_results). Writes for ingestion live in ingestion.py.
"""

import uuid
from typing import List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import CandidateRepo


def _with_results():
    return (selectinload(CandidateRepo.benchmark), selectinload(CandidateRepo.evaluation))


async def get_repo(db: AsyncSession, repo_id: uuid.UUID) -> Optional[CandidateRepo]:
    stmt = select(CandidateRepo).options(*_with_results()).where(CandidateRepo.id == repo_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_repo_by_url(db: AsyncSession, repo_url: str) -> Optional[CandidateRepo]:
    stmt = select(CandidateRepo).options(*_with_results()).where(CandidateRepo.repo_url == repo_url)
    return (await db.execute(stmt)).scalar_one_or_none()


async def list_repos(db: AsyncSession, *, limit: int, include_demo: bool = True) -> List[CandidateRepo]:
    stmt = select(CandidateRepo).options(*_with_results()).order_by(desc(CandidateRepo.submitted_at)).limit(limit)
    if not include_demo:
        stmt = stmt.where(CandidateRepo.is_demo.is_(False))
    return list((await db.execute(stmt)).scalars().all())


async def delete_repo(db: AsyncSession, repo_id: uuid.UUID) -> bool:
    stmt = select(CandidateRepo).options(*_with_results()).where(CandidateRepo.id == repo_id)
    repo = (await db.execute(stmt)).scalar_one_or_none()
    if not repo:
        return False
    await db.delete(repo)
    await db.commit()
    return True
