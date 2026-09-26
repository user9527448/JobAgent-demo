"""Operate explicit report delivery and inspect its credential-safe ledger."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from jobagent.core import JobAgentError, configure_logging, get_settings
from jobagent.db import Database

from .contracts import (
    DeliveryDispatchStatus,
    DeliveryExecutionResult,
    DeliveryOperatorResult,
    DeliveryStatus,
)
from .persistence import SqlAlchemyDeliveryRepository
from .runtime import build_pushplus_delivery_service


def main() -> int:
    """Parse one delivery command and return a stable operator exit code."""
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
    send = commands.add_parser("send", help="create or safely resume one snapshot delivery")
    send.add_argument("--snapshot-id", type=_positive_id, required=True)
    resend = commands.add_parser(
        "resend",
        help="make one audited development-only submission for a terminal part",
    )
    resend.add_argument("--delivery-id", type=_positive_id, required=True)
    resend.add_argument("--part-number", type=_positive_id, required=True)
    resend.add_argument("--reason", type=_operator_reason, required=True)
    resend.add_argument("--confirm-duplicate-risk", action="store_true", required=True)
    show = commands.add_parser("show", help="show one delivery and its part attempts")
    show.add_argument("--delivery-id", type=_positive_id, required=True)
    return parser


async def _execute(args: argparse.Namespace) -> int:
    settings = get_settings()
    database = Database(settings.database_url.get_secret_value())
    provider = None
    try:
        repository = SqlAlchemyDeliveryRepository(database.session_factory)
        if args.command == "show":
            delivery = await repository.get(args.delivery_id)
            if delivery is None:
                print(
                    json.dumps(
                        {
                            "code": "notification.delivery_not_found",
                            "delivery_id": args.delivery_id,
                        },
                        ensure_ascii=False,
                    ),
                    file=sys.stderr,
                )
                return 2
            attempts = await repository.list_attempts(delivery.id)
            events = await repository.list_operator_events(delivery.id)
            payload = delivery.as_json()
            payload["attempts"] = [attempt.as_json() for attempt in attempts]
            payload["operator_events"] = [event.as_json() for event in events]
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0

        if args.command == "resend" and settings.environment != "development":
            print(
                json.dumps(
                    {
                        "code": "notification.operator_resend_environment_forbidden",
                        "environment": settings.environment,
                    },
                    ensure_ascii=False,
                ),
                file=sys.stderr,
            )
            return 2

        provider, service = build_pushplus_delivery_service(
            database.session_factory,
            settings,
        )
        result: DeliveryOperatorResult | DeliveryExecutionResult
        if args.command == "resend":
            result = await service.resend(
                delivery_id=args.delivery_id,
                part_number=args.part_number,
                reason=args.reason,
                duplicate_risk_confirmed=args.confirm_duplicate_risk,
            )
        else:
            result = await service.deliver(args.snapshot_id)
        print(json.dumps(result.as_json(), ensure_ascii=False, indent=2))
        if result.dispatch_status is DeliveryDispatchStatus.LOCKED:
            return 3
        if result.delivery is None or result.delivery.status is not DeliveryStatus.SUCCEEDED:
            return 2
        return 0
    finally:
        if provider is not None:
            await provider.aclose()
        await database.close()


def _positive_id(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("identifier must be positive")
    return parsed


def _operator_reason(value: str) -> str:
    normalized = value.strip()
    if not 10 <= len(normalized) <= 500:
        raise argparse.ArgumentTypeError("reason must contain 10 to 500 characters")
    return normalized


def _configure_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
