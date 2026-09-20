"""
FastAPI Modular Router for AI Voice Defense & Live Assessment Leaderboard (Tab 2, Feature 2)
Provides both REST endpoints and real-time WebSocket connection.
"""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.core.database import get_db, AsyncSessionLocal
from app.tab2_assessment.feature2_voice_interview.models import VoiceSession
from app.tab2_assessment.feature2_voice_interview.schemas import (
    VoiceSessionInitRequest,
    VoiceSessionResponse,
    VoiceTurnInput,
    VoiceTurnOutput,
    LeaderboardScoreResponse,
)
from app.tab2_assessment.feature2_voice_interview.service import VoiceInterviewService

router = APIRouter(prefix="/assessment/voice", tags=["Tab 2 - Voice Interview Defense"])

@router.post(
    "/init",
    response_model=VoiceSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initialize an interactive AI Voice Defense session"
)
async def initialize_voice_session(
    request: VoiceSessionInitRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        session = await VoiceInterviewService.create_session(db=db, request=request)
        return session
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start voice defense session: {str(e)}"
        )

@router.post(
    "/turn",
    response_model=VoiceTurnOutput,
    summary="Submit candidate answer turn and receive adaptive interviewer follow-up"
)
async def process_voice_turn(
    turn: VoiceTurnInput,
    db: AsyncSession = Depends(get_db)
):
    try:
        return await VoiceInterviewService.process_candidate_turn(db=db, payload=turn)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice turn processing failed: {str(e)}")

@router.get(
    "/leaderboard",
    response_model=List[LeaderboardScoreResponse],
    summary="Fetch live assessment leaderboard rankings"
)
async def get_leaderboard(
    db: AsyncSession = Depends(get_db)
):
    return await VoiceInterviewService.list_leaderboard(db=db)

@router.get(
    "/{session_id}",
    response_model=VoiceSessionResponse,
    summary="Retrieve complete voice session record with transcript"
)
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    session = await db.get(VoiceSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.websocket("/stream/{session_id}")
async def voice_defense_websocket_endpoint(
    websocket: WebSocket,
    session_id: str
):
    """
    Real-time WebSocket connection for low-latency bidirectional audio / transcript defense streaming.
    """
    await websocket.accept()
    try:
        await websocket.send_json({
            "event": "connected",
            "session_id": session_id,
            "status": "ready",
            "message": "AI Voice Defense stream established. Ready for audio and speech input."
        })
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            event_type = data.get("type", "candidate_speech")

            if event_type == "candidate_speech":
                speech_text = data.get("text", "")
                async with AsyncSessionLocal() as db:
                    result = await VoiceInterviewService.process_candidate_turn(
                        db=db,
                        payload=VoiceTurnInput(
                            session_id=UUID(session_id),
                            candidate_speech_text=speech_text,
                        )
                    )
                    await websocket.send_json({
                        "event": "interviewer_speech",
                        "turn": result.turn_number,
                        "text": result.interviewer_reply_text,
                        "score": result.current_composite_score,
                        "score_delta": result.defense_score_delta,
                        "verdict": result.current_verdict
                    })
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"event": "error", "error": str(e)})
        except Exception:
            pass
