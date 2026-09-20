"""
Pydantic v2 Schemas for AI Voice Defense & Live Assessment Leaderboard (Tab 2, Feature 2)
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

class TranscriptTurn(BaseModel):
    speaker: str = Field(..., example="ai_interviewer")  # 'ai_interviewer' or 'candidate'
    text: str
    timestamp: str
    audio_url: Optional[str] = None
    technical_assessment_note: Optional[str] = None

class VoiceSessionInitRequest(BaseModel):
    repo_id: Optional[UUID] = None
    candidate_name: str = Field(default="Candidate")
    focus_topic: Optional[str] = Field(default="Raft Consensus & Log Compaction Under Network Partition")

class VoiceTurnInput(BaseModel):
    session_id: UUID
    candidate_speech_text: str
    audio_base64: Optional[str] = None

class VoiceTurnOutput(BaseModel):
    session_id: UUID
    interviewer_reply_text: str
    interviewer_audio_base64: Optional[str] = None
    defense_score_delta: Optional[float] = None
    current_composite_score: float
    current_verdict: str
    turn_number: int

class VoiceSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    repo_id: Optional[UUID]
    candidate_name: str
    session_status: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: int
    technical_depth_score: float
    clarity_articulation_score: float
    architecture_defense_score: float
    final_composite_score: float
    defense_verdict: str
    transcript_turns: List[Dict[str, Any]]
    key_takeaways: List[str]

class LeaderboardScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    candidate_name: str
    candidate_avatar_url: Optional[str]
    candidate_handle: str
    target_role: str
    repo_name: str
    code_health_score: float
    voice_defense_score: float
    composite_percentile: float
    rank_tier: str
    status_tag: str
    recorded_at: datetime
