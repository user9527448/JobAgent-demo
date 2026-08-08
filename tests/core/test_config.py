"""Tests for typed environment configuration."""

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

    settings = get_settings()

    assert settings.environment == "test"
    assert settings.log_level == "DEBUG"
    assert settings.timezone == "UTC"


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
