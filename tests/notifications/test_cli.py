"""Credential-safe operator CLI checks for JAI-027."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime
from typing import ClassVar

import pytest

from jobagent.notifications import cli
from jobagent.notifications.contracts import (
    DeliveryAttemptSnapshot,
    DeliveryAttemptStatus,
    DeliveryChannel,
    DeliveryDispatchStatus,
    DeliveryExecutionResult,
    DeliverySnapshot,
    DeliveryStatus,
)


class _Secret:
    def get_secret_value(self) -> str:
        return "postgresql+psycopg://synthetic"


class _Settings:
    database_url = _Secret()


class _FakeDatabase:
    instances: ClassVar[list[_FakeDatabase]] = []

    def __init__(self, database_url: str) -> None:
        assert database_url == "postgresql+psycopg://synthetic"
        self.session_factory = object()
        self.closed = False
        self.instances.append(self)

    async def close(self) -> None:
        self.closed = True


class _FakeRepository:
    delivery: ClassVar[DeliverySnapshot | None] = None
    attempts: ClassVar[tuple[DeliveryAttemptSnapshot, ...]] = ()

    def __init__(self, session_factory: object) -> None:
        assert session_factory is not None

    async def get(self, delivery_id: int) -> DeliverySnapshot | None:
        assert delivery_id > 0
        return self.delivery

    async def list_attempts(self, delivery_id: int) -> tuple[DeliveryAttemptSnapshot, ...]:
        assert delivery_id > 0
        return self.attempts


class _FakeProvider:
    def __init__(self) -> None:
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True


class _FakeService:
    def __init__(self, result: DeliveryExecutionResult) -> None:
        self.result = result
        self.snapshot_ids: list[int] = []

    async def deliver(self, snapshot_id: int) -> DeliveryExecutionResult:
        self.snapshot_ids.append(snapshot_id)
        return self.result


@pytest.fixture(autouse=True)
def reset_fakes(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeDatabase.instances.clear()
    _FakeRepository.delivery = None
    _FakeRepository.attempts = ()
    monkeypatch.setattr(cli, "get_settings", lambda: _Settings())
    monkeypatch.setattr(cli, "Database", _FakeDatabase)
    monkeypatch.setattr(cli, "SqlAlchemyDeliveryRepository", _FakeRepository)


def test_delivery_cli_parser_accepts_commands_and_rejects_nonpositive_ids() -> None:
    parser = cli._build_parser()

    send = parser.parse_args(["send", "--snapshot-id", "7"])
    show = parser.parse_args(["show", "--delivery-id", "9"])
    assert (send.command, send.snapshot_id) == ("send", 7)
    assert (show.command, show.delivery_id) == ("show", 9)
    with pytest.raises(argparse.ArgumentTypeError, match="positive"):
        cli._positive_id("0")


def test_show_returns_safe_not_found_payload(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = asyncio.run(cli._execute(argparse.Namespace(command="show", delivery_id=41)))

    captured = capsys.readouterr()
    assert exit_code == 2
    assert json.loads(captured.err) == {
        "code": "notification.delivery_not_found",
        "delivery_id": 41,
    }
    assert _FakeDatabase.instances[-1].closed is True


def test_show_prints_delivery_with_ordered_attempts(capsys: pytest.CaptureFixture[str]) -> None:
    delivery = _delivery(DeliveryStatus.SUCCEEDED)
    _FakeRepository.delivery = delivery
    _FakeRepository.attempts = (
        DeliveryAttemptSnapshot(
            id=3,
            delivery_id=delivery.id,
            part_number=1,
            attempt=1,
            part_hash="b" * 64,
            status=DeliveryAttemptStatus.SUCCEEDED,
            provider_message_id="safe-short-code",
            started_at=_now(),
            finished_at=_now(),
            error_code=None,
            error_message=None,
        ),
    )

    exit_code = asyncio.run(cli._execute(argparse.Namespace(command="show", delivery_id=1)))

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "succeeded"
    assert payload["attempts"][0]["provider_message_id"] == "safe-short-code"
    assert _FakeDatabase.instances[-1].closed is True


def _delivery(status: DeliveryStatus) -> DeliverySnapshot:
    return DeliverySnapshot(
        id=1,
        report_snapshot_id=17,
        channel=DeliveryChannel.PUSHPLUS_WECHAT,
        delivery_version="jai-027-v1",
        message_hash="a" * 64,
        part_count=1,
        status=status,
        started_at=_now(),
        finished_at=_now(),
        error_code="pushplus.permanent" if status is DeliveryStatus.FAILED else None,
        error_message="Provider permanently rejected the request."
        if status is DeliveryStatus.FAILED
        else None,
        created_at=_now(),
        updated_at=_now(),
    )


def _now() -> datetime:
    return datetime(2026, 9, 10, tzinfo=UTC)


@pytest.mark.parametrize(
    ("result", "expected_exit"),
    [
        (DeliveryExecutionResult(DeliveryDispatchStatus.LOCKED, None), 3),
        (
            DeliveryExecutionResult(
                DeliveryDispatchStatus.EXECUTED,
                _delivery(DeliveryStatus.FAILED),
            ),
            2,
        ),
        (
            DeliveryExecutionResult(
                DeliveryDispatchStatus.REUSED,
                _delivery(DeliveryStatus.SUCCEEDED),
            ),
            0,
        ),
    ],
)
def test_send_maps_dispatch_result_and_closes_resources(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    result: DeliveryExecutionResult,
    expected_exit: int,
) -> None:
    provider = _FakeProvider()
    service = _FakeService(result)
    monkeypatch.setattr(
        cli,
        "build_pushplus_delivery_service",
        lambda session_factory, settings: (provider, service),
    )

    exit_code = asyncio.run(cli._execute(argparse.Namespace(command="send", snapshot_id=17)))

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == expected_exit
    assert payload["dispatch_status"] == result.dispatch_status.value
    assert service.snapshot_ids == [17]
    assert provider.closed is True
    assert _FakeDatabase.instances[-1].closed is True
