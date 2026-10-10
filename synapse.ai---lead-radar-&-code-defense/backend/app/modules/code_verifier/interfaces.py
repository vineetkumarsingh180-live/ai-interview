"""
Code Verifier module: public read contract for other modules (consumed via the composition root).
"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from .models import CandidateRepo


@dataclass(frozen=True)
class RepositorySummary:
    """Facts about a repository that other modules may read. Matches Voice Defense's port by shape."""

    candidate_name: str
    github_handle: str
    repo_name: str
    target_role: Optional[str]


class RepositoryDirectory:
    """Implements Voice Defense's `RepositoryLookup` port without importing that module."""

    async def get_summary(self, db: AsyncSession, repo_id: UUID) -> Optional[RepositorySummary]:
        repo = await db.get(CandidateRepo, repo_id)
        if repo is None:
            return None
        return RepositorySummary(
            candidate_name=repo.candidate_name,
            github_handle=repo.candidate_github_handle,
            repo_name=repo.repo_name,
            target_role=repo.target_role,
        )
