"""PostgreSQL acceptance check for persisted JAI-007 crawl progress."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.orm import Session

from jobagent.core.exceptions import JsonValue
from jobagent.crawlers import SqlAlchemyCrawlRunRepository
from jobagent.db.database import Database
from jobagent.db.models import CrawlRun, Source

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).parents[2]


def test_crawl_run_repository_persists_source_progress_and_completion() -> None:
    database_url = _test_database_url()
    engine = create_engine(database_url)
    alembic_config = _alembic_config(database_url)
    _reset_test_schema(engine)

    try:
        command.upgrade(alembic_config, "head")
        with Session(engine) as session:
            source = Source(
                name="JAI-007 fake source",
                base_url="https://example.invalid",
                category="test",
                adapter="fake",
            )
            session.add(source)
            session.commit()
            source_id = source.id

        initial_stats: dict[str, JsonValue] = {"discovered": 0}
        completed_stats: dict[str, JsonValue] = {
            "discovered": 2,
            "detail_succeeded": 1,
            "detail_failed": 1,
        }

        async def verify_repository() -> int:
            database = Database(database_url.render_as_string(hide_password=False))
            repository = SqlAlchemyCrawlRunRepository(database.session_factory)
            try:
                loaded_source = await repository.get_source(source_id)
                assert loaded_source is not None
                assert loaded_source.adapter == "fake"

                run_id = await repository.start_run(source_id, initial_stats)
                await repository.update_run(run_id, completed_stats)
                await repository.finish_run(
                    run_id,
                    status="partial",
                    stats=completed_stats,
                    error_message="One item failed safely.",
                )
                return run_id
            finally:
                await database.close()

        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            run_id = runner.run(verify_repository())

        with Session(engine) as session:
            run = session.scalar(select(CrawlRun).where(CrawlRun.id == run_id))
            assert run is not None
            assert run.status == "partial"
            assert run.stats == completed_stats
            assert run.error_message == "One item failed safely."
            assert run.finished_at is not None
    finally:
        command.downgrade(alembic_config, "base")
        engine.dispose()


def _test_database_url() -> URL:
    raw_url = os.getenv("JOBAGENT_TEST_DATABASE_URL")
    if raw_url is None:
        pytest.skip("Set JOBAGENT_TEST_DATABASE_URL to run PostgreSQL repository tests.")
    database_url = make_url(raw_url)
    if not (database_url.database or "").endswith("_test"):
        pytest.fail("Repository tests require a database whose name ends with '_test'.")
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
