import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "Synapse.AI"
    VERSION: str = "2.6.0"
    API_V1_STR: str = "/api/v1"
    
    # Asynchronous PostgreSQL connection string with pgvector
    DATABASE_URL: str = Field(
        default=os.getenv(
            "DATABASE_URL", 
            "postgresql+asyncpg://postgres:postgres@localhost:5432/synapse_db"
        ),
        description="Async PostgreSQL connection string with asyncpg driver"
    )
    
    # Google Gemini API configuration
    GEMINI_API_KEY: str = Field(
        default=os.getenv("GEMINI_API_KEY", ""),
        description="Google Gemini API key for parsing, code review, and voice defense"
    )
    
    # Embedding configuration
    EMBEDDING_MODEL: str = "models/gemini-embedding-2-preview"
    EMBEDDING_DIMENSIONS: int = 768
    
    # Verification Thresholds
    VOICE_DEFENSE_CUTOFF_SCORE: float = 82.0
    AUTO_HIRE_THRESHOLD: float = 89.0

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
