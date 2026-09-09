"""PostgreSQL acceptance for JAI-027 idempotency, retry, and crash recovery."""

from __future__ import annotations

import asyncio
import os
from datetime import date
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import URL, Engine, make_url

from jobagent.core import TransientJobAgentError
from jobagent.db import Database
from jobagent.db.models import NotificationDelivery, NotificationDeliveryAttempt
from jobagent.notifications import (
    DeliveryAttemptStatus,
    DeliveryDispatchStatus,
    DeliveryFailureKind,
    DeliveryMessagePart,
    DeliveryProviderError,
    DeliveryServicePolicy,
    DeliveryStatus,
    DeterministicDeliveryRenderer,
    ProviderDeliveryResult,
    ProviderDeliveryStatus,
    ProviderSubmission,
    SqlAlchemyDeliveryLock,
    SqlAlchemyDeliveryRepository,
    SqlAlchemyNotificationDeliveryService,
)
from jobagent.reports import SqlAlchemyDailyReportService

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).parents[2]


class ScriptedProvider:
    name = "synthetic"

    def __init__(
        self,
        submissions: list[ProviderSubmission | DeliveryProviderError],
        *,
        results: list[ProviderDeliveryResult | DeliveryProviderError] | None = None,
    ) -> None:
        self.submissions = submissions
        self.results = results or []
        self.submit_calls = 0
        self.result_calls: list[str] = []

    async def submit(self, part: DeliveryMessagePart) -> ProviderSubmission:
        del part
        self.submit_calls += 1
        outcome = self.submissions.pop(0)
        if isinstance(outcome, DeliveryProviderError):
            raise outcome
        return outcome

    async def get_result(self, provider_message_id: str) -> ProviderDeliveryResult:
        self.result_calls.append(provider_message_id)
        if self.results:
            outcome = self.results.pop(0)
            if isinstance(outcome, DeliveryProviderError):
                raise outcome
            return outcome
        return ProviderDeliveryResult(ProviderDeliveryStatus.SUCCEEDED)


class BlockingProvider(ScriptedProvider):
    def __init__(self) -> None:
        super().__init__([ProviderSubmission("synthetic-concurrent")])
        self.entered = asyncio.Event()
        self.release = asyncio.Event()

    async def submit(self, part: DeliveryMessagePart) -> ProviderSubmission:
        self.entered.set()
        await self.release.wait()
        return await super().submit(part)


