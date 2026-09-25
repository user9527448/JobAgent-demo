"""Persistent idempotent delivery orchestration with bounded provider interaction."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from typing import Protocol

from jobagent.core import PermanentJobAgentError, TransientJobAgentError
from jobagent.reports import DailyReportOperations

from .contracts import (
    DeliveryAttemptSnapshot,
    DeliveryAttemptStatus,
    DeliveryChannel,
    DeliveryDispatchStatus,
    DeliveryExecutionResult,
    DeliveryFailureKind,
    DeliveryMessage,
    DeliveryMessagePart,
    DeliveryProvider,
    DeliveryProviderError,
    DeliveryRetryPolicy,
    DeliverySnapshot,
    DeliveryStatus,
    ProviderDeliveryStatus,
)
from .rendering import DeterministicDeliveryRenderer

Sleep = Callable[[float], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class DeliveryServicePolicy:
    """Bound submission retries and final-result polling independently."""

    retry: DeliveryRetryPolicy = field(default_factory=DeliveryRetryPolicy)
    max_result_polls: int = 12
    result_poll_interval_seconds: float = 10.0

    def __post_init__(self) -> None:
        if self.max_result_polls <= 0:
            raise ValueError("Delivery result poll count must be positive.")
        if self.result_poll_interval_seconds < 0:
            raise ValueError("Delivery result poll interval cannot be negative.")


class DeliveryRepository(Protocol):
    async def get_or_create(self, message: DeliveryMessage) -> DeliverySnapshot: ...

    async def get(self, delivery_id: int) -> DeliverySnapshot | None: ...

    async def get_by_identity(
        self,
        report_snapshot_id: int,
        channel: DeliveryChannel,
    ) -> DeliverySnapshot | None: ...

    async def list_attempts(self, delivery_id: int) -> tuple[DeliveryAttemptSnapshot, ...]: ...

    async def interrupt_submitting_attempts(self, delivery_id: int) -> int: ...

    async def start_attempt(
        self,
        delivery_id: int,
        part: DeliveryMessagePart,
    ) -> DeliveryAttemptSnapshot: ...

    async def accept_attempt(
        self,
        attempt_id: int,
        provider_message_id: str,
    ) -> DeliveryAttemptSnapshot: ...

    async def finish_attempt(
        self,
        attempt_id: int,
        *,
        status: DeliveryAttemptStatus,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> DeliveryAttemptSnapshot: ...

    async def finish_delivery(
        self,
        delivery_id: int,
        *,
        status: DeliveryStatus,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> DeliverySnapshot: ...


class DeliveryLock(Protocol):
    def acquire(
        self,
        report_snapshot_id: int,
        channel: DeliveryChannel,
    ) -> AbstractAsyncContextManager[bool]: ...


class SqlAlchemyNotificationDeliveryService:
    """Persist every submission transition and never auto-resend unknown outcomes."""

    def __init__(
        self,
        reports: DailyReportOperations,
        repository: DeliveryRepository,
        lock: DeliveryLock,
        provider: DeliveryProvider,
        *,
        renderer: DeterministicDeliveryRenderer | None = None,
        policy: DeliveryServicePolicy | None = None,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._reports = reports
        self._repository = repository
        self._lock = lock
        self._provider = provider
        self._renderer = renderer or DeterministicDeliveryRenderer()
        self._policy = policy or DeliveryServicePolicy()
        self._sleep = sleep

    async def deliver(self, report_snapshot_id: int) -> DeliveryExecutionResult:
        """Deliver once, resume accepted work, or return a durable blocked result."""
        snapshot = await self._reports.get(report_snapshot_id)
        message = self._renderer.render(snapshot)
        async with self._lock.acquire(message.report_snapshot_id, message.channel) as acquired:
            if not acquired:
                return DeliveryExecutionResult(DeliveryDispatchStatus.LOCKED, None)
            delivery = await self._repository.get_or_create(message)
            if delivery.status in {
                DeliveryStatus.SUCCEEDED,
                DeliveryStatus.FAILED,
                DeliveryStatus.UNKNOWN,
            }:
                return DeliveryExecutionResult(DeliveryDispatchStatus.REUSED, delivery)
            if await self._repository.interrupt_submitting_attempts(delivery.id):
                interrupted = await self._require_delivery(delivery.id)
                return DeliveryExecutionResult(DeliveryDispatchStatus.EXECUTED, interrupted)

            attempts = await self._repository.list_attempts(delivery.id)
            _verify_attempt_hashes(message, attempts)
            by_part = _attempts_by_part(attempts)
            for part in message.parts:
                outcome = await self._deliver_part(
                    delivery.id,
                    part,
                    by_part.get(part.part_number, ()),
                )
                if outcome is not None:
                    return DeliveryExecutionResult(DeliveryDispatchStatus.EXECUTED, outcome)

            completed = await self._repository.finish_delivery(
                delivery.id,
                status=DeliveryStatus.SUCCEEDED,
            )
            return DeliveryExecutionResult(DeliveryDispatchStatus.EXECUTED, completed)

    async def _deliver_part(
        self,
        delivery_id: int,
        part: DeliveryMessagePart,
        attempts: tuple[DeliveryAttemptSnapshot, ...],
    ) -> DeliverySnapshot | None:
        latest = attempts[-1] if attempts else None
        if latest is not None and latest.status is DeliveryAttemptStatus.SUCCEEDED:
            return None
        if latest is not None and latest.status is DeliveryAttemptStatus.UNKNOWN:
            return await self._repository.finish_delivery(
                delivery_id,
                status=DeliveryStatus.UNKNOWN,
                error_code=latest.error_code,
                error_message=latest.error_message,
            )
        if latest is not None and latest.status is DeliveryAttemptStatus.ACCEPTED:
            return await self._confirm_accepted(delivery_id, latest)

        used_attempts = latest.attempt if latest is not None else 0
        if used_attempts >= self._policy.retry.max_attempts:
            return await self._repository.finish_delivery(
                delivery_id,
                status=DeliveryStatus.FAILED,
                error_code="notification.retry_exhausted",
                error_message="The bounded provider submission attempts were exhausted.",
            )

        for _ in range(used_attempts, self._policy.retry.max_attempts):
            attempt = await self._repository.start_attempt(delivery_id, part)
            try:
                submission = await self._provider.submit(part)
            except asyncio.CancelledError:
                await self._repository.finish_attempt(
                    attempt.id,
                    status=DeliveryAttemptStatus.UNKNOWN,
                    error_code="notification.submit_cancelled_unknown",
                    error_message="Provider submission may have completed before cancellation.",
                )
                await self._repository.finish_delivery(
                    delivery_id,
                    status=DeliveryStatus.UNKNOWN,
                    error_code="notification.submit_cancelled_unknown",
                    error_message="Provider submission outcome is unknown after cancellation.",
                )
                raise
            except DeliveryProviderError as error:
                outcome = await self._record_provider_failure(delivery_id, attempt, error)
                if outcome is not None:
                    return outcome
                await self._sleep(self._policy.retry.delay_after(attempt.attempt))
                continue

            accepted = await self._repository.accept_attempt(
                attempt.id,
                submission.provider_message_id,
            )
            return await self._confirm_accepted(delivery_id, accepted)
        raise AssertionError("Delivery retry loop exited without a result.")

    async def _record_provider_failure(
        self,
        delivery_id: int,
        attempt: DeliveryAttemptSnapshot,
        error: DeliveryProviderError,
    ) -> DeliverySnapshot | None:
        if error.kind is DeliveryFailureKind.UNKNOWN:
            message = "The provider may have accepted the message; automatic resend is blocked."
            await self._repository.finish_attempt(
                attempt.id,
                status=DeliveryAttemptStatus.UNKNOWN,
                error_code=error.code,
                error_message=message,
            )
            return await self._repository.finish_delivery(
                delivery_id,
                status=DeliveryStatus.UNKNOWN,
                error_code=error.code,
                error_message=message,
            )

        message = (
            "The provider temporarily rejected the submission."
            if error.retryable
            else "The provider permanently rejected the submission."
        )
        await self._repository.finish_attempt(
            attempt.id,
            status=DeliveryAttemptStatus.FAILED,
            error_code=error.code,
            error_message=message,
        )
        if error.retryable and attempt.attempt < self._policy.retry.max_attempts:
            return None
        return await self._repository.finish_delivery(
            delivery_id,
            status=DeliveryStatus.FAILED,
            error_code=error.code,
            error_message=message,
        )

    async def _confirm_accepted(
        self,
        delivery_id: int,
        attempt: DeliveryAttemptSnapshot,
    ) -> DeliverySnapshot | None:
        provider_message_id = attempt.provider_message_id
        if provider_message_id is None:
            raise PermanentJobAgentError(
                "An accepted delivery attempt is missing its provider message ID.",
                code="notification.accepted_identity_missing",
                details={"attempt_id": attempt.id},
            )
        for poll in range(1, self._policy.max_result_polls + 1):
            try:
                result = await self._provider.get_result(provider_message_id)
            except DeliveryProviderError as error:
                if error.retryable and poll < self._policy.max_result_polls:
                    await self._sleep(self._policy.result_poll_interval_seconds)
                    continue
                if error.retryable:
                    raise TransientJobAgentError(
                        "Provider final status remains temporarily unavailable.",
                        code="notification.result_temporarily_unavailable",
                        details={"delivery_id": delivery_id, "attempt_id": attempt.id},
                    ) from None
                # Submission already returned a durable provider identity. A lookup
                # error cannot prove final delivery failure, even when its immediate
                # cause (for example an AccessKey rejection) is permanent. Keep the
                # logical outcome unknown so no later operator action can resubmit it.
                message = "Provider final status could not be safely confirmed."
                await self._repository.finish_attempt(
                    attempt.id,
                    status=DeliveryAttemptStatus.UNKNOWN,
                    error_code=error.code,
                    error_message=message,
                )
                return await self._repository.finish_delivery(
                    delivery_id,
                    status=DeliveryStatus.UNKNOWN,
                    error_code=error.code,
                    error_message=message,
                )

            if result.status is ProviderDeliveryStatus.SUCCEEDED:
                await self._repository.finish_attempt(
                    attempt.id,
                    status=DeliveryAttemptStatus.SUCCEEDED,
                )
                return None
            if result.status is ProviderDeliveryStatus.FAILED:
                error_code = result.error_code or "pushplus.delivery_failed"
                message = "The provider reported final delivery failure."
                await self._repository.finish_attempt(
                    attempt.id,
                    status=DeliveryAttemptStatus.FAILED,
                    error_code=error_code,
                    error_message=message,
                )
                return await self._repository.finish_delivery(
                    delivery_id,
                    status=DeliveryStatus.FAILED,
                    error_code=error_code,
                    error_message=message,
                )
            if poll < self._policy.max_result_polls:
                await self._sleep(self._policy.result_poll_interval_seconds)
                continue
            raise TransientJobAgentError(
                "Provider delivery remains accepted but not final.",
                code="notification.result_pending",
                details={"delivery_id": delivery_id, "attempt_id": attempt.id},
            )
        raise AssertionError("Delivery result polling loop exited without a result.")

    async def _require_delivery(self, delivery_id: int) -> DeliverySnapshot:
        delivery = await self._repository.get(delivery_id)
        if delivery is None:
            raise PermanentJobAgentError(
                "The notification delivery disappeared during execution.",
                code="notification.delivery_not_found",
                details={"delivery_id": delivery_id},
            )
        return delivery


def _attempts_by_part(
    attempts: tuple[DeliveryAttemptSnapshot, ...],
) -> dict[int, tuple[DeliveryAttemptSnapshot, ...]]:
    grouped: dict[int, list[DeliveryAttemptSnapshot]] = {}
    for attempt in attempts:
        grouped.setdefault(attempt.part_number, []).append(attempt)
    return {part: tuple(values) for part, values in grouped.items()}


def _verify_attempt_hashes(
    message: DeliveryMessage,
    attempts: tuple[DeliveryAttemptSnapshot, ...],
) -> None:
    hashes = {part.part_number: part.content_hash for part in message.parts}
    for attempt in attempts:
        if hashes.get(attempt.part_number) != attempt.part_hash:
            raise PermanentJobAgentError(
                "Persisted delivery attempt does not match the deterministic message.",
                code="notification.attempt_identity_conflict",
                details={"delivery_id": attempt.delivery_id, "attempt_id": attempt.id},
            )
