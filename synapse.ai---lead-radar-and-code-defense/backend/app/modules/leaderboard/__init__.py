"""Leaderboard module public API. Import from here only (never from submodules)."""

from . import models  # noqa: F401  (registers tables with SQLAlchemy metadata)
from .router import router
from .ingestion import DemoScore, delete_demo_scores, ingest_demo_score
from .interfaces import LeaderboardRecorder

__all__ = ["router", "LeaderboardRecorder", "DemoScore", "ingest_demo_score", "delete_demo_scores"]
