"""Same-origin production frontend routing checks."""

from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import SecretStr

from jobagent.api import create_app
from jobagent.core import Settings


class FakeDatabase:
    async def ping(self) -> None:
        return None

    async def close(self) -> None:
        return None


def test_frontend_index_and_client_route_use_same_shell(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html><body>JOBAGENT UI</body></html>", encoding="utf-8")

    with TestClient(create_app(_settings(dist), FakeDatabase())) as client:
        root = client.get("/app/")
        client_route = client.get("/app/planned-route")

    assert root.status_code == 200
    assert root.text == client_route.text
    assert "JOBAGENT UI" in root.text


def test_frontend_missing_build_is_safe_503(tmp_path: Path) -> None:
    with TestClient(create_app(_settings(tmp_path / "missing"), FakeDatabase())) as client:
        response = client.get("/app/")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "frontend.build_unavailable"


def _settings(frontend_dist_path: Path) -> Settings:
    return Settings(
        environment="test",
        log_level="CRITICAL",
        timezone="Asia/Shanghai",
        database_url=SecretStr("postgresql+psycopg://jobagent:test-only@localhost/jobagent_test"),
        frontend_dist_path=frontend_dist_path,
    )
