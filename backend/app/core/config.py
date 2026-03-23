from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]  # backend/


class Settings(BaseSettings):
    """
    Centralized environment configuration.

    IMPORTANT: all env vars should be added here to keep configuration consistent.
    """

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    VERSION: str = Field(default="1.0.0", description="Public API/server version")
    PROJECT_NAME: str = Field(default="CodexArena", description="Application name")

    # CORS
    CORS_ALLOW_ORIGINS: str = Field(
        default="*",
        description="Comma-separated list of allowed origins. Use '*' for all origins.",
    )

    # JWT
    JWT_SECRET_KEY: str = Field(default="change-me", description="JWT signing secret")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, description="Access token expiry (minutes)")

    # Supabase
    SUPABASE_URL: str | None = Field(default=None)
    SUPABASE_ANON_KEY: str | None = Field(default=None)
    SUPABASE_SERVICE_ROLE_KEY: str | None = Field(default=None)

    # Redis / Arq
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    ARQ_QUEUE_NAME: str = Field(default="codexarena")

    # Minio (object storage) placeholder
    MINIO_ENDPOINT: str = Field(default="http://localhost:9000")
    MINIO_ACCESS_KEY: str = Field(default="minioadmin")
    MINIO_SECRET_KEY: str = Field(default="minioadmin")

    # Gemini
    GEMINI_API_KEY: str | None = Field(default=None)

    @property
    def cors_allow_origins_list(self) -> List[str]:
        raw = (self.CORS_ALLOW_ORIGINS or "*").strip()
        if raw == "*":
            return ["*"]
        return [item.strip() for item in raw.split(",") if item.strip()]


settings = Settings()

