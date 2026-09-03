"""JAI-024 report generation, snapshot, Markdown, and HTML API checks."""

from datetime import UTC, date, datetime

from fastapi.testclient import TestClient
from pydantic import SecretStr

from jobagent.api import create_app
from jobagent.core import PermanentJobAgentError
from jobagent.core.config import Settings
from jobagent.reports import (
    DailyReport,
    DailyReportSection,
    DailyReportSnapshot,
    ReportGroup,
)


class FakeDatabase:
    async def ping(self) -> None:
        return None

    async def close(self) -> None:
        return None


class FakeReportService:
    def __init__(self, error: PermanentJobAgentError | None = None) -> None:
        self.error = error
        self.generated: list[date] = []
        self.loaded: list[int] = []
        report = DailyReport(
            report_date=date(2026, 9, 3),
            timezone="Asia/Shanghai",
            report_version="jai-024-v1",
            input_hash="a" * 64,
            sections=tuple(DailyReportSection(group, ()) for group in ReportGroup),
        )
        self.snapshot = DailyReportSnapshot(
            id=7,
            report=report,
            content_hash="b" * 64,
            markdown="# 日报\n",
            html="<!doctype html><html><body>日报</body></html>",
            created_at=datetime(2026, 9, 3, 2, tzinfo=UTC),
        )

    async def generate(self, report_date: date) -> DailyReportSnapshot:
        self.generated.append(report_date)
        if self.error is not None:
            raise self.error
        return self.snapshot

    async def get(self, snapshot_id: int) -> DailyReportSnapshot:
        self.loaded.append(snapshot_id)
        if self.error is not None:
            raise self.error
        return self.snapshot


def test_generate_returns_structured_snapshot_and_both_renderings() -> None:
    service = FakeReportService()
    with TestClient(create_app(_settings(), FakeDatabase(), report_service=service)) as client:
        response = client.post("/reports/daily", json={"report_date": "2026-09-03"})

    assert response.status_code == 200
    assert response.json()["snapshot_id"] == 7
    assert response.json()["report"]["report_date"] == "2026-09-03"
    assert len(response.json()["report"]["sections"]) == 4
    assert response.json()["markdown"] == "# 日报\n"
    assert response.json()["html"].startswith("<!doctype html>")
    assert service.generated == [date(2026, 9, 3)]


def test_snapshot_rendering_endpoints_return_exact_persisted_content() -> None:
    service = FakeReportService()
    with TestClient(create_app(_settings(), FakeDatabase(), report_service=service)) as client:
        snapshot = client.get("/reports/daily/7")
        markdown = client.get("/reports/daily/7/markdown")
        html = client.get("/reports/daily/7/html")

    assert snapshot.status_code == 200
    assert markdown.status_code == 200
    assert markdown.text == "# 日报\n"
    assert markdown.headers["content-type"].startswith("text/markdown")
    assert html.status_code == 200
    assert html.text == "<!doctype html><html><body>日报</body></html>"
    assert html.headers["content-type"].startswith("text/html")
    assert service.loaded == [7, 7, 7]


def test_missing_snapshot_maps_to_404() -> None:
    service = FakeReportService(
        PermanentJobAgentError(
            "Missing.",
            code="reports.snapshot_not_found",
            details={"snapshot_id": 999},
        )
    )
    with TestClient(create_app(_settings(), FakeDatabase(), report_service=service)) as client:
        response = client.get("/reports/daily/999")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "reports.snapshot_not_found"


def test_report_endpoint_is_explicitly_unavailable_without_service() -> None:
    with TestClient(create_app(_settings(), FakeDatabase())) as client:
        response = client.post("/reports/daily", json={"report_date": "2026-09-03"})

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "reports.service_unavailable"


def _settings() -> Settings:
    return Settings(
        environment="test",
        log_level="CRITICAL",
        timezone="Asia/Shanghai",
        database_url=SecretStr("postgresql+psycopg://jobagent:test-only@localhost/jobagent_test"),
    )
