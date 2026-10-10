"""
Voice Defense module: HTTP and WebSocket routes (URLs unchanged).
"""

import json
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database import AsyncSessionLocal, get_db
from app.shared.errors import ApiError, NotFound

from .interfaces import (
    LeaderboardPublisher,
    RepositoryLookup,
    get_leaderboard_publisher,
    get_repository_lookup,
)
from .models import VoiceSession
from .schemas import VoiceSessionInitRequest, VoiceSessionResponse, VoiceTurnInput, VoiceTurnOutput
from .service import VoiceInterviewService

router = APIRouter(prefix="/assessment/voice", tags=["Voice Defense"])


@router.post(
    "/init",
    response_model=VoiceSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start an interview session (returns the opening question and the session id to use)",
)
async def initialize_voice_session(
    request: VoiceSessionInitRequest,
    db: AsyncSession = Depends(get_db),
    repositories: RepositoryLookup = Depends(get_repository_lookup),
):
    return await VoiceInterviewService.create_session(db=db, request=request, repositories=repositories)


@router.post(
    "/turn",
    response_model=VoiceTurnOutput,
    summary="Record a candidate answer and get the interviewer's follow-up (never a score or verdict)",
)
async def process_voice_turn(
    turn: VoiceTurnInput,
    db: AsyncSession = Depends(get_db),
    leaderboard: LeaderboardPublisher = Depends(get_leaderboard_publisher),
    repositories: RepositoryLookup = Depends(get_repository_lookup),
):
    return await VoiceInterviewService.process_candidate_turn(
        db=db, payload=turn, leaderboard=leaderboard, repositories=repositories
    )


@router.get("/{session_id}", response_model=VoiceSessionResponse, summary="One session with its transcript")
async def get_session(session_id: UUID, db: AsyncSession = Depends(get_db)):
    session = await db.get(VoiceSession, session_id)
    if not session:
        raise NotFound("Voice session not found.")
    return session


@router.websocket("/stream/{session_id}")
async def voice_defense_websocket_endpoint(
    websocket: WebSocket,
    session_id: UUID,
    leaderboard: LeaderboardPublisher = Depends(get_leaderboard_publisher),
    repositories: RepositoryLookup = Depends(get_repository_lookup),
):
    """Text-turn WebSocket: send {"type":"candidate_speech","text":"..."}; same semantics as POST /turn."""
    await websocket.accept()
    try:
        await websocket.send_json({"event": "connected", "sessionId": str(session_id)})
        while True:
            data = json.loads(await websocket.receive_text())
            if data.get("type", "candidate_speech") != "candidate_speech":
                continue
            async with AsyncSessionLocal() as db:
                try:
                    result = await VoiceInterviewService.process_candidate_turn(
                        db=db,
                        payload=VoiceTurnInput(session_id=session_id, candidate_speech_text=data.get("text", "")),
                        leaderboard=leaderboard,
                        repositories=repositories,
                    )
                except ApiError as exc:
                    await websocket.send_json({"event": "error", "code": exc.code, "detail": exc.detail})
                    continue
            await websocket.send_json({"event": "turn", **result.model_dump(by_alias=True, mode="json")})
    except WebSocketDisconnect:
        pass
