"""
Voice Defense module: ports for functionality owned by other modules.

The composition root (app/core/wiring.py) binds these to concrete implementations, so this
module never imports another module.
"""

from dataclasses import dataclass
from typing import Optional, Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class RepositorySummary:
    candidate_name: str
    github_handle: str
    repo_name: str
    target_role: Optional[str]


class RepositoryLookup(Protocol):
    """Reads repository facts (owned by the Code Verifier module)."""

    async def get_summary(self, db: AsyncSession, repo_id: UUID) -> Optional[RepositorySummary]: ...


class LeaderboardPublisher(Protocol):
    """Publishes a session result to the leaderboard (owned by the Leaderboard module)."""

    async def publish_voice_result(
        self,
        db: AsyncSession,
        *,
        session_id: UUID,
        candidate_name: str,
        candidate_handle: Optional[str],
        repo_name: Optional[str],
        target_role: Optional[str],
        composite_score: Optional[float],
    ) -> None: ...


def get_leaderboard_publisher() -> LeaderboardPublisher:
    raise RuntimeError("LeaderboardPublisher is not wired; see app/core/wiring.py")


def get_repository_lookup() -> RepositoryLookup:
    raise RuntimeError("RepositoryLookup is not wired; see app/core/wiring.py")
