"""Preview one manually configured source without database writes."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from jobagent.crawlers.catalog import SourceCatalogEntry, load_source_catalog
from jobagent.crawlers.contracts import SourceDefinition
from jobagent.crawlers.http import HttpSourcePolicy, SourceHttpClient
from jobagent.crawlers.sasac import SasacRecruitmentAdapter

DEFAULT_CATALOG = Path("config/source_catalog.toml")
USER_AGENT = "JOBAGENT/0.1 (+personal recruitment intelligence; low-frequency preview)"


def main() -> int:
    """List configured sources or preview the selected active source."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--source")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--list", action="store_true", dest="list_sources")
    args = parser.parse_args()
    if args.limit <= 0:
        parser.error("--limit must be positive")

    catalog = load_source_catalog(args.catalog)
    if args.list_sources:
        print(
            json.dumps(
                [
                    {
                        "key": entry.key,
                        "name": entry.name,
                        "category": entry.category,
                        "status": entry.implementation_status,
                        "enabled": entry.enabled,
                    }
                    for entry in catalog.entries
                ],
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if not args.source:
        parser.error("--source is required unless --list is used")

    entry = catalog.get(args.source)
    if not entry.runnable:
        parser.error(f"source '{entry.key}' is not active and enabled")
    return asyncio.run(_preview(entry, limit=args.limit))


async def _preview(entry: SourceCatalogEntry, *, limit: int) -> int:
    source = SourceDefinition(
        id=1,
        name=entry.name,
        base_url=entry.base_url,
        category=entry.category,
        adapter=entry.adapter,
        enabled=entry.enabled,
    )
    policy = HttpSourcePolicy(
        source_id=source.id,
        user_agent=USER_AGENT,
        min_interval_seconds=1.0,
        max_concurrency=1,
    )
    async with SourceHttpClient(policy) as client:
        if entry.adapter != "sasac_recruitment":
            raise RuntimeError(f"No preview runner is registered for '{entry.adapter}'.")
        adapter = SasacRecruitmentAdapter(source, entry, client)
        items = tuple(await adapter.discover(None))[:limit]

    print(
        json.dumps(
            {
                "source": entry.key,
                "list_url": entry.list_url,
                "matched": len(items),
                "items": [{"url": item.url, **item.metadata} for item in items],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
