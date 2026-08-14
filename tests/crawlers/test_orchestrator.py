"""Acceptance checks for common collection batch orchestration."""

import asyncio
from copy import deepcopy
from datetime import UTC, datetime

import pytest

from jobagent.core.exceptions import JsonValue, PermanentJobAgentError
from jobagent.crawlers import (
    AdapterRegistry,
    CollectionOrchestrator,
    CrawlCursor,
    CrawlRunSummary,
    DiscoveredItem,
    HttpCacheValidators,
    RawDocumentInput,
    RawDocumentWriteResult,
    RawDocumentWriteStatus,
    SourceDefinition,
)


class FakeRepository:
    def __init__(
        self,
        source: SourceDefinition | None,
        *,
        previous_runs: tuple[CrawlRunSummary, ...] = (),
    ) -> None:
        self.source = source
        self.previous_runs = {run.run_id: run for run in previous_runs}
        self.started = 0
        self.progress: list[dict[str, JsonValue]] = []
        self.finished: tuple[str, dict[str, JsonValue], str | None] | None = None

    async def get_source(self, source_id: int) -> SourceDefinition | None:
        if self.source is not None and self.source.id == source_id:
            return self.source
        return None

    async def get_run(self, run_id: int) -> CrawlRunSummary | None:
        return self.previous_runs.get(run_id)

    async def start_run(self, source_id: int, stats: dict[str, JsonValue]) -> int:
        self.started += 1
        self.progress.append(deepcopy(stats))
        return 100 + self.started

    async def update_run(self, run_id: int, stats: dict[str, JsonValue]) -> None:
        assert run_id == 100 + self.started
        self.progress.append(deepcopy(stats))

    async def finish_run(
        self,
        run_id: int,
        *,
        status: str,
        stats: dict[str, JsonValue],
        error_message: str | None = None,
    ) -> None:
        assert run_id == 100 + self.started
        self.finished = (status, deepcopy(stats), error_message)


class FakeDocumentRepository:
    def __init__(
        self,
        statuses: dict[str, RawDocumentWriteStatus] | None = None,
        *,
        failing_urls: set[str] | None = None,
    ) -> None:
        self.statuses = statuses or {}
        self.failing_urls = failing_urls or set()
        self.saved_urls: list[str] = []

    async def save(
        self,
        source: SourceDefinition,
        document: RawDocumentInput,
    ) -> RawDocumentWriteResult:
        assert source.id == 7
        self.saved_urls.append(document.url)
        if document.url in self.failing_urls:
            raise RuntimeError("Sensitive database response must not be persisted")
        status = self.statuses.get(document.url, RawDocumentWriteStatus.CREATED)
        return RawDocumentWriteResult(
            document_id=len(self.saved_urls),
            status=status,
            version=1,
            canonical_url=document.url,
            content_hash="a" * 64,
            previous_document_id=None,
        )

    async def get_validators(
        self,
        source: SourceDefinition,
        url: str,
    ) -> HttpCacheValidators | None:
        return None


class CancellingDocumentRepository(FakeDocumentRepository):
    async def save(
        self,
        source: SourceDefinition,
        document: RawDocumentInput,
    ) -> RawDocumentWriteResult:
        raise asyncio.CancelledError


class FakeAdapter:
    def __init__(self, *, failing_urls: set[str] | None = None) -> None:
        self.failing_urls = failing_urls or set()
        self.fetched_urls: list[str] = []
        self.cursors: list[CrawlCursor | None] = []

    async def discover(self, cursor: CrawlCursor | None) -> list[DiscoveredItem]:
        self.cursors.append(cursor)
        return [
            DiscoveredItem(
                f"https://example.invalid/{index}",
                metadata={"title": f"item-{index}"},
            )
            for index in range(1, 4)
        ]

    async def fetch_detail(self, item: DiscoveredItem) -> RawDocumentInput:
        self.fetched_urls.append(item.url)
        if item.url in self.failing_urls:
            raise RuntimeError("Sensitive upstream response must not be persisted")
        return RawDocumentInput(
            url=item.url,
            title=str(item.metadata["title"]),
            raw_text="body",
        )


class FailingDiscoveryAdapter(FakeAdapter):
    async def discover(self, cursor: CrawlCursor | None) -> list[DiscoveredItem]:
        raise RuntimeError("Sensitive discovery response must not be persisted")


