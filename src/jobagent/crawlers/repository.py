"""Persistence boundary and PostgreSQL implementation for collection runs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobagent.core.exceptions import JsonValue, PermanentJobAgentError, TransientJobAgentError
from jobagent.crawlers.contracts import CrawlRunSummary, SourceDefinition
from jobagent.db.models import CrawlRun, Source


class CrawlRunRepository(Protocol):
    """Minimal state operations required by the collection orchestrator."""

    async def get_source(self, source_id: int) -> SourceDefinition | None:
        """Return the requested source configuration when it exists."""
        ...

    async def get_run(self, run_id: int) -> CrawlRunSummary | None:
        """Return one persisted run summary when it exists."""
        ...

    async def start_run(self, source_id: int, stats: dict[str, JsonValue]) -> int:
        """Create a running crawl record and return its identifier."""
        ...

    async def update_run(self, run_id: int, stats: dict[str, JsonValue]) -> None:
        """Persist progress while a batch is still running."""
        ...

    async def finish_run(
        self,
        run_id: int,
        *,
        status: str,
        stats: dict[str, JsonValue],
        error_message: str | None = None,
    ) -> None:
        """Persist a terminal status and completion instant."""
        ...


class SqlAlchemyCrawlRunRepository:
    """Store source lookups and crawl progress through short transactions."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_source(self, source_id: int) -> SourceDefinition | None:
        try:
            async with self._session_factory() as session:
                source = await session.get(Source, source_id)
                if source is None:
                    return None
                return SourceDefinition(
                    id=source.id,
                    name=source.name,
                    base_url=source.base_url,
                    category=source.category,
                    adapter=source.adapter,
                    enabled=source.enabled,
                )
        except SQLAlchemyError as error:
            raise _database_error("load source configuration", error) from error

    async def get_run(self, run_id: int) -> CrawlRunSummary | None:
        try:
            async with self._session_factory() as session:
                run = await session.get(CrawlRun, run_id)
                if run is None:
                    return None
                return CrawlRunSummary(
                    run_id=run.id,
                    source_id=run.source_id,
                    status=run.status,
                    started_at=run.started_at,
                    finished_at=run.finished_at,
                    stats=run.stats,
                    error_message=run.error_message,
                )
        except SQLAlchemyError as error:
            raise _database_error("load crawl run", error) from error

    async def start_run(self, source_id: int, stats: dict[str, JsonValue]) -> int:
        run = CrawlRun(
            source_id=source_id,
            status="running",
            started_at=datetime.now(UTC),
            stats=stats,
        )
        try:
            async with self._session_factory() as session:
                session.add(run)
                await session.commit()
                return run.id
        except SQLAlchemyError as error:
            raise _database_error("start crawl run", error) from error

    async def update_run(self, run_id: int, stats: dict[str, JsonValue]) -> None:
        try:
            async with self._session_factory() as session:
                run = await _require_run(session, run_id)
                run.stats = stats
                await session.commit()
        except SQLAlchemyError as error:
            raise _database_error("update crawl run", error) from error

    async def finish_run(
        self,
        run_id: int,
        *,
        status: str,
        stats: dict[str, JsonValue],
        error_message: str | None = None,
    ) -> None:
        try:
            async with self._session_factory() as session:
                run = await _require_run(session, run_id)
                run.status = status
                run.stats = stats
                run.error_message = error_message
                run.finished_at = datetime.now(UTC)
                await session.commit()
        except SQLAlchemyError as error:
            raise _database_error("finish crawl run", error) from error


async def _require_run(session: AsyncSession, run_id: int) -> CrawlRun:
    run = await session.get(CrawlRun, run_id)
    if run is None:
        raise PermanentJobAgentError(
            f"Crawl run {run_id} does not exist.",
            code="crawler.run_not_found",
            details={"run_id": run_id},
        )
    return run


def _database_error(operation: str, error: SQLAlchemyError) -> TransientJobAgentError:
    return TransientJobAgentError(
        f"Database could not {operation}.",
        code="database.crawl_run_unavailable",
        details={"error_type": type(error).__name__},
    )
