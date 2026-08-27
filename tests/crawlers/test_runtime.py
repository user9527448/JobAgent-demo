"""Checks for explicit manual-run catalog and Adapter wiring."""

import asyncio
from pathlib import Path

import httpx
import pytest

from jobagent.core.exceptions import ConfigurationError
from jobagent.crawlers import (
    HttpSourcePolicy,
    SourceDefinition,
    SourceHttpClient,
    build_adapter_registry,
    load_source_catalog,
    match_catalog_entry,
)

CATALOG_PATH = Path(__file__).parents[2] / "config" / "source_catalog.toml"


@pytest.mark.parametrize(
    "source_key",
    [
        "ncss-jobs",
        "jiangsu-personnel-exam",
        "shanghai-firstjob",
        "shanghai-public-institution",
        "china-mobile-recruitment",
    ],
)
def test_runnable_catalog_sources_have_explicit_manual_wiring(source_key: str) -> None:
    catalog = load_source_catalog(CATALOG_PATH)
    entry = catalog.get(source_key)
    source = SourceDefinition(
        id=7,
        name=entry.name,
        base_url=entry.base_url,
        category=entry.category,
        adapter=entry.adapter,
        enabled=True,
    )
    client = SourceHttpClient(
        HttpSourcePolicy(source_id=7, user_agent="JOBAGENT test"),
        transport=httpx.MockTransport(lambda request: httpx.Response(200, request=request)),
    )
    try:
        matched = match_catalog_entry(catalog, source)
        registry = build_adapter_registry(source, matched, client)

        assert registry.names == (entry.adapter,)
        assert registry.create(source).__class__.__name__.endswith("Adapter")
    finally:
        asyncio.run(client.aclose())


def test_manual_runtime_rejects_database_catalog_mismatch() -> None:
    catalog = load_source_catalog(CATALOG_PATH)
    entry = catalog.get("china-mobile-recruitment")
    source = SourceDefinition(
        id=7,
        name=f"{entry.name} changed",
        base_url=entry.base_url,
        category=entry.category,
        adapter=entry.adapter,
        enabled=True,
    )

    with pytest.raises(ConfigurationError) as captured_error:
        match_catalog_entry(catalog, source)

    assert captured_error.value.code == "crawler.catalog_source_mismatch"
