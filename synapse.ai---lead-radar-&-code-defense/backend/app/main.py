"""
Synapse.AI FastAPI Application Factory
Composes the four modules: Job Lead Radar, Code Verifier, Voice Defense, Leaderboard.
"""

import logging
from typing import Literal
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.shared.config import settings
from app.shared.database import check_database
from app.core.api import build_api_router
from app.core.wiring import wire_dependencies
from app.shared.errors import register_exception_handlers
from app.shared.schemas import ApiModel
from app.shared.gemini import is_configured

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("synapse.app")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: report database/AI availability. Never creates schema (Alembic owns it)."""
    if await check_database():
        logger.info("Database reachable.")
    else:
        logger.warning("Database unreachable: DB-backed routes will return 503 until it is available.")
    if not settings.GEMINI_API_KEY:
        logger.info("GEMINI_API_KEY not set: AI features will report 'unavailable'.")
    yield
    logger.info("Shutting down Synapse.AI backend.")

class HealthResponse(ApiModel):
    status: Literal["ok", "degraded"]
    service: str
    version: str
    database: Literal["connected", "unreachable"]
    gemini: Literal["configured", "not_configured"]


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
        lifespan=lifespan,
    )

    # Set up CORS for frontend integration
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount all module routers (composition lives in app/core/api.py)
    application.include_router(build_api_router(), prefix=settings.API_V1_STR)
    wire_dependencies(application)

    register_exception_handlers(application)

    @application.get("/api/health", response_model=HealthResponse, tags=["Health"])
    async def health_check():
        database = await check_database()
        return HealthResponse(
            status="ok" if database else "degraded",
            service=settings.PROJECT_NAME,
            version=settings.VERSION,
            database="connected" if database else "unreachable",
            gemini="configured" if is_configured() else "not_configured",
        )

    return application

app = create_application()
