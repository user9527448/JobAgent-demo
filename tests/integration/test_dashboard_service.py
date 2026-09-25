"""PostgreSQL acceptance for JAI-050 read-only dashboard evidence."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.orm import Session

from jobagent.dashboard import (
    BriefingSnapshot,
    DeliveryEvidenceState,
    SqlAlchemyDashboardService,
)
from jobagent.db import Database
from jobagent.db.models import (
    APSchedulerJob,
    DailyReportSnapshot,
    NotificationDelivery,
    PipelineRun,
    PipelineStageRun,
)
from jobagent.jobs import DAILY_PIPELINE_JOB_NAME

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).parents[2]
NOW = datetime(2026, 9, 10, 1, 0, tzinfo=UTC)


def test_dashboard_reads_pre_delivery_schema_and_tracked_delivery() -> None:
    database_url = _test_database_url()
    engine = create_engine(database_url)
    alembic_config = _alembic_config(database_url)
    _reset_test_schema(engine)
    command.upgrade(alembic_config, "0009_pipeline_scheduling")

    try:
        report_id = _seed_pipeline_and_report(engine)
        before = _read_dashboard(database_url)

        assert before.scheduler.present is True
        assert before.scheduler.next_run_at == datetime(2026, 9, 11, 0, 0, tzinfo=UTC)
        assert before.recent_runs[0].status == "succeeded"
        assert [stage.stage for stage in before.recent_runs[0].stages] == [
            "collection",
            "extraction",
            "matching",
            "report",
        ]
        assert before.missing_record_dates == (
            date(2026, 9, 7),
            date(2026, 9, 8),
            date(2026, 9, 9),
            date(2026, 9, 10),
        )
        assert before.latest_report is not None
        assert before.latest_report.snapshot_id == report_id
        assert before.latest_report.item_count == 1
        assert before.latest_report.items[0].organization == "合成单位"
        assert before.delivery.state is DeliveryEvidenceState.UNAVAILABLE_SCHEMA

        command.upgrade(alembic_config, "head")
        with Session(engine) as session:
            session.add(
                NotificationDelivery(
                    report_snapshot_id=report_id,
                    channel="pushplus_wechat",
                    delivery_version="jai-027-v1",
                    message_hash="c" * 64,
                    part_count=1,
                    status="succeeded",
                    started_at=datetime(2026, 9, 10, 1, 1, tzinfo=UTC),
                    finished_at=datetime(2026, 9, 10, 1, 2, tzinfo=UTC),
                )
            )
            session.commit()

        after = _read_dashboard(database_url)
        assert after.delivery.state is DeliveryEvidenceState.SUCCEEDED
        assert after.delivery.channel == "pushplus_wechat"
        assert after.delivery.error_code is None
    finally:
        _reset_test_schema(engine)
        engine.dispose()


def _seed_pipeline_and_report(engine: Engine) -> int:
    scheduled_for = datetime(2026, 9, 6, 0, 0, tzinfo=UTC)
    with Session(engine) as session:
        session.add(
            APSchedulerJob(
                id=DAILY_PIPELINE_JOB_NAME,
                next_run_time=datetime(2026, 9, 11, 0, 0, tzinfo=UTC).timestamp(),
                job_state=b"synthetic",
            )
        )
        run = PipelineRun(
            job_name=DAILY_PIPELINE_JOB_NAME,
            scheduled_for=scheduled_for,
            report_date=date(2026, 9, 6),
            timezone="Asia/Shanghai",
            trigger="makeup",
            status="succeeded",
            started_at=scheduled_for,
            finished_at=datetime(2026, 9, 6, 0, 4, tzinfo=UTC),
        )
        session.add(run)
        session.flush()
        for minute, stage in enumerate(("collection", "extraction", "matching", "report")):
            session.add(
                PipelineStageRun(
                    pipeline_run_id=run.id,
                    stage=stage,
                    attempt=1,
                    status="succeeded",
                    started_at=datetime(2026, 9, 6, 0, minute, tzinfo=UTC),
                    finished_at=datetime(2026, 9, 6, 0, minute + 1, tzinfo=UTC),
                    output={},
                )
            )
        report = DailyReportSnapshot(
            report_date=date(2026, 9, 6),
            timezone="Asia/Shanghai",
            report_version="jai-024-v1",
            input_hash="a" * 64,
            content_hash="b" * 64,
            payload={
                "report_date": "2026-09-06",
                "timezone": "Asia/Shanghai",
                "report_version": "jai-024-v1",
                "input_hash": "a" * 64,
                "sections": [
                    {
                        "group": "priority_applications",
                        "items": [
                            {
                                "position_id": 6,
                                "match_result_id": 6,
                                "organization": "合成单位",
                                "title": "合成岗位",
                                "region": "北京",
                                "deadline": None,
                                "score": 88,
                                "reason": "与偏好匹配。",
                                "risks": [],
                                "source_url": "https://example.invalid/jobs/6",
                            }
                        ],
                    },
                    {"group": "closing_soon", "items": []},
                    {"group": "added_today", "items": []},
                    {"group": "needs_confirmation", "items": []},
                ],
            },
            markdown="# 合成日报\n",
            html="<!doctype html><html><body>合成日报</body></html>",
        )
        session.add(report)
        session.commit()
        return report.id


def _read_dashboard(database_url: URL) -> BriefingSnapshot:
    async def scenario() -> BriefingSnapshot:
        database = Database(database_url.render_as_string(hide_password=False))
        try:
            service = SqlAlchemyDashboardService(
                database.session_factory,
                "Asia/Shanghai",
                8,
                0,
                clock=lambda: NOW,
            )
            return await service.get_briefing()
        finally:
            await database.close()

    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        return runner.run(scenario())


def _test_database_url() -> URL:
    raw_url = os.getenv("JOBAGENT_TEST_DATABASE_URL")
    if raw_url is None:
        pytest.skip("Set JOBAGENT_TEST_DATABASE_URL to run PostgreSQL dashboard tests.")
    database_url = make_url(raw_url)
    if not (database_url.database or "").endswith("_test"):
        pytest.fail("Dashboard tests require a database whose name ends with '_test'.")
    return database_url


def _alembic_config(database_url: URL) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    rendered_url = database_url.render_as_string(hide_password=False).replace("%", "%%")
    config.set_main_option("sqlalchemy.url", rendered_url)
    return config


def _reset_test_schema(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
