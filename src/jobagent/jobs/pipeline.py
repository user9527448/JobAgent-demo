"""Durable four-stage pipeline coordination, retry, and recovery."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, replace
from datetime import date, datetime
from typing import Protocol, cast
from zoneinfo import ZoneInfo

from jobagent.core.exceptions import JobAgentError, JsonValue

from .contracts import (
    DAILY_PIPELINE_JOB_NAME,
    PIPELINE_STAGE_ORDER,
    DispatchStatus,
    PipelineExecutionResult,
    PipelineRunSnapshot,
    PipelineStage,
    PipelineStatus,
    PipelineTrigger,
    StageAttemptSnapshot,
    StageOutcome,
    StageStatus,
)

Sleep = Callable[[float], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class PipelineContext:
    """Stable logical inputs shared by all attempts and stages."""

    pipeline_run_id: int
    scheduled_for: datetime
    report_date: date
    timezone: str
    collection_source_ids: tuple[int, ...] | None = None


@dataclass(frozen=True, slots=True)
class PipelinePolicy:
    """Bounded stage-level retry policy."""

    max_attempts: int = 3
    retry_delay_seconds: int = 30

    def __post_init__(self) -> None:
        if self.max_attempts <= 0:
            raise ValueError("Pipeline max attempts must be positive.")
        if self.retry_delay_seconds < 0:
            raise ValueError("Pipeline retry delay cannot be negative.")


class PipelineRepository(Protocol):
    """Persistence operations required by the coordinator."""

    async def get_or_create(
        self,
        *,
        job_name: str,
        scheduled_for: datetime,
        report_date: date,
        timezone: str,
        trigger: PipelineTrigger,
    ) -> PipelineRunSnapshot: ...

    async def interrupt_running_stages(self, run_id: int) -> int: ...

    async def latest_stage_statuses(self, run_id: int) -> dict[PipelineStage, StageStatus]: ...

    async def latest_stage_attempts(
        self, run_id: int
    ) -> dict[PipelineStage, StageAttemptSnapshot]: ...

    async def start_stage(
        self,
        run_id: int,
        stage: PipelineStage,
    ) -> StageAttemptSnapshot: ...

    async def finish_stage(
        self,
        stage_run_id: int,
        *,
        status: StageStatus,
        output: dict[str, JsonValue] | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> StageAttemptSnapshot: ...

    async def finish_run(
        self,
        run_id: int,
        *,
        status: PipelineStatus,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> PipelineRunSnapshot: ...


class PipelineLock(Protocol):
    """Cross-process lock boundary."""

    def acquire(self) -> AbstractAsyncContextManager[bool]: ...


class PipelineStages(Protocol):
    """Injectable production or test implementation of each stage."""

    async def run(self, stage: PipelineStage, context: PipelineContext) -> StageOutcome: ...


class PipelineCoordinator:
    """Execute or resume one uniquely identified daily pipeline run."""

    def __init__(
        self,
        repository: PipelineRepository,
        lock: PipelineLock,
        stages: PipelineStages,
        *,
        timezone: str,
        policy: PipelinePolicy | None = None,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._repository = repository
        self._lock = lock
        self._stages = stages
        self._timezone = timezone
        self._policy = policy or PipelinePolicy()
        self._sleep = sleep

    async def execute(
        self,
        scheduled_for: datetime,
        trigger: PipelineTrigger,
    ) -> PipelineExecutionResult:
        """Run once, resume safely, reuse terminal results, or report lock contention."""
        if scheduled_for.tzinfo is None or scheduled_for.utcoffset() is None:
            raise ValueError("Pipeline schedule times must be timezone-aware.")
        report_date = scheduled_for.astimezone(ZoneInfo(self._timezone)).date()
        async with self._lock.acquire() as acquired:
            if not acquired:
                return PipelineExecutionResult(DispatchStatus.LOCKED, None)
            run = await self._repository.get_or_create(
                job_name=DAILY_PIPELINE_JOB_NAME,
                scheduled_for=scheduled_for,
                report_date=report_date,
                timezone=self._timezone,
                trigger=trigger,
            )
            if run.status in {PipelineStatus.SUCCEEDED, PipelineStatus.PARTIAL}:
                return PipelineExecutionResult(DispatchStatus.REUSED, run)

            await self._repository.interrupt_running_stages(run.id)
            latest = await self._repository.latest_stage_statuses(run.id)
            latest_attempts = await self._repository.latest_stage_attempts(run.id)
            partial = any(status is StageStatus.PARTIAL for status in latest.values())
            context = PipelineContext(
                pipeline_run_id=run.id,
                scheduled_for=run.scheduled_for,
                report_date=run.report_date,
                timezone=run.timezone,
            )
            for stage in PIPELINE_STAGE_ORDER:
                previous = latest.get(stage)
                if previous in {StageStatus.SUCCEEDED, StageStatus.PARTIAL}:
                    partial = partial or previous is StageStatus.PARTIAL
                    continue
                previous_output = (
                    latest_attempts[stage].output if stage in latest_attempts else None
                )
                outcome = await self._run_stage(
                    run.id,
                    stage,
                    context,
                    previous_output=previous_output,
                )
                if outcome is None:
                    failed = await self._repository.get_or_create(
                        job_name=run.job_name,
                        scheduled_for=run.scheduled_for,
                        report_date=run.report_date,
                        timezone=run.timezone,
                        trigger=run.trigger,
                    )
                    return PipelineExecutionResult(DispatchStatus.EXECUTED, failed)
                partial = partial or outcome.status is StageStatus.PARTIAL

            completed = await self._repository.finish_run(
                run.id,
                status=PipelineStatus.PARTIAL if partial else PipelineStatus.SUCCEEDED,
            )
            return PipelineExecutionResult(DispatchStatus.EXECUTED, completed)

    async def _run_stage(
        self,
        run_id: int,
        stage: PipelineStage,
        context: PipelineContext,
        *,
        previous_output: dict[str, JsonValue] | None = None,
    ) -> StageOutcome | None:
        collection_output = (
            _collection_output(previous_output) if stage is PipelineStage.COLLECTION else None
        )
        retry_source_ids = _retryable_source_ids(collection_output)
        for policy_attempt in range(1, self._policy.max_attempts + 1):
            attempt = await self._repository.start_stage(run_id, stage)
            attempt_context = (
                replace(context, collection_source_ids=retry_source_ids)
                if stage is PipelineStage.COLLECTION and retry_source_ids
                else context
            )
            try:
                outcome = await self._stages.run(stage, attempt_context)
            except asyncio.CancelledError:
                await self._repository.finish_stage(
                    attempt.id,
                    status=StageStatus.INTERRUPTED,
                    error_code="pipeline.stage_cancelled",
                    error_message="The pipeline process cancelled this stage.",
                )
                await self._repository.finish_run(run_id, status=PipelineStatus.CANCELLED)
                raise
            except JobAgentError as error:
                output = dict(error.details)
                if stage is PipelineStage.COLLECTION:
                    collection_output = _merge_collection_outputs(
                        collection_output,
                        output,
                    )
                    output = collection_output
                    retry_source_ids = _retryable_source_ids(collection_output)
                is_collection_partial = (
                    stage is PipelineStage.COLLECTION
                    and policy_attempt == self._policy.max_attempts
                    and _positive_count(output.get("successful_sources"))
                )
                terminal_status = (
                    StageStatus.PARTIAL if is_collection_partial else StageStatus.FAILED
                )
                await self._repository.finish_stage(
                    attempt.id,
                    status=terminal_status,
                    output=output,
                    error_code=error.code,
                    error_message=error.message,
                )
                if is_collection_partial:
                    return StageOutcome(StageStatus.PARTIAL, output)
                if (
                    error.retryable
                    and policy_attempt < self._policy.max_attempts
                    and (
                        stage is not PipelineStage.COLLECTION
                        or retry_source_ids
                        or not _has_retryable_collection_failure_identity(output)
                    )
                ):
                    await self._sleep(
                        self._policy.retry_delay_seconds * (2 ** (policy_attempt - 1))
                    )
                    continue
                await self._repository.finish_run(
                    run_id,
                    status=PipelineStatus.FAILED,
                    error_code=error.code,
                    error_message=error.message,
                )
                return None
            except Exception as error:
                error_type = type(error).__name__
                await self._repository.finish_stage(
                    attempt.id,
                    status=StageStatus.FAILED,
                    error_code="pipeline.stage_unexpected",
                    error_message=f"Unexpected stage failure: {error_type}.",
                )
                await self._repository.finish_run(
                    run_id,
                    status=PipelineStatus.FAILED,
                    error_code="pipeline.stage_unexpected",
                    error_message=f"Unexpected stage failure: {error_type}.",
                )
                return None
            if stage is PipelineStage.COLLECTION:
                collection_output = _merge_collection_outputs(
                    collection_output,
                    outcome.output,
                )
                collection_status = (
                    StageStatus.PARTIAL
                    if collection_output.get("failures")
                    or _positive_count(collection_output.get("partial_sources"))
                    else outcome.status
                )
                outcome = StageOutcome(collection_status, collection_output)
            await self._repository.finish_stage(
                attempt.id,
                status=outcome.status,
                output=outcome.output,
            )
            return outcome
        raise AssertionError("Pipeline retry loop exited without a result.")


def _positive_count(value: JsonValue) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _collection_output(
    output: dict[str, JsonValue] | None,
) -> dict[str, JsonValue] | None:
    if not output or not isinstance(output.get("successful_source_ids"), list):
        return None
    return dict(output)


def _retryable_source_ids(output: dict[str, JsonValue] | None) -> tuple[int, ...] | None:
    if output is None:
        return None
    failures = output.get("failures")
    if not isinstance(failures, list):
        return None
    source_ids = {
        source_id
        for failure in failures
        if isinstance(failure, dict)
        and failure.get("retryable") is True
        and isinstance((source_id := failure.get("source_id")), int)
        and not isinstance(source_id, bool)
    }
    return tuple(sorted(source_ids)) or None


def _has_retryable_collection_failure_identity(output: dict[str, JsonValue]) -> bool:
    failures = output.get("failures")
    return isinstance(failures, list) and any(
        isinstance(failure, dict)
        and failure.get("retryable") is True
        and isinstance(failure.get("source_id"), int)
        and not isinstance(failure.get("source_id"), bool)
        for failure in failures
    )


def _merge_collection_outputs(
    previous: dict[str, JsonValue] | None,
    current: dict[str, JsonValue],
) -> dict[str, JsonValue]:
    if previous is None:
        return dict(current)

    successful = _integer_set(previous.get("successful_source_ids"))
    successful.update(_integer_set(current.get("successful_source_ids")))
    partial = _integer_set(previous.get("partial_source_ids"))
    partial.update(_integer_set(current.get("partial_source_ids")))

    failures: dict[int, dict[str, JsonValue]] = {}
    for output in (previous, current):
        values = output.get("failures")
        if not isinstance(values, list):
            continue
        for value in values:
            if not isinstance(value, dict):
                continue
            source_id = value.get("source_id")
            if isinstance(source_id, int) and not isinstance(source_id, bool):
                failures[source_id] = dict(value)
    for source_id in successful | partial:
        failures.pop(source_id, None)

    crawl_run_ids = list(_integer_sequence(previous.get("crawl_run_ids")))
    for run_id in _integer_sequence(current.get("crawl_run_ids")):
        if run_id not in crawl_run_ids:
            crawl_run_ids.append(run_id)

    source_count = max(
        _nonnegative_integer(previous.get("source_count")),
        _nonnegative_integer(current.get("source_count")),
    )
    merged = dict(current)
    merged.update(
        {
            "source_count": source_count,
            "successful_sources": len(successful),
            "partial_sources": len(partial),
            "successful_source_ids": cast(list[JsonValue], sorted(successful)),
            "partial_source_ids": cast(list[JsonValue], sorted(partial)),
            "crawl_run_ids": cast(list[JsonValue], crawl_run_ids),
            "failures": [failures[source_id] for source_id in sorted(failures)],
        }
    )
    return merged


def _integer_set(value: JsonValue) -> set[int]:
    return set(_integer_sequence(value))


def _integer_sequence(value: JsonValue) -> tuple[int, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, int) and not isinstance(item, bool))


def _nonnegative_integer(value: JsonValue) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0
