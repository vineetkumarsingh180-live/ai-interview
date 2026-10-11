"""Voice Defense module public API. Import from here only (never from submodules)."""

from . import models  # noqa: F401  (registers tables with SQLAlchemy metadata)
from .router import router
from .ingestion import DemoSession, delete_demo_sessions, ingest_demo_session
from .interfaces import (
    FollowUpQuestion,
    Interviewer,
    LeaderboardPublisher,
    RepositoryLookup,
    get_interviewer,
    get_leaderboard_publisher,
    get_repository_lookup,
)

__all__ = [
    "FollowUpQuestion",
    "Interviewer",
    "get_interviewer",
    "router",
    "DemoSession",
    "ingest_demo_session",
    "delete_demo_sessions",
    "LeaderboardPublisher",
    "RepositoryLookup",
    "get_leaderboard_publisher",
    "get_repository_lookup",
]
