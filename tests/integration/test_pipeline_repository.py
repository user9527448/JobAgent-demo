"""PostgreSQL acceptance for the JAI-026 run ledger and advisory lock."""

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

from jobagent.db import Database
from jobagent.jobs import (
    PipelineStage,
    PipelineStatus,
    PipelineTrigger,
    SqlAlchemyPipelineLock,
    SqlAlchemyPipelineRepository,
    StageStatus,
)

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).parents[2]
SCHEDULED_FOR = datetime(2026, 9, 6, tzinfo=UTC)


def test_pipeline_ledger_is_idempotent_and_records_recovery() -> None:
    database_url = _test_database_url()
    sync_engine = create_engine(database_url)
    _reset_test_schema(sync_engine)
    command.upgrade(_alembic_config(database_url), "head")

    async def scenario() -> None:
        database = Database(database_url.render_as_string(hide_password=False))
        try:
            repository = SqlAlchemyPipelineRepository(database.session_factory)
            first = await repository.get_or_create(
                job_name="daily",
                scheduled_for=SCHEDULED_FOR,
                report_date=date(2026, 9, 6),
                timezone="Asia/Shanghai",
                trigger=PipelineTrigger.SCHEDULED,
            )
            repeated = await repository.get_or_create(
                job_name="daily",
                scheduled_for=SCHEDULED_FOR,
                report_date=date(2026, 9, 6),
                timezone="Asia/Shanghai",
                trigger=PipelineTrigger.MAKEUP,
            )
            assert repeated.id == first.id
            assert repeated.trigger is PipelineTrigger.SCHEDULED

            attempt = await repository.start_stage(first.id, PipelineStage.COLLECTION)
            assert attempt.attempt == 1
            assert attempt.status is StageStatus.RUNNING
            assert await repository.interrupt_running_stages(first.id) == 1
            statuses = await repository.latest_stage_statuses(first.id)
            assert statuses == {PipelineStage.COLLECTION: StageStatus.INTERRUPTED}

            recovered = await repository.start_stage(first.id, PipelineStage.COLLECTION)
            assert recovered.attempt == 2
            finished = await repository.finish_stage(
                recovered.id,
                status=StageStatus.SUCCEEDED,
                output={"crawl_run_ids": [11, 12]},
            )
            assert finished.output == {"crawl_run_ids": [11, 12]}
            completed = await repository.finish_run(
                first.id,
                status=PipelineStatus.SUCCEEDED,
            )
            assert completed.status is PipelineStatus.SUCCEEDED
            assert completed.finished_at is not None
            assert len(await repository.list_stage_attempts(first.id)) == 2
        finally:
            await database.close()

    try:
        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            runner.run(scenario())
    finally:
        _reset_test_schema(sync_engine)
        sync_engine.dispose()


def test_pipeline_advisory_lock_rejects_concurrent_holder() -> None:
    database_url = _test_database_url()
    sync_engine = create_engine(database_url)
    _reset_test_schema(sync_engine)
    command.upgrade(_alembic_config(database_url), "head")

    async def scenario() -> None:
        database = Database(database_url.render_as_string(hide_password=False))
        try:
            first = SqlAlchemyPipelineLock(database.session_factory)
            second = SqlAlchemyPipelineLock(database.session_factory)
            async with first.acquire() as first_acquired:
                assert first_acquired is True
                async with second.acquire() as second_acquired:
                    assert second_acquired is False
            async with second.acquire() as acquired_after_release:
                assert acquired_after_release is True
        finally:
            await database.close()

    try:
        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            runner.run(scenario())
    finally:
        _reset_test_schema(sync_engine)
        sync_engine.dispose()


def _test_database_url() -> URL:
    raw_url = os.getenv("JOBAGENT_TEST_DATABASE_URL")
    if raw_url is None:
        pytest.skip("Set JOBAGENT_TEST_DATABASE_URL to run PostgreSQL pipeline tests.")
    database_url = make_url(raw_url)
    if not (database_url.database or "").endswith("_test"):
        pytest.fail("Pipeline tests require a database whose name ends with '_test'.")
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
