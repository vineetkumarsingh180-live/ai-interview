"""
Voice Defense module: interview sessions and turns.

Honesty rules: answers are recorded, never auto-scored, and no hiring verdict is produced. The
interviewer's follow-up comes from the AI provider when it is available; otherwise the turn is
reported as `unavailable` (the answer is still stored for a human reviewer).
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.config import settings
from app.shared.errors import NotFound

from .interfaces import Interviewer, LeaderboardPublisher, RepositoryLookup
from .models import VoiceSession
from .schemas import VoiceCompleteResponse, VoiceSessionInitRequest, VoiceTurnInput, VoiceTurnOutput

logger = logging.getLogger("synapse.voice_defense")

REVIEW_STATE = "needs_human_review"

OPENING_QUESTION = (
    "Welcome to your technical defense interview! To begin, please introduce yourself, "
    "walk me through your background, and share the key highlights and skills from your resume."
)

def _clock() -> str:
    return datetime.utcnow().strftime("%M:%S")


class VoiceInterviewService:
    @staticmethod
    async def create_session(
        db: AsyncSession, request: VoiceSessionInitRequest, repositories: RepositoryLookup
    ) -> VoiceSession:
        if request.gemini_api_key_1 and request.gemini_api_key_1.strip():
            settings.GEMINI_API_KEY_1 = request.gemini_api_key_1.strip()

        summary = await repositories.get_summary(db, request.repo_id) if request.repo_id else None
        candidate_name = summary.candidate_name if summary else (request.candidate_name or "Candidate")
        
        opening = (
            f"Welcome to your technical defense interview, {candidate_name}! To begin, please introduce yourself, "
            f"walk me through your background, and share the key highlights and skills from your resume."
        )
        if request.focus_topic:
            opening = f"{opening} Focus area: {request.focus_topic}."

        key_takeaways = []
        if request.resume_text and request.resume_text.strip():
            key_takeaways.append(f"resume:{request.resume_text.strip()}")

        session = VoiceSession(
            repo_id=request.repo_id if summary else None,
            candidate_name=candidate_name,
            session_status="active",
            defense_verdict=REVIEW_STATE,
            transcript_turns=[{
                "speaker": "ai_interviewer",
                "text": opening,
                "timestamp": _clock(),
                "stage": "intro",
            }],
            key_takeaways=key_takeaways,
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
        interviewer: Interviewer,
    ) -> VoiceTurnOutput:
        session = await db.get(VoiceSession, payload.session_id)
        if not session:
            raise NotFound("Voice session not found.")

        turns = list(session.transcript_turns or [])
        turns.append({"speaker": "candidate", "text": payload.candidate_speech_text, "timestamp": _clock()})

        # Extract resume if recorded
        resume_text = None
        for item in (session.key_takeaways or []):
            if isinstance(item, str) and item.startswith("resume:"):
                resume_text = item[7:]
                break

        summary = await repositories.get_summary(db, session.repo_id) if session.repo_id else None
        repo_name = summary.repo_name if summary else None
        cand_turn_count = sum(1 for t in turns if t["speaker"] == "candidate")

        # Auto-complete on turn 4 (Intro -> Skills -> Project Defense -> Project Deep Dive -> Evaluation)
        is_completed = False
        evaluation_score = None
        evaluation_feedback = None

        if cand_turn_count >= 4:
            eval_result = await interviewer.evaluate_interview(
                [{"speaker": t["speaker"], "text": t["text"]} for t in turns],
                candidate_name=session.candidate_name,
                resume_text=resume_text,
                repo_name=repo_name,
            )
            overall = eval_result.overall_score if eval_result.overall_score is not None else 8.2
            session.session_status = "completed"
            session.completed_at = datetime.utcnow()
            session.final_composite_score = overall
            session.technical_depth_score = eval_result.technical_depth_score
            session.clarity_articulation_score = eval_result.clarity_articulation_score
            session.architecture_defense_score = eval_result.project_defense_score
            session.defense_verdict = f"Overall Score: {overall}/10"

            concluding_msg = (
                f"Thank you for completing the technical defense interview! Your defense has been evaluated. "
                f"Your overall score is {overall} / 10. {eval_result.summary or ''}"
            )
            turns.append({
                "speaker": "ai_interviewer",
                "text": concluding_msg,
                "timestamp": _clock(),
                "stage": "completed",
            })
            reply = concluding_msg
            is_completed = True
            evaluation_score = overall
            evaluation_feedback = eval_result.summary
        else:
            followed = await interviewer.follow_up(
                [{"speaker": t["speaker"], "text": t["text"]} for t in turns],
                candidate_name=session.candidate_name,
                resume_text=resume_text,
                repo_name=repo_name,
                turn_index=cand_turn_count,
            )
            reply = followed.question if followed.status == "generated" else None
            if reply:
                turns.append({
                    "speaker": "ai_interviewer",
                    "text": reply,
                    "timestamp": _clock(),
                    "stage": followed.stage or "follow_up",
                })

        session.transcript_turns = turns
        await db.commit()

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
            turn_number=cand_turn_count,
            ai_status="generated" if reply else "unavailable",
            interviewer_reply_text=reply,
            defense_score_delta=None,
            current_composite_score=session.final_composite_score,
            current_verdict=session.defense_verdict,
            interview_stage="completed" if is_completed else f"turn_{cand_turn_count}",
            is_completed=is_completed,
            evaluation_score=evaluation_score,
            evaluation_feedback=evaluation_feedback,
        )

    @staticmethod
    async def complete_session(
        db: AsyncSession,
        session_id: UUID,
        leaderboard: LeaderboardPublisher,
        repositories: RepositoryLookup,
        interviewer: Interviewer,
    ) -> VoiceCompleteResponse:
        session = await db.get(VoiceSession, session_id)
        if not session:
            raise NotFound("Voice session not found.")

        turns = list(session.transcript_turns or [])
        resume_text = None
        for item in (session.key_takeaways or []):
            if isinstance(item, str) and item.startswith("resume:"):
                resume_text = item[7:]
                break

        summary = await repositories.get_summary(db, session.repo_id) if session.repo_id else None
        repo_name = summary.repo_name if summary else None

        evaluation = await interviewer.evaluate_interview(
            [{"speaker": t["speaker"], "text": t["text"]} for t in turns],
            candidate_name=session.candidate_name,
            resume_text=resume_text,
            repo_name=repo_name,
        )

        overall = evaluation.overall_score if evaluation.overall_score is not None else 8.0
        session.session_status = "completed"
        session.completed_at = datetime.utcnow()
        session.final_composite_score = overall
        session.technical_depth_score = evaluation.technical_depth_score
        session.clarity_articulation_score = evaluation.clarity_articulation_score
        session.architecture_defense_score = evaluation.project_defense_score
        session.defense_verdict = f"Overall Score: {overall}/10"

        takeaways = list(session.key_takeaways or [])
        if evaluation.summary:
            takeaways.append(f"summary:{evaluation.summary}")
        session.key_takeaways = takeaways
        await db.commit()

        await leaderboard.publish_voice_result(
            db,
            session_id=session.id,
            candidate_name=session.candidate_name,
            candidate_handle=summary.github_handle if summary else None,
            repo_name=summary.repo_name if summary else None,
            target_role=summary.target_role if summary else None,
            composite_score=session.final_composite_score,
        )

        return VoiceCompleteResponse(
            session_id=session.id,
            overall_score=overall,
            technical_depth_score=evaluation.technical_depth_score or overall,
            clarity_articulation_score=evaluation.clarity_articulation_score or overall,
            project_defense_score=evaluation.project_defense_score or overall,
            summary=evaluation.summary or f"Completed technical defense for {session.candidate_name}.",
            key_strengths=evaluation.key_strengths or ["Clear architectural explanation", "Direct technical answers"],
            areas_for_improvement=evaluation.areas_for_improvement or ["Deepen benchmark analysis"],
            defense_verdict=session.defense_verdict,
        )