def _source(*, adapter: str = "fake", enabled: bool = True) -> SourceDefinition:
    return SourceDefinition(
        id=7,
        name="Fake source",
        base_url="https://example.invalid",
        category="test",
        adapter=adapter,
        enabled=enabled,
    )


def _summary(
    run_id: int,
    *,
    status: str = "partial",
    failures: list[dict[str, JsonValue]] | None = None,
) -> CrawlRunSummary:
    failure_values: list[JsonValue] = []
    if failures:
        failure_values.extend(failures)
    return CrawlRunSummary(
        run_id=run_id,
        source_id=7,
        status=status,
        started_at=datetime(2026, 8, 14, tzinfo=UTC),
        finished_at=datetime(2026, 8, 14, 0, 1, tzinfo=UTC),
        stats={"failures": failure_values},
        error_message=None,
    )


def _orchestrator(
    adapter: FakeAdapter,
    repository: FakeRepository,
    document_repository: FakeDocumentRepository | None = None,
) -> CollectionOrchestrator:
    registry = AdapterRegistry()
    registry.register("fake", lambda source: adapter)
    return CollectionOrchestrator(registry, repository, document_repository)


def test_item_failure_is_isolated_and_run_statistics_are_completed() -> None:
    adapter = FakeAdapter(failing_urls={"https://example.invalid/2"})
    repository = FakeRepository(_source())

    result = asyncio.run(_orchestrator(adapter, repository).run(7, cursor={"page": 2}))

    assert adapter.fetched_urls == [
        "https://example.invalid/1",
        "https://example.invalid/2",
        "https://example.invalid/3",
    ]
    assert [document.url for document in result.documents] == [
        "https://example.invalid/1",
        "https://example.invalid/3",
    ]
    assert result.status == "partial"
    assert result.stats == {
        "discovered": 3,
        "detail_succeeded": 2,
        "detail_failed": 1,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "failed": 1,
        "steps": {
            "discover": {"status": "succeeded", "count": 3, "total": 3},
            "fetch_detail": {"status": "partial", "succeeded": 2, "failed": 1},
            "persist": {"status": "skipped"},
        },
        "failures": [
            {
                "url": "https://example.invalid/2",
                "step": "fetch_detail",
                "code": "crawler.adapter_fetch_detail_failed",
                "message": "Adapter fetch_detail failed with RuntimeError.",
                "retryable": False,
            }
        ],
    }
    assert repository.finished == ("partial", result.stats, None)
    assert len(repository.progress) == 5


def test_persistence_counts_created_updated_and_skipped_documents() -> None:
    adapter = FakeAdapter()
    repository = FakeRepository(_source())
    documents = FakeDocumentRepository(
        {
            "https://example.invalid/1": RawDocumentWriteStatus.CREATED,
            "https://example.invalid/2": RawDocumentWriteStatus.UPDATED,
            "https://example.invalid/3": RawDocumentWriteStatus.UNCHANGED,
        }
    )

    result = asyncio.run(_orchestrator(adapter, repository, documents).run(7))

    assert result.status == "succeeded"
    assert result.stats["created"] == 1
    assert result.stats["updated"] == 1
    assert result.stats["skipped"] == 1
    assert result.stats["failed"] == 0
    assert result.stats["steps"] == {
        "discover": {"status": "succeeded", "count": 3, "total": 3},
        "fetch_detail": {"status": "succeeded", "succeeded": 3, "failed": 0},
        "persist": {
            "status": "succeeded",
            "created": 1,
            "updated": 1,
            "skipped": 1,
            "failed": 0,
        },
    }


def test_persistence_failure_is_isolated_and_safe() -> None:
    adapter = FakeAdapter()
    repository = FakeRepository(_source())
    documents = FakeDocumentRepository(failing_urls={"https://example.invalid/2"})

    result = asyncio.run(_orchestrator(adapter, repository, documents).run(7))

    assert result.status == "partial"
    assert len(result.documents) == 2
    assert result.stats["created"] == 2
    assert result.stats["failed"] == 1
    assert result.failures[0].step == "persist_document"
    assert result.failures[0].code == "crawler.persist_document_failed"
    assert "Sensitive database response" not in str(result.stats)


