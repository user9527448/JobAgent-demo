"""Common batch orchestration with observable, item-isolated execution."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence

from jobagent.core.exceptions import JobAgentError, JsonValue, PermanentJobAgentError
from jobagent.core.logging import bind_log_context, get_logger
from jobagent.crawlers.contracts import (
    CrawlBatchResult,
    CrawlCursor,
    CrawlItemFailure,
    DiscoveredItem,
    RawDocumentInput,
)
from jobagent.crawlers.registry import AdapterRegistry
from jobagent.crawlers.repository import CrawlRunRepository

logger = get_logger(__name__)


class CollectionOrchestrator:
    """Run source-specific adapters inside one shared observable batch flow."""

    def __init__(self, registry: AdapterRegistry, repository: CrawlRunRepository) -> None:
        self._registry = registry
        self._repository = repository

    async def run(
        self,
        source_id: int,
        *,
        cursor: CrawlCursor | None = None,
    ) -> CrawlBatchResult:
        """Discover and fetch a source while isolating individual detail failures."""
        source = await self._repository.get_source(source_id)
        if source is None:
            raise PermanentJobAgentError(
                f"Source {source_id} does not exist.",
                code="crawler.source_not_found",
                details={"source_id": source_id},
            )
        if not source.enabled:
            raise PermanentJobAgentError(
                f"Source {source_id} is disabled.",
                code="crawler.source_disabled",
                details={"source_id": source_id},
            )

        adapter = self._registry.create(source)
        stats = _initial_stats()
        run_id = await self._repository.start_run(source_id, stats)

        with bind_log_context(source_id=source_id, crawl_run_id=run_id):
            logger.info("crawl_run.started", extra={"adapter": source.adapter})
            try:
                items = tuple(await adapter.discover(cursor))
            except asyncio.CancelledError:
                _set_discovery_status(stats, "cancelled")
                await self._repository.finish_run(
                    run_id,
                    status="cancelled",
                    stats=stats,
                    error_message="Crawl was cancelled during discovery.",
                )
                raise
            except Exception as error:
                failure = _adapter_failure("", error, step="discover")
                _set_discovery_status(stats, "failed")
                stats["failures"] = [failure.to_dict()]
                await self._repository.finish_run(
                    run_id,
                    status="failed",
                    stats=stats,
                    error_message=failure.message,
                )
                logger.error(
                    "crawl_run.discovery_failed",
                    extra={"error_code": failure.code, "error_type": type(error).__name__},
                )
                raise

            _record_discovery(stats, len(items))
            await self._repository.update_run(run_id, stats)
            return await self._fetch_items(run_id, source_id, adapter.fetch_detail, items, stats)

    async def _fetch_items(
        self,
        run_id: int,
        source_id: int,
        fetch_detail: Callable[[DiscoveredItem], Awaitable[RawDocumentInput]],
        items: Sequence[DiscoveredItem],
        stats: dict[str, JsonValue],
    ) -> CrawlBatchResult:
        documents: list[RawDocumentInput] = []
        failures: list[CrawlItemFailure] = []

        for item in items:
            try:
                document = await fetch_detail(item)
            except asyncio.CancelledError:
                _record_fetch_status(stats, documents, failures, "cancelled")
                await self._repository.finish_run(
                    run_id,
                    status="cancelled",
                    stats=stats,
                    error_message="Crawl was cancelled while fetching details.",
                )
                raise
            except Exception as error:
                failure = _adapter_failure(item.url, error, step="fetch_detail")
                failures.append(failure)
                logger.warning(
                    "crawl_run.item_failed",
                    extra={
                        "item_url": item.url,
                        "error_code": failure.code,
                        "error_type": type(error).__name__,
                    },
                )
            else:
                documents.append(document)

            _record_fetch_status(stats, documents, failures, "running")
            await self._repository.update_run(run_id, stats)

        status = _terminal_status(documents, failures)
        _record_fetch_status(stats, documents, failures, status)
        await self._repository.finish_run(run_id, status=status, stats=stats)
        logger.info("crawl_run.finished", extra={"status": status, "stats": stats})
        return CrawlBatchResult(
            run_id=run_id,
            source_id=source_id,
            status=status,
            documents=tuple(documents),
            failures=tuple(failures),
            stats=stats,
        )


def _initial_stats() -> dict[str, JsonValue]:
    return {
        "discovered": 0,
        "detail_succeeded": 0,
        "detail_failed": 0,
        "steps": {
            "discover": {"status": "running"},
            "fetch_detail": {"status": "pending"},
        },
        "failures": [],
    }


def _record_discovery(stats: dict[str, JsonValue], discovered: int) -> None:
    stats["discovered"] = discovered
    stats["steps"] = {
        "discover": {"status": "succeeded", "count": discovered},
        "fetch_detail": {"status": "running"},
    }


def _set_discovery_status(stats: dict[str, JsonValue], status: str) -> None:
    stats["steps"] = {
        "discover": {"status": status},
        "fetch_detail": {"status": "skipped"},
    }


def _record_fetch_status(
    stats: dict[str, JsonValue],
    documents: Sequence[RawDocumentInput],
    failures: Sequence[CrawlItemFailure],
    status: str,
) -> None:
    stats["detail_succeeded"] = len(documents)
    stats["detail_failed"] = len(failures)
    stats["failures"] = [failure.to_dict() for failure in failures]
    stats["steps"] = {
        "discover": {"status": "succeeded", "count": stats["discovered"]},
        "fetch_detail": {
            "status": status,
            "succeeded": len(documents),
            "failed": len(failures),
        },
    }


def _terminal_status(
    documents: Sequence[RawDocumentInput], failures: Sequence[CrawlItemFailure]
) -> str:
    if not failures:
        return "succeeded"
    if documents:
        return "partial"
    return "failed"


def _adapter_failure(url: str, error: Exception, *, step: str) -> CrawlItemFailure:
    if isinstance(error, JobAgentError):
        return CrawlItemFailure(
            url=url,
            code=error.code,
            message=error.message,
            retryable=error.retryable,
        )
    return CrawlItemFailure(
        url=url,
        code=f"crawler.adapter_{step}_failed",
        message=f"Adapter {step} failed with {type(error).__name__}.",
        retryable=False,
    )
