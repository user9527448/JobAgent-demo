"""PostgreSQL delivery ledger and report/channel advisory lock."""

from __future__ import annotations

import hashlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobagent.core import PermanentJobAgentError, TransientJobAgentError
from jobagent.db.models import NotificationDelivery, NotificationDeliveryAttempt

from .contracts import (
    DeliveryAttemptSnapshot,
    DeliveryAttemptStatus,
    DeliveryChannel,
    DeliveryMessage,
    DeliveryMessagePart,
    DeliverySnapshot,
    DeliveryStatus,
)


class SqlAlchemyDeliveryRepository:
    """Persist idempotent logical deliveries and append-only part attempts."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_or_create(self, message: DeliveryMessage) -> DeliverySnapshot:
        try:
            async with self._session_factory() as session, session.begin():
                created_id = await session.scalar(
                    insert(NotificationDelivery)
                    .values(
                        report_snapshot_id=message.report_snapshot_id,
                        channel=message.channel.value,
                        delivery_version=message.delivery_version,
                        message_hash=message.message_hash,
                        part_count=len(message.parts),
                        status=DeliveryStatus.PENDING.value,
                    )
                    .on_conflict_do_nothing(
                        index_elements=[
                            NotificationDelivery.report_snapshot_id,
                            NotificationDelivery.channel,
                        ]
                    )
                    .returning(NotificationDelivery.id)
                )
                model = (
                    await session.get(NotificationDelivery, created_id)
                    if created_id is not None
                    else await session.scalar(
                        select(NotificationDelivery)
                        .where(
                            NotificationDelivery.report_snapshot_id == message.report_snapshot_id,
                            NotificationDelivery.channel == message.channel.value,
                        )
                        .with_for_update()
                    )
                )
                if model is None:
                    raise RuntimeError("Delivery upsert did not return a row.")
                if (
                    model.delivery_version != message.delivery_version
                    or model.message_hash != message.message_hash
                    or model.part_count != len(message.parts)
                ):
                    raise PermanentJobAgentError(
                        "The logical delivery identity has conflicting rendered content.",
                        code="notification.delivery_identity_conflict",
                        details={"delivery_id": model.id},
                    )
                return _delivery_snapshot(model)
        except SQLAlchemyError as error:
            raise _database_error("get or create delivery", error) from error

    async def get(self, delivery_id: int) -> DeliverySnapshot | None:
        try:
            async with self._session_factory() as session:
                model = await session.get(NotificationDelivery, delivery_id)
                return None if model is None else _delivery_snapshot(model)
        except SQLAlchemyError as error:
            raise _database_error("load delivery", error) from error

    async def get_by_identity(
        self,
        report_snapshot_id: int,
        channel: DeliveryChannel,
    ) -> DeliverySnapshot | None:
        try:
            async with self._session_factory() as session:
                model = await session.scalar(
                    select(NotificationDelivery).where(
                        NotificationDelivery.report_snapshot_id == report_snapshot_id,
                        NotificationDelivery.channel == channel.value,
                    )
                )
                return None if model is None else _delivery_snapshot(model)
        except SQLAlchemyError as error:
            raise _database_error("load delivery identity", error) from error

    async def list_attempts(self, delivery_id: int) -> tuple[DeliveryAttemptSnapshot, ...]:
        try:
            async with self._session_factory() as session:
                models = await session.scalars(
                    select(NotificationDeliveryAttempt)
                    .where(NotificationDeliveryAttempt.delivery_id == delivery_id)
                    .order_by(
                        NotificationDeliveryAttempt.part_number,
                        NotificationDeliveryAttempt.attempt,
                    )
                )
                return tuple(_attempt_snapshot(model) for model in models)
        except SQLAlchemyError as error:
            raise _database_error("list delivery attempts", error) from error

    async def interrupt_submitting_attempts(self, delivery_id: int) -> int:
        """Make crash-window ambiguity explicit before any resumed submission."""
        now = datetime.now(UTC)
        try:
            async with self._session_factory() as session, session.begin():
                attempt_ids = tuple(
                    await session.scalars(
                        select(NotificationDeliveryAttempt.id).where(
                            NotificationDeliveryAttempt.delivery_id == delivery_id,
                            NotificationDeliveryAttempt.status
                            == DeliveryAttemptStatus.SUBMITTING.value,
                        )
                    )
                )
                if not attempt_ids:
                    return 0
                await session.execute(
                    update(NotificationDeliveryAttempt)
                    .where(NotificationDeliveryAttempt.id.in_(attempt_ids))
                    .values(
                        status=DeliveryAttemptStatus.UNKNOWN.value,
                        finished_at=now,
                        error_code="notification.submit_interrupted_unknown",
                        error_message=(
                            "The process ended while provider submission outcome was unknown."
                        ),
                    )
                )
                delivery = await _require_delivery(session, delivery_id)
                delivery.status = DeliveryStatus.UNKNOWN.value
                delivery.finished_at = now
                delivery.error_code = "notification.submit_interrupted_unknown"
                delivery.error_message = (
                    "The provider may have accepted a message before the process ended."
                )
                delivery.updated_at = now
                return len(attempt_ids)
        except SQLAlchemyError as error:
            raise _database_error("interrupt ambiguous delivery attempts", error) from error

    async def start_attempt(
        self,
        delivery_id: int,
        part: DeliveryMessagePart,
    ) -> DeliveryAttemptSnapshot:
        now = datetime.now(UTC)
        try:
            async with self._session_factory() as session, session.begin():
                delivery = await _require_delivery(session, delivery_id)
                if part.part_count != delivery.part_count:
                    raise PermanentJobAgentError(
                        "Delivery part count conflicts with its logical delivery.",
                        code="notification.part_identity_conflict",
                        details={"delivery_id": delivery_id, "part_number": part.part_number},
                    )
                latest_attempt = await session.scalar(
                    select(func.coalesce(func.max(NotificationDeliveryAttempt.attempt), 0)).where(
                        NotificationDeliveryAttempt.delivery_id == delivery_id,
                        NotificationDeliveryAttempt.part_number == part.part_number,
                    )
                )
                model = NotificationDeliveryAttempt(
                    delivery_id=delivery_id,
                    part_number=part.part_number,
                    attempt=int(latest_attempt or 0) + 1,
                    part_hash=part.content_hash,
                    status=DeliveryAttemptStatus.SUBMITTING.value,
                    started_at=now,
                )
                session.add(model)
                delivery.status = DeliveryStatus.SENDING.value
                delivery.started_at = delivery.started_at or now
                delivery.finished_at = None
                delivery.error_code = None
                delivery.error_message = None
                delivery.updated_at = now
                await session.flush()
                return _attempt_snapshot(model)
        except SQLAlchemyError as error:
            raise _database_error("start delivery attempt", error) from error

    async def accept_attempt(
        self,
        attempt_id: int,
        provider_message_id: str,
    ) -> DeliveryAttemptSnapshot:
        try:
            async with self._session_factory() as session, session.begin():
                model = await _require_attempt(session, attempt_id)
                if model.status != DeliveryAttemptStatus.SUBMITTING.value:
                    raise PermanentJobAgentError(
                        "Only a submitting delivery attempt can be accepted.",
                        code="notification.attempt_transition_invalid",
                        details={"attempt_id": attempt_id},
                    )
                model.status = DeliveryAttemptStatus.ACCEPTED.value
                model.provider_message_id = provider_message_id
                await session.flush()
                return _attempt_snapshot(model)
        except SQLAlchemyError as error:
            raise _database_error("accept delivery attempt", error) from error

    async def finish_attempt(
        self,
        attempt_id: int,
        *,
        status: DeliveryAttemptStatus,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> DeliveryAttemptSnapshot:
        if status not in {
            DeliveryAttemptStatus.SUCCEEDED,
            DeliveryAttemptStatus.FAILED,
            DeliveryAttemptStatus.UNKNOWN,
            DeliveryAttemptStatus.INTERRUPTED,
        }:
            raise ValueError("Delivery attempt completion requires a terminal status.")
        try:
            async with self._session_factory() as session, session.begin():
                model = await _require_attempt(session, attempt_id)
                model.status = status.value
                model.finished_at = datetime.now(UTC)
                model.error_code = error_code
                model.error_message = error_message
                await session.flush()
                return _attempt_snapshot(model)
        except SQLAlchemyError as error:
            raise _database_error("finish delivery attempt", error) from error

    async def finish_delivery(
        self,
        delivery_id: int,
        *,
        status: DeliveryStatus,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> DeliverySnapshot:
        if status not in {
            DeliveryStatus.SUCCEEDED,
            DeliveryStatus.FAILED,
            DeliveryStatus.UNKNOWN,
        }:
            raise ValueError("Delivery completion requires a terminal status.")
        now = datetime.now(UTC)
        try:
            async with self._session_factory() as session, session.begin():
                model = await _require_delivery(session, delivery_id)
                model.status = status.value
                model.finished_at = now
                model.error_code = error_code
                model.error_message = error_message
                model.updated_at = now
                await session.flush()
                return _delivery_snapshot(model)
        except SQLAlchemyError as error:
            raise _database_error("finish delivery", error) from error


class SqlAlchemyDeliveryLock:
    """Serialize scheduler and operator delivery for one report/channel identity."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    @asynccontextmanager
    async def acquire(
        self,
        report_snapshot_id: int,
        channel: DeliveryChannel,
    ) -> AsyncIterator[bool]:
        lock_key = int.from_bytes(
            hashlib.sha256(
                f"jobagent.delivery:{report_snapshot_id}:{channel.value}".encode()
            ).digest()[:8],
            byteorder="big",
            signed=True,
        )
        acquired = False
        try:
            async with self._session_factory() as session:
                acquired = bool(await session.scalar(select(func.pg_try_advisory_lock(lock_key))))
                try:
                    yield acquired
                finally:
                    if acquired:
                        await session.scalar(select(func.pg_advisory_unlock(lock_key)))
        except SQLAlchemyError as error:
            raise _database_error("acquire delivery lock", error) from error


