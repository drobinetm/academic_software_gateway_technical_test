from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = Field(default="local", alias="ENVIRONMENT")
    innovasoft_base_url: str = Field(..., alias="INNOVASOFT_BASE_URL")
    mongodb_uri: str = Field(..., alias="MONGODB_URI")
    mongodb_database: str = Field(..., alias="MONGODB_DATABASE")
    api_timeout_seconds: float = Field(default=30.0, alias="API_TIMEOUT_SECONDS")
    cors_origins_raw: str = Field(default="", alias="CORS_ORIGINS")
    cors_origin_regex_raw: str = Field(default="", alias="CORS_ORIGIN_REGEX")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    upstream_openapi_url: str = Field(
        default="https://pruebareactjs.test-class.com/Api/swagger/v1/swagger.json",
        alias="UPSTREAM_OPENAPI_URL",
    )
    upstream_openapi_fetch_timeout: float = Field(
        default=5.0, alias="UPSTREAM_OPENAPI_FETCH_TIMEOUT"
    )
    openapi_cache_path: str = Field(
        default="static/innovasoft_openapi_cache.json", alias="OPENAPI_CACHE_PATH"
    )
    request_logs_collection: str = Field(default="request_logs", alias="REQUEST_LOGS_COLLECTION")
    request_log_ttl_seconds: int | None = Field(default=None, alias="REQUEST_LOG_TTL_SECONDS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        if not self.cors_origins_raw:
            return []
        return [item.strip() for item in self.cors_origins_raw.split(",") if item.strip()]

    @property
    def cors_origin_regex(self) -> str | None:
        if not self.cors_origin_regex_raw.strip():
            return None
        return self.cors_origin_regex_raw.strip()

    @field_validator("innovasoft_base_url")
    @classmethod
    def _ensure_trailing_slash(cls, value: str) -> str:
        return value if value.endswith("/") else f"{value}/"

    @field_validator("environment", "log_level", mode="before")
    @classmethod
    def _empty_string_to_default(cls, value: object, info) -> object:
        if value is None:
            return value
        if not isinstance(value, str) or value.strip():
            return value
        defaults = {
            "environment": "local",
            "log_level": "INFO",
        }
        return defaults[info.field_name]

    @field_validator("request_log_ttl_seconds", mode="before")
    @classmethod
    def _empty_ttl_to_none(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
