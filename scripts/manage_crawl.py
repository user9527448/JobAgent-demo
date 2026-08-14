"""Manually run, inspect, or retry one persisted source crawl."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from jobagent.core import JobAgentError, configure_logging, get_settings
from jobagent.core.exceptions import PermanentJobAgentError
from jobagent.crawlers import (
    CollectionOrchestrator,
    HttpSourcePolicy,
    SourceHttpClient,
    SqlAlchemyCrawlRunRepository,
    SqlAlchemyRawDocumentRepository,
    build_adapter_registry,
    load_source_catalog,
    match_catalog_entry,
)
from jobagent.crawlers.contracts import CrawlRunSummary, SourceDefinition
from jobagent.db import create_database

DEFAULT_CATALOG = Path("config/source_catalog.toml")
USER_AGENT = "JOBAGENT/0.1 (+personal recruitment intelligence; manual public-source run)"


def main() -> int:
    """Parse one manual collection command and return a process exit code."""
    _configure_stdout()
    args = _build_parser().parse_args()
    settings = get_settings()
    configure_logging(settings)
    try:
        if sys.platform == "win32":
            with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
                return runner.run(_execute(args))
        return asyncio.run(_execute(args))
    except JobAgentError as error:
        print(json.dumps(error.to_dict(), ensure_ascii=False), file=sys.stderr)
        return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    commands = parser.add_subparsers(dest="command", required=True)

    run_parser = commands.add_parser("run", help="run one enabled source")
    run_parser.add_argument("--source-id", type=_positive_id, required=True)

    show_parser = commands.add_parser("show", help="show one persisted run summary")
    show_parser.add_argument("--run-id", type=_positive_id, required=True)

    retry_parser = commands.add_parser("retry", help="retry only failed detail items")
    retry_parser.add_argument("--run-id", type=_positive_id, required=True)
    return parser


async def _execute(args: argparse.Namespace) -> int:
    settings = get_settings()
    database = create_database(settings)
    run_repository = SqlAlchemyCrawlRunRepository(database.session_factory)
    document_repository = SqlAlchemyRawDocumentRepository(database.session_factory)
    try:
        if args.command == "show":
            summary = await _require_run(run_repository, args.run_id)
        else:
            retry_run_id = args.run_id if args.command == "retry" else None
            source_id = (
                (await _require_run(run_repository, retry_run_id)).source_id
                if retry_run_id is not None
                else args.source_id
            )
            source = await _require_source(run_repository, source_id)
            catalog = load_source_catalog(args.catalog)
            entry = match_catalog_entry(catalog, source)
            policy = HttpSourcePolicy(
                source_id=source.id,
                user_agent=USER_AGENT,
                min_interval_seconds=1.0,
                max_concurrency=1,
            )
            async with SourceHttpClient(policy) as http_client:
                registry = build_adapter_registry(source, entry, http_client)
                orchestrator = CollectionOrchestrator(
                    registry,
                    run_repository,
                    document_repository,
                )
                result = (
                    await orchestrator.retry_failed(retry_run_id)
                    if retry_run_id is not None
                    else await orchestrator.run(source_id)
                )
            summary = await _require_run(run_repository, result.run_id)
        print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))
        return 0
    finally:
        await database.close()


async def _require_run(
    repository: SqlAlchemyCrawlRunRepository,
    run_id: int,
) -> CrawlRunSummary:
    summary = await repository.get_run(run_id)
    if summary is None:
        raise PermanentJobAgentError(
            f"Crawl run {run_id} does not exist.",
            code="crawler.run_not_found",
            details={"run_id": run_id},
        )
    return summary


async def _require_source(
    repository: SqlAlchemyCrawlRunRepository,
    source_id: int,
) -> SourceDefinition:
    source = await repository.get_source(source_id)
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


def _positive_id(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("identifier must be positive")
    return parsed


def _configure_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
