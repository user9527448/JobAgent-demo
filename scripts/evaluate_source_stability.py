"""Run one bounded, read-only daily stability observation for active sources."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from jobagent.core import JobAgentError
from jobagent.core.exceptions import JsonValue
from jobagent.crawlers import (
    HttpSourcePolicy,
    SourceDefinition,
    SourceHttpClient,
    build_adapter_registry,
    load_source_catalog,
)
from jobagent.crawlers.contracts import RawDocumentInput
from jobagent.crawlers.stability import evaluate_source_stability

DEFAULT_CATALOG = Path("config/source_catalog.toml")
USER_AGENT = "JOBAGENT/0.1 (+personal recruitment intelligence; bounded stability check)"
_SHANGHAI = ZoneInfo("Asia/Shanghai")


def main() -> int:
    """Print one stable JSON report; never persist pages or runtime output."""
    _configure_stdout()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--source", action="append", dest="sources")
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.limit <= 10:
        parser.error("--limit must be between 1 and 10")
    try:
        report = asyncio.run(_evaluate(args.catalog, args.sources, args.limit))
    except JobAgentError as error:
        print(json.dumps(error.to_dict(), ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["successful_source_runs"] == report["source_count"] else 1


async def _evaluate(
    catalog_path: Path,
    selected_keys: list[str] | None,
    limit: int,
) -> dict[str, object]:
    catalog = load_source_catalog(catalog_path)
    entries = (
        tuple(catalog.get(key) for key in selected_keys)
        if selected_keys
        else catalog.runnable_entries()
    )
    if any(not entry.runnable for entry in entries):
        raise ValueError("Stability observations require active and enabled sources.")

    metrics: list[dict[str, object]] = []
    total_attempted = 0
    total_succeeded = 0
    total_failed = 0
    total_duplicates = 0
    total_complete = 0
    total_possible = 0
    successful_source_runs = 0
    for source_id, entry in enumerate(entries, start=1):
        source = SourceDefinition(
            id=source_id,
            name=entry.name,
            base_url=entry.base_url,
            category=entry.category,
            adapter=entry.adapter,
            enabled=True,
        )
        policy = HttpSourcePolicy(
            source_id=source_id,
            user_agent=USER_AGENT,
            min_interval_seconds=1.0,
            max_concurrency=1,
        )
        documents: list[RawDocumentInput] = []
        failures: list[dict[str, JsonValue]] = []
        async with SourceHttpClient(policy) as client:
            adapter = build_adapter_registry(source, entry, client).create(source)
            try:
                items = tuple(await adapter.discover(None))[:limit]
            except JobAgentError as error:
                items = ()
                failures.append(error.to_dict())
                discovery_succeeded = False
            except Exception as error:  # defensive isolation for one live discovery
                items = ()
                failures.append(_unexpected_failure(error, step="discover"))
                discovery_succeeded = False
            else:
                discovery_succeeded = True
                for item in items:
                    try:
                        documents.append(await adapter.fetch_detail(item))
                    except JobAgentError as error:
                        failures.append(error.to_dict())
                    except Exception as error:  # defensive isolation for one live detail
                        failures.append(_unexpected_failure(error, step="fetch_detail"))
        detail_failures = len(items) - len(documents)
        result = evaluate_source_stability(
            entry.key,
            attempted=len(items),
            documents=tuple(documents),
            failed=detail_failures,
        )
        rendered = result.to_dict()
        status = (
            "failed" if not discovery_succeeded else "partial" if detail_failures else "succeeded"
        )
        rendered["status"] = status
        rendered["failures"] = failures
        metrics.append(rendered)
        successful_source_runs += int(status == "succeeded")
        total_attempted += result.attempted
        total_succeeded += result.succeeded
        total_failed += result.failed
        total_duplicates += result.duplicates
        total_complete += result.complete_core_fields
        total_possible += result.possible_core_fields

    return {
        "observation_date": datetime.now(_SHANGHAI).date().isoformat(),
        "source_count": len(metrics),
        "successful_source_runs": successful_source_runs,
        "source_success_rate": _rate(successful_source_runs, len(metrics)),
        "limit_per_source": limit,
        "attempted_details": total_attempted,
        "succeeded_details": total_succeeded,
        "failed_details": total_failed,
        "success_rate": _rate(total_succeeded, total_attempted),
        "duplicates": total_duplicates,
        "duplicate_rate": _rate(total_duplicates, total_succeeded),
        "complete_core_fields": total_complete,
        "possible_core_fields": total_possible,
        "core_field_completeness": _rate(total_complete, total_possible),
        "sources": metrics,
    }


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _unexpected_failure(error: Exception, *, step: str) -> dict[str, JsonValue]:
    return {
        "code": f"stability.unexpected_{step}_failure",
        "message": f"Unexpected {step} evaluation failure.",
        "category": "permanent",
        "retryable": False,
        "details": {"error_type": type(error).__name__},
    }


def _configure_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
