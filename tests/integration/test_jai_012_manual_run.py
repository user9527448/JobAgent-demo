"""PostgreSQL acceptance for JAI-012 manual runs and failed-item retries."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.orm import Session

from jobagent.crawlers import (
    AdapterRegistry,
    CollectionOrchestrator,
    CrawlCursor,
    DiscoveredItem,
    RawDocumentInput,
    SqlAlchemyCrawlRunRepository,
    SqlAlchemyRawDocumentRepository,
)
from jobagent.db.database import Database
from jobagent.db.models import CrawlRun, RawDocument, Source

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).parents[2]


class RetryAdapter:
    """Offline Adapter whose one detail can fail before succeeding on retry."""

    def __init__(self) -> None:
        self.failing_urls = {"https://example.invalid/jobs/2"}
        self.fetched_urls: list[str] = []

    async def discover(self, cursor: CrawlCursor | None) -> tuple[DiscoveredItem, ...]:
        assert cursor is None
        return tuple(
            DiscoveredItem(
                f"https://example.invalid/jobs/{index}",
                metadata={"title": f"Job {index}"},
            )
            for index in range(1, 4)
        )

    async def fetch_detail(self, item: DiscoveredItem) -> RawDocumentInput:
        self.fetched_urls.append(item.url)
        if item.url in self.failing_urls:
            raise RuntimeError("fixture failure")
        return RawDocumentInput(
            url=item.url,
            title=str(item.metadata["title"]),
            raw_text=f"stable body for {item.url}",
        )


def test_manual_retry_fetches_only_failures_and_remains_idempotent() -> None:
    database_url = _test_database_url()
    engine = create_engine(database_url)
    alembic_config = _alembic_config(database_url)
    _reset_test_schema(engine)

    try:
        command.upgrade(alembic_config, "head")
        with Session(engine) as session:
            source = Source(
                name="JAI-012 offline source",
                base_url="https://example.invalid",
                category="test",
                adapter="retry_fixture",
            )
            session.add(source)
            session.commit()
            source_id = source.id

        adapter = RetryAdapter()

        async def verify_runs() -> tuple[int, int, int]:
            database = Database(database_url.render_as_string(hide_password=False))
            run_repository = SqlAlchemyCrawlRunRepository(database.session_factory)
            document_repository = SqlAlchemyRawDocumentRepository(database.session_factory)
            registry = AdapterRegistry()
            registry.register("retry_fixture", lambda source: adapter)
            orchestrator = CollectionOrchestrator(
                registry,
                run_repository,
                document_repository,
            )
            try:
                first = await orchestrator.run(source_id)
                assert first.status == "partial"
                assert first.stats["created"] == 2
                assert first.stats["failed"] == 1

                adapter.failing_urls.clear()
                adapter.fetched_urls.clear()
                retry = await orchestrator.retry_failed(first.run_id)
                assert adapter.fetched_urls == ["https://example.invalid/jobs/2"]
                assert retry.status == "succeeded"
                assert retry.stats["created"] == 1
                assert retry.stats["retry_of_run_id"] == first.run_id

                adapter.fetched_urls.clear()
                repeated = await orchestrator.retry_failed(first.run_id)
                assert adapter.fetched_urls == ["https://example.invalid/jobs/2"]
                assert repeated.status == "succeeded"
                assert repeated.stats["created"] == 0
                assert repeated.stats["skipped"] == 1

                summary = await run_repository.get_run(retry.run_id)
                assert summary is not None
                assert summary.failures == ()
                return first.run_id, retry.run_id, repeated.run_id
            finally:
                await database.close()

        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            run_ids = runner.run(verify_runs())

        with Session(engine) as session:
            assert session.scalar(select(func.count()).select_from(RawDocument)) == 3
            persisted_runs = tuple(session.scalars(select(CrawlRun).order_by(CrawlRun.id)).all())
            assert tuple(run.id for run in persisted_runs) == run_ids
            assert tuple(run.status for run in persisted_runs) == (
                "partial",
                "succeeded",
                "succeeded",
            )
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
