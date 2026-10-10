"""
Application configuration (infrastructure only; module settings live in each module's config.py).

Values come from environment variables, then `backend/.env` (never committed; see `.env.example`).
"""

from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    PROJECT_NAME: str = "Synapse.AI"
    VERSION: str = "3.0.0"
    API_V1_STR: str = "/api/v1"

    # Dedicated, isolated Synapse database (role `synapse_app`, database `synapse_dev`).
    # Never point this at another project's database.
    DATABASE_URL: str = "postgresql+asyncpg://synapse_app@localhost:5432/synapse_dev"

    # Gemini (server-side only; the browser never sees the key). Empty = AI features unavailable.
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Origins allowed to call the API directly from a browser (the Vite dev server proxies /api,
    # so same-origin calls need no CORS at all).
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
