"""
Synapse.AI FastAPI Application Factory
Mounts domain feature routers for Tab 1 (Leads Radar) and Tab 2 (Code Assessment & Voice Defense).
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db

# Import Tab 1 routers
from app.tab1_leads.feature1_ingestion.router import router as ingestion_router
from app.tab1_leads.feature2_outreach.router import router as outreach_router

# Import Tab 2 routers
from app.tab2_assessment.feature1_code_verifier.router import router as verifier_router
from app.tab2_assessment.feature2_voice_interview.router import router as voice_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("synapse.app")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for database initialization and connection teardown"""
    logger.info("Initializing Synapse.AI domain models and pgvector schemas...")
    try:
        await init_db()
        logger.info("Database schemas and pgvector extension ready.")
    except Exception as e:
        logger.warning(f"Database initialization deferred (running in local container sandbox): {e}")
    yield
    logger.info("Shutting down Synapse.AI backend.")

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
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount Tab 1: Lead Radar Domain Routers
    application.include_router(ingestion_router, prefix=settings.API_V1_STR)
    application.include_router(outreach_router, prefix=settings.API_V1_STR)

    # Mount Tab 2: Code Verification & Voice Defense Routers
    application.include_router(verifier_router, prefix=settings.API_V1_STR)
    application.include_router(voice_router, prefix=settings.API_V1_STR)

    @application.get("/api/health", tags=["Health"])
    async def health_check():
        return {
            "status": "healthy",
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "tab1_modules": ["feature1_ingestion", "feature2_outreach"],
            "tab2_modules": ["feature1_code_verifier", "feature2_voice_interview"]
        }

    return application

app = create_application()
