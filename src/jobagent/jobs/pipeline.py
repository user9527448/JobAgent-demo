"""Durable four-stage pipeline coordination, retry, and recovery."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol
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
                outcome = await self._run_stage(run.id, stage, context)
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
    ) -> StageOutcome | None:
        for policy_attempt in range(1, self._policy.max_attempts + 1):
            attempt = await self._repository.start_stage(run_id, stage)
            try:
                outcome = await self._stages.run(stage, context)
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
                is_collection_partial = (
                    stage is PipelineStage.COLLECTION
                    and policy_attempt == self._policy.max_attempts
                    and _positive_count(error.details.get("successful_sources"))
                )
                terminal_status = (
                    StageStatus.PARTIAL if is_collection_partial else StageStatus.FAILED
                )
                output = dict(error.details)
                await self._repository.finish_stage(
                    attempt.id,
                    status=terminal_status,
                    output=output,
                    error_code=error.code,
                    error_message=error.message,
                )
                if is_collection_partial:
                    return StageOutcome(StageStatus.PARTIAL, output)
                if error.retryable and policy_attempt < self._policy.max_attempts:
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
            await self._repository.finish_stage(
                attempt.id,
                status=outcome.status,
                output=outcome.output,
            )
            return outcome
        raise AssertionError("Pipeline retry loop exited without a result.")


def _positive_count(value: JsonValue) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0
