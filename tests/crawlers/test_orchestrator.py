"""Acceptance checks for common collection batch orchestration."""

import asyncio
from copy import deepcopy

import pytest

from jobagent.core.exceptions import JsonValue, PermanentJobAgentError
from jobagent.crawlers import (
    AdapterRegistry,
    CollectionOrchestrator,
    CrawlCursor,
    DiscoveredItem,
    RawDocumentInput,
    SourceDefinition,
)


class FakeRepository:
    def __init__(self, source: SourceDefinition | None) -> None:
        self.source = source
        self.started = 0
        self.progress: list[dict[str, JsonValue]] = []
        self.finished: tuple[str, dict[str, JsonValue], str | None] | None = None

    async def get_source(self, source_id: int) -> SourceDefinition | None:
        if self.source is not None and self.source.id == source_id:
            return self.source
        return None

    async def start_run(self, source_id: int, stats: dict[str, JsonValue]) -> int:
        self.started += 1
        self.progress.append(deepcopy(stats))
        return 101

    async def update_run(self, run_id: int, stats: dict[str, JsonValue]) -> None:
        assert run_id == 101
        self.progress.append(deepcopy(stats))

    async def finish_run(
        self,
        run_id: int,
        *,
        status: str,
        stats: dict[str, JsonValue],
        error_message: str | None = None,
    ) -> None:
        assert run_id == 101
        self.finished = (status, deepcopy(stats), error_message)


class FakeAdapter:
    def __init__(self, *, failing_urls: set[str] | None = None) -> None:
        self.failing_urls = failing_urls or set()
        self.fetched_urls: list[str] = []

    async def discover(self, cursor: CrawlCursor | None) -> list[DiscoveredItem]:
        assert cursor == {"page": 2}
        return [
            DiscoveredItem("https://example.invalid/1"),
            DiscoveredItem("https://example.invalid/2"),
            DiscoveredItem("https://example.invalid/3"),
        ]

    async def fetch_detail(self, item: DiscoveredItem) -> RawDocumentInput:
        self.fetched_urls.append(item.url)
        if item.url in self.failing_urls:
            raise RuntimeError("Sensitive upstream response must not be persisted")
        return RawDocumentInput(url=item.url, title=item.url.rsplit("/", 1)[-1], raw_text="body")


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


def _orchestrator(adapter: FakeAdapter, repository: FakeRepository) -> CollectionOrchestrator:
    registry = AdapterRegistry()
    registry.register("fake", lambda source: adapter)
    return CollectionOrchestrator(registry, repository)


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
        "steps": {
            "discover": {"status": "succeeded", "count": 3},
            "fetch_detail": {"status": "partial", "succeeded": 2, "failed": 1},
        },
        "failures": [
            {
                "url": "https://example.invalid/2",
                "code": "crawler.adapter_fetch_detail_failed",
                "message": "Adapter fetch_detail failed with RuntimeError.",
                "retryable": False,
            }
        ],
    }
    assert repository.finished == ("partial", result.stats, None)
    assert len(repository.progress) == 5


def test_all_details_succeed() -> None:
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
    source: SourceDefinition | None, expected_code: str
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
    }
    assert "Sensitive discovery response" not in str(stats)
