"""Voice Defense module public API. Import from here only (never from submodules)."""

from . import models  # noqa: F401  (registers tables with SQLAlchemy metadata)
from .router import router
from .interfaces import (
    LeaderboardPublisher,
    RepositoryLookup,
    get_leaderboard_publisher,
    get_repository_lookup,
)

__all__ = [
    "router",
    "LeaderboardPublisher",
    "RepositoryLookup",
    "get_leaderboard_publisher",
    "get_repository_lookup",
]
