"""
API router composition.

Each module publishes one `router`. The order matters in exactly one place: the leaderboard route
`/assessment/voice/leaderboard` must be registered before voice-defense's `/{session_id}` route,
otherwise "leaderboard" would be parsed as a session id.
"""

from fastapi import APIRouter

from app.modules import code_verifier, job_lead_radar, leaderboard, voice_defense
from app.shared.schemas import ErrorResponse

_ERRORS = {
    404: {"model": ErrorResponse, "description": "Not found"},
    409: {"model": ErrorResponse, "description": "Conflict"},
    422: {"model": ErrorResponse, "description": "Validation failed"},
    500: {"model": ErrorResponse, "description": "Unexpected server error"},
    503: {"model": ErrorResponse, "description": "A dependency (AI provider or database) is unavailable"},
}


def build_api_router() -> APIRouter:
    api = APIRouter(responses=_ERRORS)
    api.include_router(job_lead_radar.router)
    api.include_router(code_verifier.router)
    api.include_router(leaderboard.router)   # before voice_defense (see module docstring)
    api.include_router(voice_defense.router)
    return api
