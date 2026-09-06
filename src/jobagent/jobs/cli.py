"""Operate the JAI-026 scheduler, makeup runs, and durable run inspection."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date

from jobagent.core import JobAgentError, configure_logging, get_settings

from .contracts import DispatchStatus, PipelineStatus
from .runtime import PipelineRuntime, scheduled_slot_for_date
from .scheduler import run_makeup, serve_scheduler


def main() -> int:
    """Parse one scheduler command and return an operator-facing exit code."""
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
    commands.add_parser("start", help="recover incomplete work and run the daily scheduler")
    makeup = commands.add_parser("makeup", help="run or resume one configured local date")
    makeup.add_argument("--date", type=_iso_date, required=True)
    show = commands.add_parser("show", help="show one pipeline run and all stage attempts")
    show.add_argument("--run-id", type=_positive_id, required=True)
    return parser


async def _execute(args: argparse.Namespace) -> int:
    settings = get_settings()
    if args.command == "start":
        await serve_scheduler()
        return 0
    if args.command == "makeup":
        result = await run_makeup(settings, scheduled_slot_for_date(args.date, settings))
        print(json.dumps(result.as_json(), ensure_ascii=False, indent=2))
        if result.dispatch_status is DispatchStatus.LOCKED:
            return 3
        if result.run is not None and result.run.status is PipelineStatus.FAILED:
            return 2
        return 0

    runtime = PipelineRuntime(settings)
    try:
        run = await runtime.get_run(args.run_id)
        if run is None:
            print(
                json.dumps(
                    {
                        "code": "pipeline.run_not_found",
                        "run_id": args.run_id,
                    },
                    ensure_ascii=False,
                ),
                file=sys.stderr,
            )
            return 2
        attempts = await runtime.repository.list_stage_attempts(run.id)
        payload = run.as_json()
        payload["stage_attempts"] = [
            {
                "id": item.id,
                "stage": item.stage.value,
                "attempt": item.attempt,
                "status": item.status.value,
                "started_at": item.started_at.isoformat(),
                "finished_at": item.finished_at.isoformat() if item.finished_at else None,
                "output": item.output,
                "error_code": item.error_code,
                "error_message": item.error_message,
            }
            for item in attempts
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    finally:
        await runtime.close()


def _iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD") from error


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
