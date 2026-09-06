"""PostgreSQL acceptance for JAI-026 orchestration, reuse, and restart recovery."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import pytest
from alembic import command
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session

from jobagent.core import Settings
from jobagent.core.exceptions import JsonValue
from jobagent.crawlers import SqlAlchemyCrawlRunRepository
from jobagent.db import Database
from jobagent.db.models import (
    CrawlRun,
    DailyReportSnapshot,
    JobPost,
    MatchResult,
    PipelineRun,
    PipelineStageRun,
    RawDocument,
    Source,
)
from jobagent.jobs import (
    DAILY_PIPELINE_JOB_NAME,
    DispatchStatus,
    PipelineContext,
    PipelineCoordinator,
    PipelineStage,
    PipelineStatus,
    PipelineTrigger,
    ProductionPipelineStages,
    SqlAlchemyPipelineLock,
    SqlAlchemyPipelineRepository,
    StageOutcome,
    StageStatus,
)

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).parents[2]
FIRST_SLOT = datetime(2026, 9, 6, tzinfo=UTC)


class SyntheticCollectionStages:
    """Replace only public-network collection while keeping downstream stages real."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        source_id: int,
        production: ProductionPipelineStages,
    ) -> None:
        self._crawl_runs = SqlAlchemyCrawlRunRepository(session_factory)
        self._source_id = source_id
        self._production = production

    async def run(self, stage: PipelineStage, context: PipelineContext) -> StageOutcome:
        if stage is not PipelineStage.COLLECTION:
            return await self._production.run(stage, context)
        run_id = await self._crawl_runs.start_run(
            self._source_id,
            {"fixture": "jai-026"},
        )
        await self._crawl_runs.finish_run(
            run_id,
            status="succeeded",
            stats={"fixture": "jai-026", "stored_documents": 1},
        )
        return StageOutcome(
            StageStatus.SUCCEEDED,
            {
                "source_count": 1,
                "successful_sources": 1,
                "partial_sources": 0,
                "crawl_run_ids": cast(list[JsonValue], [run_id]),
                "failures": [],
            },
        )


def test_daily_pipeline_closes_reuses_and_recovers_with_postgresql(tmp_path: Path) -> None:
    database_url = _test_database_url()
    sync_engine = create_engine(database_url)
    _reset_test_schema(sync_engine)
    command.upgrade(_alembic_config(database_url), "head")
    source_id = _seed_raw_document(sync_engine)

    async def scenario() -> None:
        rendered_url = database_url.render_as_string(hide_password=False)
        settings = Settings(
            environment="test",
            database_url=SecretStr(rendered_url),
            attachment_storage_path=tmp_path,
            timezone="Asia/Shanghai",
            scheduler_stage_max_attempts=1,
            scheduler_retry_delay_seconds=0,
        )
        database = Database(rendered_url)
        try:
            repository = SqlAlchemyPipelineRepository(database.session_factory)
            coordinator = PipelineCoordinator(
                repository,
                SqlAlchemyPipelineLock(database.session_factory),
                SyntheticCollectionStages(
                    database.session_factory,
                    source_id,
                    ProductionPipelineStages(database.session_factory, settings),
                ),
                timezone=settings.timezone,
            )

            first = await coordinator.execute(FIRST_SLOT, PipelineTrigger.MAKEUP)
            assert first.dispatch_status is DispatchStatus.EXECUTED
            assert first.run is not None and first.run.status is PipelineStatus.SUCCEEDED
            first_attempts = await repository.list_stage_attempts(first.run.id)
            assert [attempt.stage for attempt in first_attempts] == list(PipelineStage)
            assert all(attempt.status is StageStatus.SUCCEEDED for attempt in first_attempts)
            assert first_attempts[0].output["crawl_run_ids"]
            assert first_attempts[1].output["extraction_version"] == "jai-026-v1"
            assert first_attempts[2].output["score_version"]
            assert first_attempts[3].output["report_snapshot_id"]

            repeated = await coordinator.execute(FIRST_SLOT, PipelineTrigger.SCHEDULED)
            assert repeated.dispatch_status is DispatchStatus.REUSED
            assert repeated.run is not None and repeated.run.id == first.run.id

            second_slot = FIRST_SLOT + timedelta(days=1)
            stale = await repository.get_or_create(
                job_name=DAILY_PIPELINE_JOB_NAME,
                scheduled_for=second_slot,
                report_date=second_slot.date(),
                timezone=settings.timezone,
                trigger=PipelineTrigger.SCHEDULED,
            )
            stale_attempt = await repository.start_stage(stale.id, PipelineStage.COLLECTION)
            assert stale_attempt.status is StageStatus.RUNNING

            recovered = await coordinator.execute(second_slot, PipelineTrigger.SCHEDULED)
            assert recovered.dispatch_status is DispatchStatus.EXECUTED
            assert recovered.run is not None
            assert recovered.run.status is PipelineStatus.SUCCEEDED
            recovered_attempts = await repository.list_stage_attempts(stale.id)
            assert recovered_attempts[0].status is StageStatus.INTERRUPTED
            assert recovered_attempts[1].attempt == 2
            assert [item.stage for item in recovered_attempts[1:]] == list(PipelineStage)
        finally:
            await database.close()

    try:
        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            runner.run(scenario())

        with Session(sync_engine) as session:
            assert session.scalar(select(func.count()).select_from(PipelineRun)) == 2
            assert session.scalar(select(func.count()).select_from(PipelineStageRun)) == 9
            assert session.scalar(select(func.count()).select_from(CrawlRun)) == 2
            assert session.scalar(select(func.count()).select_from(JobPost)) == 1
            assert session.scalar(select(func.count()).select_from(MatchResult)) == 2
            assert session.scalar(select(func.count()).select_from(DailyReportSnapshot)) == 2
    finally:
        _reset_test_schema(sync_engine)
        sync_engine.dispose()


def _seed_raw_document(engine: Engine) -> int:
    with Session(engine) as session:
        document = RawDocument(
            source=Source(
                name="JAI-026 scheduled flow source",
                base_url="https://example.invalid",
                category="public_exam",
                adapter="scheduler_test",
            ),
            canonical_url="https://example.invalid/notices/26",
            title="Synthetic scheduled recruitment",
            raw_text=(
                "招聘单位: 测试大学\n"
                "招聘类型: 事业单位\n"
                "地区: 上海\n"
                "报名开始时间: 2026-09-01\n"
                "报名截止时间: 2026-09-10\n"
                "报名链接: https://apply.example.invalid/jobs\n"
                "学历: 本科\n"
                "招聘人数: 3人"
            ),
            fetched_at=FIRST_SLOT,
            content_hash="a" * 64,
        )
        session.add(document)
        session.commit()
        return document.source_id


def _test_database_url() -> URL:
    raw_url = os.getenv("JOBAGENT_TEST_DATABASE_URL")
    if raw_url is None:
        pytest.skip("Set JOBAGENT_TEST_DATABASE_URL to run PostgreSQL scheduling tests.")
    database_url = make_url(raw_url)
    if not (database_url.database or "").endswith("_test"):
        pytest.fail("Scheduling tests require a database whose name ends with '_test'.")
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