def test_delivery_ledger_reuses_retries_recovers_and_locks_with_postgresql() -> None:
    database_url = _test_database_url()
    sync_engine = create_engine(database_url)
    _reset_test_schema(sync_engine)
    command.upgrade(_alembic_config(database_url), "head")

    async def scenario() -> None:
        rendered_url = database_url.render_as_string(hide_password=False)
        database = Database(rendered_url)
        reports = SqlAlchemyDailyReportService(database.session_factory, "Asia/Shanghai")
        repository = SqlAlchemyDeliveryRepository(database.session_factory)
        lock = SqlAlchemyDeliveryLock(database.session_factory)
        delays: list[float] = []

        async def capture_sleep(delay: float) -> None:
            delays.append(delay)

        try:
            first_snapshot = await reports.generate(date(2026, 9, 9))
            success_provider = ScriptedProvider([ProviderSubmission("synthetic-success")])
            success_service = SqlAlchemyNotificationDeliveryService(
                reports,
                repository,
                lock,
                success_provider,
                policy=DeliveryServicePolicy(max_result_polls=1),
                sleep=capture_sleep,
            )
            first = await success_service.deliver(first_snapshot.id)
            repeated = await success_service.deliver(first_snapshot.id)
            assert first.dispatch_status is DeliveryDispatchStatus.EXECUTED
            assert first.delivery is not None
            assert first.delivery.status is DeliveryStatus.SUCCEEDED
            assert repeated.dispatch_status is DeliveryDispatchStatus.REUSED
            assert repeated.delivery is not None
            assert repeated.delivery.id == first.delivery.id
            assert success_provider.submit_calls == 1

            retry_snapshot = await reports.generate(date(2026, 9, 10))
            retry_provider = ScriptedProvider(
                [
                    DeliveryProviderError(
                        "pushplus.submit_not_connected",
                        kind=DeliveryFailureKind.TRANSIENT,
                    ),
                    DeliveryProviderError(
                        "pushplus.submit_not_connected",
                        kind=DeliveryFailureKind.TRANSIENT,
                    ),
                    ProviderSubmission("synthetic-retry-success"),
                ]
            )
            retry_result = await SqlAlchemyNotificationDeliveryService(
                reports,
                repository,
                lock,
                retry_provider,
                policy=DeliveryServicePolicy(max_result_polls=1),
                sleep=capture_sleep,
            ).deliver(retry_snapshot.id)
            assert retry_result.delivery is not None
            assert retry_result.delivery.status is DeliveryStatus.SUCCEEDED
            assert retry_provider.submit_calls == 3
            assert delays == [30.0, 60.0]

            unknown_snapshot = await reports.generate(date(2026, 9, 11))
            unknown_provider = ScriptedProvider(
                [
                    DeliveryProviderError(
                        "pushplus.submit_outcome_unknown",
                        kind=DeliveryFailureKind.UNKNOWN,
                    )
                ]
            )
            unknown_service = SqlAlchemyNotificationDeliveryService(
                reports,
                repository,
                lock,
                unknown_provider,
                policy=DeliveryServicePolicy(max_result_polls=1),
                sleep=capture_sleep,
            )
            unknown = await unknown_service.deliver(unknown_snapshot.id)
            unknown_reused = await unknown_service.deliver(unknown_snapshot.id)
            assert unknown.delivery is not None
            assert unknown.delivery.status is DeliveryStatus.UNKNOWN
            assert unknown_reused.dispatch_status is DeliveryDispatchStatus.REUSED
            assert unknown_provider.submit_calls == 1

            interrupted_snapshot = await reports.generate(date(2026, 9, 12))
            message = DeterministicDeliveryRenderer().render(interrupted_snapshot)
            interrupted_delivery = await repository.get_or_create(message)
            await repository.start_attempt(interrupted_delivery.id, message.parts[0])
            recovery_provider = ScriptedProvider([])
            interrupted = await SqlAlchemyNotificationDeliveryService(
                reports,
                repository,
                lock,
                recovery_provider,
            ).deliver(interrupted_snapshot.id)
            assert interrupted.delivery is not None
            assert interrupted.delivery.status is DeliveryStatus.UNKNOWN
            assert recovery_provider.submit_calls == 0
            attempts = await repository.list_attempts(interrupted_delivery.id)
            assert attempts[0].status is DeliveryAttemptStatus.UNKNOWN

            accepted_snapshot = await reports.generate(date(2026, 9, 13))
            accepted_message = DeterministicDeliveryRenderer().render(accepted_snapshot)
            accepted_delivery = await repository.get_or_create(accepted_message)
            accepted_attempt = await repository.start_attempt(
                accepted_delivery.id,
                accepted_message.parts[0],
            )
            await repository.accept_attempt(accepted_attempt.id, "synthetic-resume")
            resume_provider = ScriptedProvider([])
            resumed = await SqlAlchemyNotificationDeliveryService(
                reports,
                repository,
                lock,
                resume_provider,
                policy=DeliveryServicePolicy(max_result_polls=1),
            ).deliver(accepted_snapshot.id)
            assert resumed.delivery is not None
            assert resumed.delivery.status is DeliveryStatus.SUCCEEDED
            assert resume_provider.submit_calls == 0
            assert resume_provider.result_calls == ["synthetic-resume"]

            pending_snapshot = await reports.generate(date(2026, 9, 14))
            pending_provider = ScriptedProvider(
                [ProviderSubmission("synthetic-pending")],
                results=[
                    ProviderDeliveryResult(ProviderDeliveryStatus.PENDING),
                    ProviderDeliveryResult(ProviderDeliveryStatus.SUCCEEDED),
                ],
            )
            pending_service = SqlAlchemyNotificationDeliveryService(
                reports,
                repository,
                lock,
                pending_provider,
                policy=DeliveryServicePolicy(max_result_polls=1),
            )
            with pytest.raises(TransientJobAgentError, match="remains accepted"):
                await pending_service.deliver(pending_snapshot.id)
            pending_resumed = await pending_service.deliver(pending_snapshot.id)
            assert pending_resumed.delivery is not None
            assert pending_resumed.delivery.status is DeliveryStatus.SUCCEEDED
            assert pending_provider.submit_calls == 1
            assert pending_provider.result_calls == ["synthetic-pending", "synthetic-pending"]

            exhausted_snapshot = await reports.generate(date(2026, 9, 15))
            exhausted_provider = ScriptedProvider(
                [
                    DeliveryProviderError(
                        "pushplus.submit_not_connected",
                        kind=DeliveryFailureKind.TRANSIENT,
                    )
                    for _ in range(3)
                ]
            )
            exhausted_service = SqlAlchemyNotificationDeliveryService(
                reports,
                repository,
                lock,
                exhausted_provider,
                policy=DeliveryServicePolicy(max_result_polls=1),
                sleep=capture_sleep,
            )
            exhausted = await exhausted_service.deliver(exhausted_snapshot.id)
            exhausted_reused = await exhausted_service.deliver(exhausted_snapshot.id)
            assert exhausted.delivery is not None
            assert exhausted.delivery.status is DeliveryStatus.FAILED
            assert exhausted.delivery.error_code == "pushplus.submit_not_connected"
            assert exhausted_reused.dispatch_status is DeliveryDispatchStatus.REUSED
            assert exhausted_provider.submit_calls == 3

            concurrent_snapshot = await reports.generate(date(2026, 9, 16))
            blocking_provider = BlockingProvider()
            concurrent_service = SqlAlchemyNotificationDeliveryService(
                reports,
                repository,
                lock,
                blocking_provider,
                policy=DeliveryServicePolicy(max_result_polls=1),
            )
            first_task = asyncio.create_task(concurrent_service.deliver(concurrent_snapshot.id))
            await blocking_provider.entered.wait()
            locked = await concurrent_service.deliver(concurrent_snapshot.id)
            assert locked.dispatch_status is DeliveryDispatchStatus.LOCKED
            assert locked.delivery is None
            blocking_provider.release.set()
            completed = await first_task
            assert completed.delivery is not None
            assert completed.delivery.status is DeliveryStatus.SUCCEEDED

            async with database.session_factory() as session:
                delivery_count = await session.scalar(
                    select(func.count()).select_from(NotificationDelivery)
                )
                attempt_count = await session.scalar(
                    select(func.count()).select_from(NotificationDeliveryAttempt)
                )
            assert delivery_count == 8
            assert attempt_count == 12
        finally:
            await database.close()

    try:
        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            runner.run(scenario())
    finally:
        _reset_test_schema(sync_engine)
        sync_engine.dispose()


def _test_database_url() -> URL:
    raw_url = os.getenv("JOBAGENT_TEST_DATABASE_URL")
    if raw_url is None:
        pytest.skip("Set JOBAGENT_TEST_DATABASE_URL to run PostgreSQL delivery tests.")
    database_url = make_url(raw_url)
    if not (database_url.database or "").endswith("_test"):
        pytest.fail("Delivery tests require a database whose name ends with '_test'.")
    return database_url


def _alembic_config(database_url: URL) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    rendered_url = database_url.render_as_string(hide_password=False).replace("%", "%%")
    config.set_main_option("sqlalchemy.url", rendered_url)
    return config


def _reset_test_schema(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