def test_persistence_cancellation_marks_run_cancelled_and_propagates() -> None:
    repository = FakeRepository(_source())

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            _orchestrator(
                FakeAdapter(),
                repository,
                CancellingDocumentRepository(),
            ).run(7)
        )

    assert repository.finished is not None
    status, stats, error_message = repository.finished
    assert status == "cancelled"
    assert stats["detail_succeeded"] == 1
    assert stats["created"] == 0
    assert error_message == "Crawl was cancelled while persisting a document."


def test_retry_rediscovers_metadata_but_fetches_only_failed_urls() -> None:
    previous = _summary(
        55,
        failures=[
            {
                "url": "https://example.invalid/2",
                "step": "fetch_detail",
                "code": "crawler.adapter_fetch_detail_failed",
                "message": "safe",
                "retryable": False,
            }
        ],
    )
    adapter = FakeAdapter()
    repository = FakeRepository(_source(), previous_runs=(previous,))
    documents = FakeDocumentRepository(
        {"https://example.invalid/2": RawDocumentWriteStatus.UNCHANGED}
    )

    result = asyncio.run(_orchestrator(adapter, repository, documents).retry_failed(55))

    assert adapter.cursors == [None]
    assert adapter.fetched_urls == ["https://example.invalid/2"]
    assert documents.saved_urls == ["https://example.invalid/2"]
    assert result.run_id == 101
    assert result.status == "succeeded"
    assert result.stats["retry_of_run_id"] == 55
    assert result.stats["retry_requested"] == 1
    assert result.stats["discovered_total"] == 3
    assert result.stats["discovered"] == 1
    assert result.stats["skipped"] == 1


@pytest.mark.parametrize(
    ("summary", "expected_code"),
    [
        (_summary(55, status="running"), "crawler.run_not_terminal"),
        (_summary(55, status="succeeded"), "crawler.run_has_no_failed_items"),
    ],
)
def test_retry_rejects_nonterminal_or_successful_runs(
    summary: CrawlRunSummary,
    expected_code: str,
) -> None:
    repository = FakeRepository(_source(), previous_runs=(summary,))

    with pytest.raises(PermanentJobAgentError) as captured_error:
        asyncio.run(_orchestrator(FakeAdapter(), repository).retry_failed(55))

    assert captured_error.value.code == expected_code
    assert repository.started == 0


def test_all_details_succeed_without_persistence() -> None:
    adapter = FakeAdapter()
    repository = FakeRepository(_source())

    result = asyncio.run(_orchestrator(adapter, repository).run(7, cursor={"page": 2}))

    assert result.status == "succeeded"
    assert len(result.documents) == 3
    assert result.failures == ()
    assert repository.finished is not None
    assert repository.finished[0] == "succeeded"


def test_unknown_adapter_fails_before_a_run_is_created() -> None:
    repository = FakeRepository(_source(adapter="missing"))

    with pytest.raises(PermanentJobAgentError) as captured_error:
        asyncio.run(CollectionOrchestrator(AdapterRegistry(), repository).run(7))

    assert captured_error.value.code == "crawler.adapter_not_registered"
    assert repository.started == 0


@pytest.mark.parametrize(
    ("source", "expected_code"),
    [
        (None, "crawler.source_not_found"),
        (_source(enabled=False), "crawler.source_disabled"),
    ],
)
def test_missing_or_disabled_source_fails_before_a_run(
    source: SourceDefinition | None,
    expected_code: str,
) -> None:
    repository = FakeRepository(source)

    with pytest.raises(PermanentJobAgentError) as captured_error:
        asyncio.run(_orchestrator(FakeAdapter(), repository).run(7))

    assert captured_error.value.code == expected_code
    assert repository.started == 0


def test_discovery_failure_marks_the_run_failed_and_reraises() -> None:
    repository = FakeRepository(_source())

    with pytest.raises(RuntimeError, match="Sensitive discovery"):
        asyncio.run(_orchestrator(FailingDiscoveryAdapter(), repository).run(7))

    assert repository.finished is not None
    status, stats, error_message = repository.finished
    assert status == "failed"
    assert error_message == "Adapter discover failed with RuntimeError."
    assert stats["steps"] == {
        "discover": {"status": "failed"},
        "fetch_detail": {"status": "skipped"},
        "persist": {"status": "skipped"},
    }
    assert stats["failed"] == 1
    assert "Sensitive discovery response" not in str(stats)
