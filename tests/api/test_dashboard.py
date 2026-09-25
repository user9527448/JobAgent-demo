"""JAI-050 read-only Morning Briefing API checks."""

from dataclasses import replace
from datetime import UTC, date, datetime

from fastapi.testclient import TestClient
from pydantic import SecretStr

from jobagent.api import create_app
from jobagent.core import Settings, TransientJobAgentError
from jobagent.dashboard import (
    BriefingSnapshot,
    DeliveryEvidence,
    DeliveryEvidenceState,
    PipelineRunEvidence,
    ReportEvidence,
    ReportItemEvidence,
    ScheduleEvidence,
    StageEvidence,
)


class FakeDatabase:
    async def ping(self) -> None:
        return None

    async def close(self) -> None:
        return None


class FakeDashboardService:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

    async def get_briefing(self) -> BriefingSnapshot:
        if self.fail:
            raise TransientJobAgentError(
                "Database URL postgresql://secret must never leak.",
                code="dashboard.database_unavailable",
            )
        started_at = datetime(2026, 9, 6, 0, 0, tzinfo=UTC)
        return BriefingSnapshot(
            generated_at=datetime(2026, 9, 14, 0, 30, tzinfo=UTC),
            timezone="Asia/Shanghai",
            scheduler=ScheduleEvidence(
                job_id="jobagent.daily-pipeline.v1",
                present=True,
                next_run_at=datetime(2026, 9, 15, 0, 0, tzinfo=UTC),
            ),
            recent_runs=(
                PipelineRunEvidence(
                    id=1,
                    scheduled_for=started_at,
                    report_date=date(2026, 9, 6),
                    trigger="makeup",
                    status="succeeded",
                    current_stage=None,
                    started_at=started_at,
                    finished_at=datetime(2026, 9, 6, 0, 4, tzinfo=UTC),
                    stages=(
                        StageEvidence(
                            stage="collection",
                            attempt=1,
                            status="succeeded",
                            started_at=started_at,
                            finished_at=datetime(2026, 9, 6, 0, 1, tzinfo=UTC),
                        ),
                        StageEvidence(
                            stage="extraction",
                            attempt=1,
                            status="succeeded",
                            started_at=datetime(2026, 9, 6, 0, 1, tzinfo=UTC),
                            finished_at=datetime(2026, 9, 6, 0, 2, tzinfo=UTC),
                        ),
                        StageEvidence(
                            stage="matching",
                            attempt=1,
                            status="succeeded",
                            started_at=datetime(2026, 9, 6, 0, 2, tzinfo=UTC),
                            finished_at=datetime(2026, 9, 6, 0, 3, tzinfo=UTC),
                        ),
                        StageEvidence(
                            stage="report",
                            attempt=1,
                            status="succeeded",
                            started_at=datetime(2026, 9, 6, 0, 3, tzinfo=UTC),
                            finished_at=datetime(2026, 9, 6, 0, 4, tzinfo=UTC),
                        ),
                        StageEvidence(
                            stage="delivery",
                            attempt=1,
                            status="partial",
                            started_at=datetime(2026, 9, 6, 0, 4, tzinfo=UTC),
                            finished_at=datetime(2026, 9, 6, 0, 4, tzinfo=UTC),
                        ),
                    ),
                ),
            ),
            missing_record_dates=(date(2026, 9, 7), date(2026, 9, 8)),
            latest_report=ReportEvidence(
                snapshot_id=2,
                report_date=date(2026, 9, 6),
                report_version="jai-024-v1",
                created_at=datetime(2026, 9, 6, 0, 4, tzinfo=UTC),
                item_count=3,
                group_counts={"priority_applications": 2, "closing_soon": 1},
                items=(
                    ReportItemEvidence(
                        group="priority_applications",
                        position_id=6,
                        match_result_id=6,
                        organization="合成单位",
                        title="合成岗位",
                        region="北京",
                        deadline=None,
                        score=88,
                        reason="与偏好匹配。",
                        risks=(),
                        source_url="https://example.invalid/jobs/6",
                    ),
                    ReportItemEvidence(
                        group="priority_applications",
                        position_id=7,
                        match_result_id=7,
                        organization="示例研究院",
                        title="数据分析师 (合成样本)",
                        region="上海",
                        deadline="2026-09-30T16:00:00Z",
                        score=84,
                        reason="岗位能力要求与合成偏好高度重合。",
                        risks=("学历要求需要确认",),
                        source_url="https://example.invalid/jobs/7",
                    ),
                    ReportItemEvidence(
                        group="closing_soon",
                        position_id=8,
                        match_result_id=8,
                        organization="演示科技",
                        title="产品经理 (合成样本)",
                        region="深圳",
                        deadline="2026-09-18T16:00:00Z",
                        score=79,
                        reason="工作方向与合成经历存在可解释匹配。",
                        risks=(),
                        source_url="https://example.invalid/jobs/8",
                    ),
                ),
            ),
            delivery=DeliveryEvidence(DeliveryEvidenceState.UNAVAILABLE_SCHEMA),
        )


class EmptyDashboardService(FakeDashboardService):
    async def get_briefing(self) -> BriefingSnapshot:
        snapshot = await super().get_briefing()
        return replace(
            snapshot,
            scheduler=ScheduleEvidence(
                job_id="jobagent.daily-pipeline.v1",
                present=False,
                next_run_at=None,
            ),
            recent_runs=(),
            missing_record_dates=(),
            latest_report=None,
            delivery=DeliveryEvidence(DeliveryEvidenceState.NO_REPORT),
        )


def test_briefing_returns_bounded_persisted_evidence() -> None:
    with TestClient(
        create_app(
            _settings(),
            FakeDatabase(),
            dashboard_service=FakeDashboardService(),
        )
    ) as client:
        response = client.get("/dashboard/briefing")

    assert response.status_code == 200
    payload = response.json()
    assert payload["scheduler"]["job_id"] == "jobagent.daily-pipeline.v1"
    assert payload["recent_runs"][0]["stages"][0]["stage"] == "collection"
    assert payload["missing_record_dates"] == ["2026-09-07", "2026-09-08"]
    assert payload["latest_report"]["snapshot_id"] == 2
    assert payload["latest_report"]["items"][0]["score"] == 88
    assert payload["delivery"]["state"] == "unavailable_schema"


def test_briefing_is_unavailable_without_database_backed_service() -> None:
    with TestClient(create_app(_settings(), FakeDatabase())) as client:
        response = client.get("/dashboard/briefing")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "dashboard.service_unavailable"


def test_briefing_database_error_is_sanitized() -> None:
    with TestClient(
        create_app(
            _settings(),
            FakeDatabase(),
            dashboard_service=FakeDashboardService(fail=True),
        )
    ) as client:
        response = client.get("/dashboard/briefing")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "dashboard.database_unavailable"
    assert "secret" not in response.text


def test_briefing_preserves_empty_evidence_as_empty_not_error() -> None:
    with TestClient(
        create_app(
            _settings(),
            FakeDatabase(),
            dashboard_service=EmptyDashboardService(),
        )
    ) as client:
        response = client.get("/dashboard/briefing")

    assert response.status_code == 200
    payload = response.json()
    assert payload["scheduler"]["present"] is False
    assert payload["recent_runs"] == []
    assert payload["latest_report"] is None
    assert payload["delivery"]["state"] == "no_report"


def _settings() -> Settings:
    return Settings(
        environment="test",
        log_level="CRITICAL",
        timezone="Asia/Shanghai",
        database_url=SecretStr("postgresql+psycopg://jobagent:test-only@localhost/jobagent_test"),
    )
