"""
Voice Defense module: interview sessions and turns.

Honesty rules: answers are recorded, never auto-scored, and no hiring verdict is produced. The
interviewer's follow-up comes from the AI provider when it is available; otherwise the turn is
reported as `unavailable` (the answer is still stored for a human reviewer).
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.errors import NotFound
from app.shared.gemini import extract_text, generate_content, is_configured

from .interfaces import LeaderboardPublisher, RepositoryLookup
from .models import VoiceSession
from .schemas import VoiceSessionInitRequest, VoiceTurnInput, VoiceTurnOutput

logger = logging.getLogger("synapse.voice_defense")

REVIEW_STATE = "needs_human_review"

# A fixed, neutral opening question (no claims about the candidate's code).
OPENING_QUESTION = (
    "Please walk me through the project you submitted: what problem it solves, how it is "
    "structured, and which design decisions you would defend."
)

_INTERVIEWER_INSTRUCTION = (
    "You are a technical interviewer. Based only on the dialogue so far, ask ONE concise follow-up "
    "question (max 2 sentences) that probes the candidate's last answer. Do not evaluate, score, "
    "or praise. Do not mention facts the candidate has not stated."
)


def _clock() -> str:
    return datetime.utcnow().strftime("%M:%S")


class VoiceInterviewService:
    @staticmethod
    async def create_session(
        db: AsyncSession, request: VoiceSessionInitRequest, repositories: RepositoryLookup
    ) -> VoiceSession:
        summary = await repositories.get_summary(db, request.repo_id) if request.repo_id else None
        candidate_name = summary.candidate_name if summary else (request.candidate_name or "Candidate")
        opening = OPENING_QUESTION
        if request.focus_topic:
            opening = f"{OPENING_QUESTION} Please pay particular attention to: {request.focus_topic}."

        session = VoiceSession(
            repo_id=request.repo_id if summary else None,
            candidate_name=candidate_name,
            session_status="active",
            defense_verdict=REVIEW_STATE,
            transcript_turns=[{"speaker": "ai_interviewer", "text": opening, "timestamp": _clock()}],
            key_takeaways=[],
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def process_candidate_turn(
        db: AsyncSession,
        payload: VoiceTurnInput,
        leaderboard: LeaderboardPublisher,
        repositories: RepositoryLookup,
    ) -> VoiceTurnOutput:
        session = await db.get(VoiceSession, payload.session_id)
        if not session:
            raise NotFound("Voice session not found.")

        turns = list(session.transcript_turns or [])
        turns.append({"speaker": "candidate", "text": payload.candidate_speech_text, "timestamp": _clock()})

        reply: Optional[str] = None
        if is_configured():
            history = "\n".join(f"{t['speaker']}: {t['text']}" for t in turns[-6:])
            body = {
                "contents": [{"parts": [{"text": f"Dialogue:\n{history}\n\nNext interviewer question:"}]}],
                "systemInstruction": {"parts": [{"text": _INTERVIEWER_INSTRUCTION}]},
                "generationConfig": {"temperature": 0.4, "maxOutputTokens": 160},
            }
            try:
                reply = (extract_text(await generate_content(body, timeout=15.0)) or "").strip() or None
            except Exception as exc:
                logger.error("Interviewer generation failed: %s", type(exc).__name__)

        if reply:
            turns.append({"speaker": "ai_interviewer", "text": reply, "timestamp": _clock()})
        session.transcript_turns = turns
        session.defense_verdict = REVIEW_STATE
        await db.commit()

        summary = await repositories.get_summary(db, session.repo_id) if session.repo_id else None
        await leaderboard.publish_voice_result(
            db,
            session_id=session.id,
            candidate_name=session.candidate_name,
            candidate_handle=summary.github_handle if summary else None,
            repo_name=summary.repo_name if summary else None,
            target_role=summary.target_role if summary else None,
            composite_score=session.final_composite_score,
        )

        return VoiceTurnOutput(
            session_id=session.id,
            turn_number=sum(1 for t in turns if t["speaker"] == "candidate"),
            ai_status="generated" if reply else "unavailable",
            interviewer_reply_text=reply,
            defense_score_delta=None,
            current_composite_score=session.final_composite_score,
            current_verdict=session.defense_verdict,
        )
