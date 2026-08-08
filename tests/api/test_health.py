"""Tests for process and dependency health endpoints."""

from fastapi.testclient import TestClient
from pydantic import SecretStr

from jobagent.api import create_app
from jobagent.core import Settings, TransientJobAgentError


class FakeDatabase:
    """Controllable in-memory stand-in for database health."""

    def __init__(self, *, available: bool = True) -> None:
        self.available = available
        self.ping_count = 0
        self.closed = False

    async def ping(self) -> None:
        self.ping_count += 1
        if not self.available:
            raise TransientJobAgentError(
                "Database unavailable in test.",
                code="database.unavailable",
            )

    async def close(self) -> None:
        self.closed = True


def build_test_settings() -> Settings:
    return Settings(
        environment="test",
        log_level="CRITICAL",
        timezone="UTC",
        database_url=SecretStr("postgresql+psycopg://jobagent:test-only@localhost/jobagent_test"),
    )


def test_liveness_does_not_query_database() -> None:
    database = FakeDatabase(available=False)

    with TestClient(create_app(build_test_settings(), database)) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive", "checks": None}
    assert database.ping_count == 0
    assert database.closed is True


def test_readiness_reports_available_database() -> None:
    database = FakeDatabase()

    with TestClient(create_app(build_test_settings(), database)) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {"database": "available"}}
    assert database.ping_count == 1


def test_readiness_returns_503_without_leaking_error() -> None:
    database = FakeDatabase(available=False)

    with TestClient(create_app(build_test_settings(), database)) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"database": "unavailable"},
    }
    assert "test-only" not in response.text