async def _require_delivery(session: AsyncSession, delivery_id: int) -> NotificationDelivery:
    model = await session.get(NotificationDelivery, delivery_id, with_for_update=True)
    if model is None:
        raise PermanentJobAgentError(
            "The requested notification delivery does not exist.",
            code="notification.delivery_not_found",
            details={"delivery_id": delivery_id},
        )
    return model


async def _require_attempt(
    session: AsyncSession,
    attempt_id: int,
) -> NotificationDeliveryAttempt:
    model = await session.get(NotificationDeliveryAttempt, attempt_id, with_for_update=True)
    if model is None:
        raise PermanentJobAgentError(
            "The requested notification delivery attempt does not exist.",
            code="notification.attempt_not_found",
            details={"attempt_id": attempt_id},
        )
    return model


def _delivery_snapshot(model: NotificationDelivery) -> DeliverySnapshot:
    return DeliverySnapshot(
        id=model.id,
        report_snapshot_id=model.report_snapshot_id,
        channel=DeliveryChannel(model.channel),
        delivery_version=model.delivery_version,
        message_hash=model.message_hash,
        part_count=model.part_count,
        status=DeliveryStatus(model.status),
        started_at=model.started_at,
        finished_at=model.finished_at,
        error_code=model.error_code,
        error_message=model.error_message,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _attempt_snapshot(model: NotificationDeliveryAttempt) -> DeliveryAttemptSnapshot:
    return DeliveryAttemptSnapshot(
        id=model.id,
        delivery_id=model.delivery_id,
        part_number=model.part_number,
        attempt=model.attempt,
        part_hash=model.part_hash,
        status=DeliveryAttemptStatus(model.status),
        provider_message_id=model.provider_message_id,
        started_at=model.started_at,
        finished_at=model.finished_at,
        error_code=model.error_code,
        error_message=model.error_message,
    )


def _database_error(operation: str, error: SQLAlchemyError) -> TransientJobAgentError:
    return TransientJobAgentError(
        f"Database could not {operation}.",
        code="notification.database_unavailable",
        details={"error_type": type(error).__name__},
    )
