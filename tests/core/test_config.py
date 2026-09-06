"""Tests for typed environment configuration."""

from pathlib import Path

import pytest

from jobagent.core.config import clear_settings_cache, get_settings
from jobagent.core.exceptions import ConfigurationError


@pytest.fixture(autouse=True)
def clear_cached_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure each test reads its own environment variables."""
    monkeypatch.setenv(
        "JOBAGENT_DATABASE_URL",
        "postgresql+psycopg://jobagent:test-only@localhost:5432/jobagent_test",
    )
    clear_settings_cache()


def test_settings_load_from_prefixed_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JOBAGENT_ENVIRONMENT", "test")
    monkeypatch.setenv("JOBAGENT_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("JOBAGENT_TIMEZONE", "UTC")
    monkeypatch.setenv("JOBAGENT_ATTACHMENT_STORAGE_PATH", "data/test-attachments")
    monkeypatch.setenv("JOBAGENT_ATTACHMENT_MAX_BYTES", "4096")
    monkeypatch.setenv("JOBAGENT_ATTACHMENT_CHUNK_BYTES", "512")
    monkeypatch.setenv("JOBAGENT_SOURCE_CATALOG_PATH", "config/test-sources.toml")
    monkeypatch.setenv("JOBAGENT_SCHEDULER_HOUR", "7")
    monkeypatch.setenv("JOBAGENT_SCHEDULER_MINUTE", "30")
    monkeypatch.setenv("JOBAGENT_SCHEDULER_MISFIRE_GRACE_SECONDS", "7200")
    monkeypatch.setenv("JOBAGENT_SCHEDULER_STAGE_MAX_ATTEMPTS", "4")
    monkeypatch.setenv("JOBAGENT_SCHEDULER_RETRY_DELAY_SECONDS", "15")

    settings = get_settings()

    assert settings.environment == "test"
    assert settings.log_level == "DEBUG"
    assert settings.timezone == "UTC"
    assert settings.attachment_storage_path == Path("data/test-attachments")
    assert settings.attachment_max_bytes == 4096
    assert settings.attachment_chunk_bytes == 512
    assert settings.source_catalog_path == Path("config/test-sources.toml")
    assert settings.scheduler_hour == 7
    assert settings.scheduler_minute == 30
    assert settings.scheduler_misfire_grace_seconds == 7200
    assert settings.scheduler_stage_max_attempts == 4
    assert settings.scheduler_retry_delay_seconds == 15


def test_missing_required_environment_fails_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JOBAGENT_ENVIRONMENT", raising=False)

    with pytest.raises(ConfigurationError) as captured:
        get_settings()

    assert captured.value.code == "configuration.invalid"
    assert captured.value.retryable is False
    assert captured.value.details["errors"]


def test_invalid_timezone_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JOBAGENT_ENVIRONMENT", "development")
    monkeypatch.setenv("JOBAGENT_TIMEZONE", "Mars/Olympus_Mons")

    with pytest.raises(ConfigurationError) as captured:
        get_settings()

    assert captured.value.details["errors"]


def test_invalid_scheduler_time_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JOBAGENT_ENVIRONMENT", "development")
    monkeypatch.setenv("JOBAGENT_SCHEDULER_HOUR", "24")

    with pytest.raises(ConfigurationError) as captured:
        get_settings()

    assert captured.value.details["errors"]
