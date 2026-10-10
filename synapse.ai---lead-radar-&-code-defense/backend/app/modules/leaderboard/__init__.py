"""Leaderboard module public API. Import from here only (never from submodules)."""

from . import models  # noqa: F401  (registers tables with SQLAlchemy metadata)
from .router import router
from .interfaces import LeaderboardRecorder

__all__ = ["router", "LeaderboardRecorder"]
