"""
AI Voice Defense & Live Assessment Leaderboard Service (Tab 2, Feature 2)
Manages live technical interrogation, speech turns, real-time score adjustment, and leaderboard ranking.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.tab2_assessment.feature1_code_verifier.models import CandidateRepo
from app.tab2_assessment.feature2_voice_interview.models import VoiceSession, LeaderboardScore
from app.tab2_assessment.feature2_voice_interview.schemas import (
    VoiceSessionInitRequest,
    VoiceTurnInput,
    VoiceTurnOutput,
)

logger = logging.getLogger("synapse.voice_interview")

INITIAL_DEFENSE_PROMPT = (
    "I see in your Raft implementation you've configured election timeouts between 150ms and 300ms. "
    "Under a partial cross-rack network split where heartbeats are intermittently dropped, how does your "
    "state machine prevent split-vote thrashing and uncommitted log divergence?"
)

class VoiceInterviewService:
    @staticmethod
    async def create_session(
        db: AsyncSession,
        request: VoiceSessionInitRequest
    ) -> VoiceSession:
        """Initializes a new live voice defense session"""
        repo = None
        if request.repo_id:
            repo = await db.get(CandidateRepo, request.repo_id)

        candidate_name = repo.candidate_name if repo else request.candidate_name
        session = VoiceSession(
            repo_id=request.repo_id,
            candidate_name=candidate_name,
            session_status="active",
            technical_depth_score=88.0,
            clarity_articulation_score=90.0,
            architecture_defense_score=89.0,
            final_composite_score=89.0,
            defense_verdict="HUMAN_REVIEW",
            transcript_turns=[
                {
                    "speaker": "ai_interviewer",
                    "text": INITIAL_DEFENSE_PROMPT,
                    "timestamp": "00:02",
                    "technical_assessment_note": "Initial architectural probe regarding Raft election jitter"
                }
            ],
            key_takeaways=[
                "Probing split-vote election stability",
                "Verifying hands-on authorship vs LLM boilerplate"
            ]
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def process_candidate_turn(
        db: AsyncSession,
        payload: VoiceTurnInput
    ) -> VoiceTurnOutput:
        """Processes candidate's verbal response, grades answer depth, and generates the next technical challenge"""
        session = await db.get(VoiceSession, payload.session_id)
        if not session:
            raise ValueError("Voice defense session not found")

        turns = list(session.transcript_turns or [])
        turn_num = len(turns) + 1
        now_ts = datetime.utcnow().strftime("%M:%S")

        # Append candidate response
        turns.append({
            "speaker": "candidate",
            "text": payload.candidate_speech_text,
            "timestamp": now_ts
        })

        # Calculate incremental score adjustment based on technical richness
        candidate_text = payload.candidate_speech_text.lower()
        score_boost = 0.0
        if any(term in candidate_text for term in ["pre-vote", "randomized", "quorum", "term", "snapshot", "linearizable", "atomic"]):
            score_boost += 1.8
        if len(payload.candidate_speech_text.split()) > 25:
            score_boost += 0.7

        new_composite = min(99.4, session.final_composite_score + score_boost)
        session.final_composite_score = round(new_composite, 1)

        # Generate adaptive interrogation challenge
        interviewer_reply = (
            "Good clarification on the pre-vote phase. Now, suppose the leader crashes during "
            "log compaction right before the snapshot metadata is fsync'd. How does your storage layer "
            "recover the write-ahead log without corrupting existing follower replicas?"
        )

        if settings.GEMINI_API_KEY:
            try:
                system_prompt = (
                    "You are a rigorous, elite AI technical interviewer grilling a senior software engineer on their "
                    "distributed systems code. The candidate just answered your previous question. "
                    "Respond with a follow-up challenge or stress-test question that is sharp, concise (2-3 sentences max), "
                    "and tests deep engineering fundamentals. Do not be condescending, be deeply technical."
                )
                dialogue_history = "\n".join([f"{t['speaker']}: {t['text']}" for t in turns[-4:]])
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={settings.GEMINI_API_KEY}"
                p_payload = {
                    "contents": [{"parts": [{"text": f"Recent dialogue:\n{dialogue_history}\n\nGenerate next AI interviewer question:"}]}],
                    "systemInstruction": {"parts": [{"text": system_prompt}]},
                    "generationConfig": {"temperature": 0.5, "maxOutputTokens": 200}
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, json=p_payload)
                    if resp.status_code == 200:
                        interviewer_reply = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            except Exception as e:
                logger.error(f"Gemini voice dialogue generation error: {e}")

        turns.append({
            "speaker": "ai_interviewer",
            "text": interviewer_reply,
            "timestamp": datetime.utcnow().strftime("%M:%S"),
            "technical_assessment_note": f"Depth score evaluated at {session.final_composite_score}%"
        })
        session.transcript_turns = turns

        if session.final_composite_score >= settings.AUTO_HIRE_THRESHOLD:
            session.defense_verdict = "AUTO_HIRE"
        else:
            session.defense_verdict = "HUMAN_REVIEW"

        await db.commit()

        # Update or create leaderboard entry if qualified
        await VoiceInterviewService.upsert_leaderboard_score(db, session)

        return VoiceTurnOutput(
            session_id=session.id,
            interviewer_reply_text=interviewer_reply,
            defense_score_delta=round(score_boost, 1),
            current_composite_score=session.final_composite_score,
            current_verdict=session.defense_verdict,
            turn_number=turn_num
        )

    @staticmethod
    async def upsert_leaderboard_score(db: AsyncSession, session: VoiceSession) -> None:
        """Synchronizes candidate session to the live assessment leaderboard"""
        stmt = select(LeaderboardScore).where(LeaderboardScore.session_id == session.id)
        existing = (await db.execute(stmt)).scalar_one_or_none()

        if not existing:
            existing = LeaderboardScore(
                session_id=session.id,
                candidate_name=session.candidate_name,
                candidate_handle=session.candidate_name.lower().replace(" ", ""),
                target_role="Staff Distributed Systems Engineer",
                repo_name="distributed-raft-kv",
                code_health_score=94.2,
                voice_defense_score=session.final_composite_score,
                composite_percentile=min(99.8, session.final_composite_score + 1.2),
                rank_tier="Top 1%" if session.final_composite_score >= 90 else "Top 5%",
                status_tag="Auto-Hire Candidate" if session.final_composite_score >= 89.0 else "Passed Defense"
            )
            db.add(existing)
        else:
            existing.voice_defense_score = session.final_composite_score
            existing.composite_percentile = min(99.8, session.final_composite_score + 1.2)
        await db.commit()

    @staticmethod
    async def list_leaderboard(db: AsyncSession, limit: int = 20) -> List[LeaderboardScore]:
        stmt = select(LeaderboardScore).order_by(desc(LeaderboardScore.composite_percentile)).limit(limit)
        res = await db.execute(stmt)
        return list(res.scalars().all())
