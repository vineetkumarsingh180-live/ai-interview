"""
Leaderboard module: response contract (camelCase on the wire).
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from app.shared.schemas import ApiModel


class LeaderboardScoreResponse(ApiModel):
    """One assessed candidate. Any score that was not measured is null; `statusTag` is a review state."""

    id: UUID
    session_id: UUID
    candidate_name: str
    candidate_avatar_url: Optional[str] = None
    candidate_handle: Optional[str] = None
    target_role: Optional[str] = None
    repo_name: Optional[str] = None
    code_health_score: Optional[float] = None
    voice_defense_score: Optional[float] = None
    composite_percentile: Optional[float] = None
    rank_tier: Optional[str] = None
    status_tag: str
    recorded_at: datetime
