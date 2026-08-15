"""Common batch orchestration with observable, item-isolated execution."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterable, Sequence

from jobagent.core.exceptions import JobAgentError, JsonValue, PermanentJobAgentError
from jobagent.core.logging import bind_log_context, get_logger
from jobagent.crawlers.contracts import (
    CrawlBatchResult,
    CrawlCursor,
    CrawlItemFailure,
    DiscoveredItem,
    RawDocumentInput,
    SourceDefinition,
)
from jobagent.crawlers.documents import RawDocumentRepository, RawDocumentWriteStatus
from jobagent.crawlers.registry import AdapterRegistry
from jobagent.crawlers.repository import CrawlRunRepository

logger = get_logger(__name__)

_TERMINAL_RUN_STATUSES = frozenset({"succeeded", "partial", "failed", "cancelled"})


class CollectionOrchestrator:
    """Run source adapters, persist raw documents, and expose retryable runs."""

    def __init__(
        self,
        registry: AdapterRegistry,
        repository: CrawlRunRepository,
        document_repository: RawDocumentRepository | None = None,
    ) -> None:
        self._registry = registry
        self._repository = repository
        self._document_repository = document_repository

    async def run(
        self,
        source_id: int,
        *,
        cursor: CrawlCursor | None = None,
        retry_of_run_id: int | None = None,
        retry_urls: Sequence[str] | None = None,
    ) -> CrawlBatchResult:
        """Run one source, optionally limiting detail work to prior failed URLs."""
        source = await self._require_enabled_source(source_id)
        adapter = self._registry.create(source)
        requested_retry_urls = _unique_nonempty_urls(retry_urls or ())
        stats = _initial_stats(
            persistence_enabled=self._document_repository is not None,
            retry_of_run_id=retry_of_run_id,
            retry_requested=len(requested_retry_urls),
        )
        run_id = await self._repository.start_run(source_id, stats)

        with bind_log_context(source_id=source_id, crawl_run_id=run_id):
            logger.info(
                "crawl_run.started",
                extra={"adapter": source.adapter, "retry_of_run_id": retry_of_run_id},
            )
            try:
                discovered_items = tuple(await adapter.discover(cursor))
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
                failure = _operation_failure("", error, step="discover")
                _set_discovery_status(stats, "failed")
                stats["failed"] = 1
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

            items = discovered_items
            initial_failures: tuple[CrawlItemFailure, ...] = ()
            if requested_retry_urls:
                items, initial_failures = _select_retry_items(
                    discovered_items,
                    requested_retry_urls,
                )
            _record_discovery(
                stats,
                len(items),
                total_discovered=len(discovered_items),
            )
            await self._repository.update_run(run_id, stats)
            return await self._fetch_items(
                run_id,
                source,
                adapter.fetch_detail,
                items,
                stats,
                initial_failures=initial_failures,
            )

    async def retry_failed(self, run_id: int) -> CrawlBatchResult:
        """Create a new run that fetches only failed URLs from a terminal run."""
        previous = await self._repository.get_run(run_id)
        if previous is None:
            raise PermanentJobAgentError(
                f"Crawl run {run_id} does not exist.",
                code="crawler.run_not_found",
                details={"run_id": run_id},
            )
        if previous.status not in _TERMINAL_RUN_STATUSES:
            raise PermanentJobAgentError(
                f"Crawl run {run_id} is not terminal.",
                code="crawler.run_not_terminal",
                details={"run_id": run_id, "status": previous.status},
            )
        retry_urls = _unique_nonempty_urls(
            failure.url for failure in previous.failures if failure.url
        )
        if not retry_urls:
            raise PermanentJobAgentError(
                f"Crawl run {run_id} has no failed detail items to retry.",
                code="crawler.run_has_no_failed_items",
                details={"run_id": run_id},
            )
        return await self.run(
            previous.source_id,
            retry_of_run_id=run_id,
            retry_urls=retry_urls,
        )

    async def _require_enabled_source(self, source_id: int) -> SourceDefinition:
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
        return source

    async def _fetch_items(
        self,
        run_id: int,
        source: SourceDefinition,
        fetch_detail: Callable[[DiscoveredItem], Awaitable[RawDocumentInput]],
        items: Sequence[DiscoveredItem],
        stats: dict[str, JsonValue],
        *,
        initial_failures: Sequence[CrawlItemFailure] = (),
    ) -> CrawlBatchResult:
        documents: list[RawDocumentInput] = []
        failures = list(initial_failures)
        detail_succeeded = 0
        detail_failed = 0
        persistence_failed = 0
        writes = {"created": 0, "updated": 0, "skipped": 0}

        for item in items:
            try:
                document = await fetch_detail(item)
            except asyncio.CancelledError:
                _record_execution_status(
                    stats,
                    detail_succeeded=detail_succeeded,
                    detail_failed=detail_failed,
                    persistence_failed=persistence_failed,
                    writes=writes,
                    failures=failures,
                    status="cancelled",
                    persistence_enabled=self._document_repository is not None,
                )
                await self._repository.finish_run(
                    run_id,
                    status="cancelled",
                    stats=stats,
                    error_message="Crawl was cancelled while fetching details.",
                )
                raise
            except Exception as error:
                detail_failed += 1
                failure = _operation_failure(item.url, error, step="fetch_detail")
                failures.append(failure)
                logger.warning(
                    "crawl_run.item_failed",
                    extra={
                        "item_url": item.url,
                        "step": failure.step,
                        "error_code": failure.code,
                        "error_type": type(error).__name__,
                    },
                )
            else:
                detail_succeeded += 1
                if self._document_repository is None:
                    documents.append(document)
                else:
                    try:
                        write_result = await self._document_repository.save(source, document)
                    except asyncio.CancelledError:
                        _record_execution_status(
                            stats,
                            detail_succeeded=detail_succeeded,
                            detail_failed=detail_failed,
                            persistence_failed=persistence_failed,
                            writes=writes,
                            failures=failures,
                            status="cancelled",
                            persistence_enabled=True,
                        )
                        await self._repository.finish_run(
                            run_id,
                            status="cancelled",
                            stats=stats,
                            error_message="Crawl was cancelled while persisting a document.",
                        )
                        raise
                    except Exception as error:
                        persistence_failed += 1
                        failure = _operation_failure(
                            item.url,
                            error,
                            step="persist_document",
                        )
                        failures.append(failure)
                        logger.warning(
                            "crawl_run.item_failed",
                            extra={
                                "item_url": item.url,
                                "step": failure.step,
                                "error_code": failure.code,
                                "error_type": type(error).__name__,
                            },
                        )
                    else:
                        writes[_write_counter(write_result.status)] += 1
                        documents.append(document)

            _record_execution_status(
                stats,
                detail_succeeded=detail_succeeded,
                detail_failed=detail_failed,
                persistence_failed=persistence_failed,
                writes=writes,
                failures=failures,
                status="running",
                persistence_enabled=self._document_repository is not None,
            )
            await self._repository.update_run(run_id, stats)

        status = _terminal_status(documents, failures)
        _record_execution_status(
            stats,
            detail_succeeded=detail_succeeded,
            detail_failed=detail_failed,
            persistence_failed=persistence_failed,
            writes=writes,
            failures=failures,
            status=status,
            persistence_enabled=self._document_repository is not None,
        )
        await self._repository.finish_run(run_id, status=status, stats=stats)
        logger.info("crawl_run.finished", extra={"status": status, "stats": stats})
        return CrawlBatchResult(
            run_id=run_id,
            source_id=source.id,
            status=status,
            documents=tuple(documents),
            failures=tuple(failures),
            stats=stats,
        )


def _initial_stats(
    *,
    persistence_enabled: bool,
    retry_of_run_id: int | None,
    retry_requested: int,
) -> dict[str, JsonValue]:
    stats: dict[str, JsonValue] = {
        "discovered": 0,
        "detail_succeeded": 0,
        "detail_failed": 0,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "failed": 0,
        "steps": {
            "discover": {"status": "running"},
            "fetch_detail": {"status": "pending"},
            "persist": {"status": "pending" if persistence_enabled else "skipped"},
        },
        "failures": [],
    }
    if retry_of_run_id is not None:
        stats["retry_of_run_id"] = retry_of_run_id
        stats["retry_requested"] = retry_requested
    return stats


def _record_discovery(
    stats: dict[str, JsonValue],
    discovered: int,
    *,
    total_discovered: int,
) -> None:
    stats["discovered"] = discovered
    if "retry_of_run_id" in stats:
        stats["discovered_total"] = total_discovered
    persist_step = _persist_step(stats)
    stats["steps"] = {
        "discover": {
            "status": "succeeded",
            "count": discovered,
            "total": total_discovered,
        },
        "fetch_detail": {"status": "running"},
        "persist": persist_step,
    }


def _set_discovery_status(stats: dict[str, JsonValue], status: str) -> None:
    stats["steps"] = {
        "discover": {"status": status},
        "fetch_detail": {"status": "skipped"},
        "persist": {"status": "skipped"},
    }


def _record_execution_status(
    stats: dict[str, JsonValue],
    *,
    detail_succeeded: int,
    detail_failed: int,
    persistence_failed: int,
    writes: dict[str, int],
    failures: Sequence[CrawlItemFailure],
    status: str,
    persistence_enabled: bool,
) -> None:
    stats["detail_succeeded"] = detail_succeeded
    stats["detail_failed"] = detail_failed
    stats["created"] = writes["created"]
    stats["updated"] = writes["updated"]
    stats["skipped"] = writes["skipped"]
    stats["failed"] = len(failures)
    stats["failures"] = [failure.to_dict() for failure in failures]
    fetch_status = (
        "running"
        if status == "running"
        else _step_status(
            detail_succeeded,
            detail_failed,
        )
    )
    if not persistence_enabled:
        persist_step: dict[str, JsonValue] = {"status": "skipped"}
    else:
        persisted = sum(writes.values())
        persist_step = {
            "status": (
                "running" if status == "running" else _step_status(persisted, persistence_failed)
            ),
            "created": writes["created"],
            "updated": writes["updated"],
            "skipped": writes["skipped"],
            "failed": persistence_failed,
        }
    stats["steps"] = {
        "discover": _discover_step(stats),
        "fetch_detail": {
            "status": fetch_status,
            "succeeded": detail_succeeded,
            "failed": detail_failed,
        },
        "persist": persist_step,
    }


def _discover_step(stats: dict[str, JsonValue]) -> dict[str, JsonValue]:
    steps = stats.get("steps")
    if isinstance(steps, dict):
        discover = steps.get("discover")
        if isinstance(discover, dict):
            return discover
    return {"status": "unknown"}


def _persist_step(stats: dict[str, JsonValue]) -> dict[str, JsonValue]:
    steps = stats.get("steps")
    if isinstance(steps, dict):
        persist = steps.get("persist")
        if isinstance(persist, dict):
            return persist
    return {"status": "skipped"}


def _terminal_status(
    documents: Sequence[RawDocumentInput], failures: Sequence[CrawlItemFailure]
) -> str:
    if not failures:
        return "succeeded"
    if documents:
        return "partial"
    return "failed"


def _step_status(succeeded: int, failed: int) -> str:
    if failed == 0:
        return "succeeded"
    if succeeded:
        return "partial"
    return "failed"


def _operation_failure(url: str, error: Exception, *, step: str) -> CrawlItemFailure:
    if isinstance(error, JobAgentError):
        return CrawlItemFailure(
            url=url,
            step=step,
            code=error.code,
            message=error.message,
            retryable=error.retryable,
        )
    adapter_step = step in {"discover", "fetch_detail"}
    return CrawlItemFailure(
        url=url,
        step=step,
        code=(f"crawler.adapter_{step}_failed" if adapter_step else f"crawler.{step}_failed"),
        message=(
            f"Adapter {step} failed with {type(error).__name__}."
            if adapter_step
            else f"Collection step {step} failed with {type(error).__name__}."
        ),
        retryable=False,
    )


def _select_retry_items(
    discovered: Sequence[DiscoveredItem],
    requested_urls: Sequence[str],
) -> tuple[tuple[DiscoveredItem, ...], tuple[CrawlItemFailure, ...]]:
    by_url = {item.url: item for item in discovered}
    selected: list[DiscoveredItem] = []
    failures: list[CrawlItemFailure] = []
    for url in requested_urls:
        item = by_url.get(url)
        if item is None:
            failures.append(
                CrawlItemFailure(
                    url=url,
                    step="retry_filter",
                    code="crawler.retry_item_not_discovered",
                    message="Previously failed item was not rediscovered.",
                    retryable=True,
                )
            )
        else:
            selected.append(item)
    return tuple(selected), tuple(failures)


def _unique_nonempty_urls(urls: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(url.strip() for url in urls if isinstance(url, str) and url.strip()))


def _write_counter(status: RawDocumentWriteStatus) -> str:
    if status is RawDocumentWriteStatus.CREATED:
        return "created"
    if status is RawDocumentWriteStatus.UPDATED:
        return "updated"
    return "skipped"
