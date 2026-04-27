"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. All values come from env vars or .env file."""

    environment: str = Field(default="local", alias="ENVIRONMENT")
    innovasoft_base_url: str = Field(..., alias="INNOVASOFT_BASE_URL")
    mongodb_uri: str = Field(..., alias="MONGODB_URI")
    mongodb_database: str = Field(..., alias="MONGODB_DATABASE")
    api_timeout_seconds: float = Field(default=30.0, alias="API_TIMEOUT_SECONDS")
    cors_origins_raw: str = Field(default="", alias="CORS_ORIGINS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> List[str]:
        if not self.cors_origins_raw:
            return []
        return [item.strip() for item in self.cors_origins_raw.split(",") if item.strip()]

    @field_validator("innovasoft_base_url")
    @classmethod
    def _ensure_trailing_slash(cls, value: str) -> str:
        return value if value.endswith("/") else f"{value}/"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached `Settings` instance."""
    return Settings()  # type: ignore[call-arg]
