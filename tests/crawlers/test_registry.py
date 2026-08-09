"""Checks for explicit source adapter registration and resolution."""

import pytest

from jobagent.core.exceptions import ConfigurationError, PermanentJobAgentError
from jobagent.crawlers import (
    AdapterRegistry,
    CrawlCursor,
    DiscoveredItem,
    RawDocumentInput,
    SourceDefinition,
)


class EmptyAdapter:
    async def discover(self, cursor: CrawlCursor | None) -> list[DiscoveredItem]:
        return []

    async def fetch_detail(self, item: DiscoveredItem) -> RawDocumentInput:
        raise AssertionError("No item should be fetched.")


def _source(adapter: str = "fake") -> SourceDefinition:
    return SourceDefinition(
        id=7,
        name="Fake source",
        base_url="https://example.invalid",
        category="test",
        adapter=adapter,
        enabled=True,
    )


def test_registry_resolves_an_explicit_factory() -> None:
    registry = AdapterRegistry()
    adapter = EmptyAdapter()
    registry.register("fake", lambda source: adapter)

    assert registry.create(_source()) is adapter
    assert registry.names == ("fake",)


def test_registry_rejects_duplicate_and_empty_names() -> None:
    registry = AdapterRegistry()
    registry.register("fake", lambda source: EmptyAdapter())

    with pytest.raises(ConfigurationError) as duplicate_error:
        registry.register("fake", lambda source: EmptyAdapter())
    with pytest.raises(ConfigurationError) as empty_error:
        registry.register("  ", lambda source: EmptyAdapter())

    assert duplicate_error.value.code == "crawler.adapter_duplicate"
    assert empty_error.value.code == "crawler.adapter_name_empty"


def test_registry_reports_an_unknown_adapter_clearly() -> None:
    with pytest.raises(PermanentJobAgentError) as captured_error:
        AdapterRegistry().create(_source("missing"))

    assert captured_error.value.code == "crawler.adapter_not_registered"
    assert captured_error.value.details == {"adapter": "missing", "source_id": 7}
