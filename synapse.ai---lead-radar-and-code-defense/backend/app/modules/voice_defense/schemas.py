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
    resume_text: Optional[str] = Field(default=None, description="Candidate resume text or summary")
    gemini_api_key_1: Optional[str] = Field(default=None, description="Dedicated Gemini API key for Voice Defense")
    gemini_api_key_voice_defense: Optional[str] = Field(default=None, description="Dedicated Gemini API key for Voice Defense")


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
    current_composite_score: Optional[float] = Field(default=None, description="Current score out of 10 if completed")
    current_verdict: str = Field(description="Review state or interview_completed")
    interview_stage: Optional[str] = None
    is_completed: bool = False
    evaluation_score: Optional[float] = None
    evaluation_feedback: Optional[str] = None
    is_doubt_response: Optional[bool] = False


class VoiceCompleteResponse(ApiModel):
    session_id: UUID
    overall_score: float = Field(..., description="Overall score in range 1.0 to 10.0")
    technical_depth_score: float = Field(..., description="Score in range 1.0 to 10.0")
    clarity_articulation_score: float = Field(..., description="Score in range 1.0 to 10.0")
    project_defense_score: float = Field(..., description="Score in range 1.0 to 10.0")
    summary: str
    key_strengths: List[str] = Field(default_factory=list)
    areas_for_improvement: List[str] = Field(default_factory=list)
    defense_verdict: str


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
