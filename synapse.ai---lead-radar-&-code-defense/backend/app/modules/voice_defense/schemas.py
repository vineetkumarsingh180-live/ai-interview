"""
Voice Defense module: request/response contract (camelCase on the wire).
"""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import Field

from app.shared.schemas import ApiModel


class TranscriptTurn(ApiModel):
    speaker: Literal["ai_interviewer", "candidate"]
    text: str
    timestamp: str
    audio_url: Optional[str] = None
    technical_assessment_note: Optional[str] = None


class VoiceSessionInitRequest(ApiModel):
    repo_id: Optional[UUID] = None
    candidate_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    focus_topic: Optional[str] = Field(default=None, max_length=300)


class VoiceTurnInput(ApiModel):
    session_id: UUID
    candidate_speech_text: str = Field(..., min_length=1, max_length=8000)


class VoiceTurnOutput(ApiModel):
    session_id: UUID
    turn_number: int
    ai_status: Literal["generated", "unavailable"] = Field(
        description="'unavailable' means no interviewer reply could be generated; the answer was still recorded"
    )
    interviewer_reply_text: Optional[str] = None
    defense_score_delta: Optional[float] = Field(default=None, description="Null: answers are not auto-scored")
    current_composite_score: Optional[float] = Field(default=None, description="Null: answers are not auto-scored")
    current_verdict: str = Field(description="Always a review state such as needs_human_review; never a hiring decision")


class VoiceSessionResponse(ApiModel):
    id: UUID
    repo_id: Optional[UUID] = None
    candidate_name: str
    session_status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: int
    technical_depth_score: Optional[float] = None
    clarity_articulation_score: Optional[float] = None
    architecture_defense_score: Optional[float] = None
    final_composite_score: Optional[float] = None
    defense_verdict: str
    transcript_turns: List[TranscriptTurn]
    key_takeaways: List[str]
