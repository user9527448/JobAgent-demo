"""Validate and reparse one persisted recruitment document."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from jobagent.core import JobAgentError, configure_logging, get_settings
from jobagent.db import create_database
from jobagent.extraction import (
    DeterministicFieldExtractor,
    ExtractionMerger,
    ExtractionPolicy,
    ExtractionWriteResult,
    ReparseService,
    SqlAlchemyExtractionRepository,
    StoredDocumentReparsePipeline,
)
from jobagent.parsers import build_parser_registry


def main() -> int:
    """Run one manual extraction quality-control command."""
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
    commands = parser.add_subparsers(dest="command", required=True)
    reparse_parser = commands.add_parser("reparse", help="reparse one stored document")
    reparse_parser.add_argument("--document-id", type=_positive_id, required=True)
    reparse_parser.add_argument("--extraction-version", required=True)
    return parser


async def _execute(args: argparse.Namespace) -> int:
    settings = get_settings()
    database = create_database(settings)
    pipeline = StoredDocumentReparsePipeline(
        database.session_factory,
        settings.attachment_storage_path,
        build_parser_registry(),
        DeterministicFieldExtractor(ExtractionPolicy(timezone=settings.timezone)),
        ExtractionMerger(),
    )
    service = ReparseService(
        pipeline,
        SqlAlchemyExtractionRepository(database.session_factory),
    )
    try:
        result = await service.reparse(args.document_id, args.extraction_version)
        print(json.dumps(_result_payload(result), ensure_ascii=False, indent=2))
        return 0
    finally:
        await database.close()


def _result_payload(result: ExtractionWriteResult) -> dict[str, object]:
    return {
        "post_id": result.post_id,
        "position_ids": list(result.position_ids),
        "version": result.version,
        "extraction_version": result.extraction_version,
        "result_hash": result.result_hash,
        "write_status": result.status.value,
        "previous_post_id": result.previous_post_id,
        "review_status": result.review_status.value,
        "recommendation_eligible": result.recommendation_eligible,
        "validation_version": result.validation_version,
        "validation_error_count": result.validation_error_count,
        "validation_warning_count": result.validation_warning_count,
    }


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
