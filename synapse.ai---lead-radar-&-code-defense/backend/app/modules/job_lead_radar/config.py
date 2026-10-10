"""Job Lead Radar module settings (moved out of app.shared.config; env names unchanged)."""

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.shared.config import BACKEND_ROOT


class LeadRadarSettings(BaseSettings):
    # Embedding configuration
    EMBEDDING_MODEL: str = "models/gemini-embedding-2-preview"
    EMBEDDING_DIMENSIONS: int = 768

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env", case_sensitive=True, extra="ignore"
    )


lead_radar_settings = LeadRadarSettings()
