"""Typed application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from jobagent.core.exceptions import ConfigurationError, JsonValue


class Settings(BaseSettings):
    """Validated settings shared by the API, worker, and command-line tasks."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="JOBAGENT_",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    environment: Literal["development", "test", "production"]
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    timezone: str = "Asia/Shanghai"
    app_name: str = "jobagent"
    database_url: SecretStr
    attachment_storage_path: Path = Path("data/attachments")
    attachment_max_bytes: int = Field(default=25 * 1024 * 1024, gt=0)
    attachment_chunk_bytes: int = Field(default=64 * 1024, gt=0)

    @field_validator("timezone")
    @classmethod
    def timezone_must_exist(cls, value: str) -> str:
        """Reject invalid IANA time zone identifiers during startup."""
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("must be a valid IANA time zone") from error
        return value


def _safe_validation_errors(error: ValidationError) -> list[JsonValue]:
    """Remove raw inputs from validation errors before logging or returning them."""
    return [
        {
            "field": ".".join(str(part) for part in item["loc"]),
            "message": str(item["msg"]),
            "type": str(item["type"]),
        }
        for item in error.errors(include_url=False, include_input=False)
    ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load settings once and convert provider errors into a domain exception."""
    try:
        # Required fields are supplied dynamically by BaseSettings from the environment.
        return Settings()  # type: ignore[call-arg]
    except ValidationError as error:
        raise ConfigurationError(
            "Application configuration is missing or invalid.",
            details={"errors": _safe_validation_errors(error)},
        ) from error


def clear_settings_cache() -> None:
    """Clear cached settings for tests and explicit configuration reloads."""
    get_settings.cache_clear()
