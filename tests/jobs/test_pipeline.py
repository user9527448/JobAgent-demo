"""Unit checks for JAI-026 pipeline ordering, retry, and recovery."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, date, datetime

import pytest

from jobagent.core import PermanentJobAgentError, TransientJobAgentError
from jobagent.core.exceptions import JsonValue
from jobagent.jobs import (
    DAILY_PIPELINE_JOB_NAME,
    DispatchStatus,
    PipelineContext,
    PipelineCoordinator,
    PipelineRunSnapshot,
    PipelineStage,
    PipelineStatus,
    PipelineTrigger,
    StageAttemptSnapshot,
    StageOutcome,
    StageStatus,
)
from jobagent.jobs.pipeline import PipelinePolicy

SCHEDULED_FOR = datetime(2026, 9, 6, tzinfo=UTC)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


pytestmark = pytest.mark.anyio


class FakeLock:
    def __init__(self, acquired: bool = True) -> None:
        self.acquired = acquired

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[bool]:
        yield self.acquired


class FakeRepository:
    def __init__(
        self,
        *,
        status: PipelineStatus = PipelineStatus.PENDING,
        latest: dict[PipelineStage, StageStatus] | None = None,
    ) -> None:
        self.run = _run(status)
        self.latest = latest or {}
        self.attempts: list[StageAttemptSnapshot] = []
        self.finished_stages: list[tuple[PipelineStage, StageStatus]] = []
        self.interrupt_calls = 0
        self.get_or_create_calls = 0

    async def get_or_create(
        self,
        *,
        job_name: str,
        scheduled_for: datetime,
        report_date: date,
        timezone: str,
        trigger: PipelineTrigger,
    ) -> PipelineRunSnapshot:
        self.get_or_create_calls += 1
        assert job_name == DAILY_PIPELINE_JOB_NAME
        assert scheduled_for == SCHEDULED_FOR
        assert report_date == date(2026, 9, 6)
        assert timezone == "Asia/Shanghai"
        del trigger
        return self.run

    async def interrupt_running_stages(self, run_id: int) -> int:
        assert run_id == self.run.id
        self.interrupt_calls += 1
        return 0

    async def latest_stage_statuses(self, run_id: int) -> dict[PipelineStage, StageStatus]:
        assert run_id == self.run.id
        return self.latest

    async def start_stage(
        self,
        run_id: int,
        stage: PipelineStage,
    ) -> StageAttemptSnapshot:
        attempt = StageAttemptSnapshot(
            id=len(self.attempts) + 1,
            pipeline_run_id=run_id,
            stage=stage,
            attempt=sum(item.stage is stage for item in self.attempts) + 1,
            status=StageStatus.RUNNING,
            started_at=SCHEDULED_FOR,
            finished_at=None,
            output={},
            error_code=None,
            error_message=None,
        )
        self.attempts.append(attempt)
        return attempt

    async def finish_stage(
        self,
        stage_run_id: int,
        *,
        status: StageStatus,
        output: dict[str, JsonValue] | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> StageAttemptSnapshot:
        original = self.attempts[stage_run_id - 1]
        finished = replace(
            original,
            status=status,
            finished_at=SCHEDULED_FOR,
            output=output or {},
            error_code=error_code,
            error_message=error_message,
        )
        self.finished_stages.append((original.stage, status))
        return finished

    async def finish_run(
        self,
        run_id: int,
        *,
        status: PipelineStatus,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> PipelineRunSnapshot:
        assert run_id == self.run.id
        self.run = replace(
            self.run,
            status=status,
            current_stage=None,
            finished_at=SCHEDULED_FOR,
            error_code=error_code,
            error_message=error_message,
        )
        return self.run


class SequenceStages:
    def __init__(self, values: list[StageOutcome | Exception] | None = None) -> None:
        self.values = list(values or [])
        self.calls: list[PipelineStage] = []

    async def run(self, stage: PipelineStage, context: PipelineContext) -> StageOutcome:
        assert context.scheduled_for == SCHEDULED_FOR
        self.calls.append(stage)
        value = self.values.pop(0) if self.values else StageOutcome(StageStatus.SUCCEEDED, {})
        if isinstance(value, Exception):
            raise value
        return value


async def test_pipeline_runs_in_order_and_preserves_partial_status() -> None:
    repository = FakeRepository()
    stages = SequenceStages(
        [
            StageOutcome(StageStatus.PARTIAL, {"crawl_run_ids": [1]}),
            StageOutcome(StageStatus.SUCCEEDED, {}),
            StageOutcome(StageStatus.SUCCEEDED, {}),
            StageOutcome(StageStatus.SUCCEEDED, {"report_snapshot_id": 9}),
        ]
    )

    result = await PipelineCoordinator(
        repository,
        FakeLock(),
        stages,
        timezone="Asia/Shanghai",
    ).execute(SCHEDULED_FOR, PipelineTrigger.SCHEDULED)

    assert result.dispatch_status is DispatchStatus.EXECUTED
    assert result.run is not None and result.run.status is PipelineStatus.PARTIAL
    assert stages.calls == list(PipelineStage)


async def test_transient_stage_retries_with_exponential_delays() -> None:
    repository = FakeRepository()
    stages = SequenceStages(
        [
            TransientJobAgentError("temporary", code="test.temporary"),
            TransientJobAgentError("temporary", code="test.temporary"),
            StageOutcome(StageStatus.SUCCEEDED, {}),
        ]
    )
    delays: list[float] = []

    async def capture_sleep(delay: float) -> None:
        delays.append(delay)

    result = await PipelineCoordinator(
        repository,
        FakeLock(),
        stages,
        timezone="Asia/Shanghai",
        policy=PipelinePolicy(max_attempts=3, retry_delay_seconds=30),
        sleep=capture_sleep,
    ).execute(SCHEDULED_FOR, PipelineTrigger.SCHEDULED)

    assert result.run is not None and result.run.status is PipelineStatus.SUCCEEDED
    assert stages.calls.count(PipelineStage.COLLECTION) == 3
    assert delays == [30, 60]


async def test_permanent_failure_stops_downstream_stages() -> None:
    repository = FakeRepository()
    stages = SequenceStages([PermanentJobAgentError("bad", code="test.permanent")])

    result = await PipelineCoordinator(
        repository,
        FakeLock(),
        stages,
        timezone="Asia/Shanghai",
    ).execute(SCHEDULED_FOR, PipelineTrigger.SCHEDULED)

    assert result.run is not None and result.run.status is PipelineStatus.FAILED
    assert result.run.error_code == "test.permanent"
    assert stages.calls == [PipelineStage.COLLECTION]


async def test_recovery_skips_completed_stage_and_lock_contention_writes_nothing() -> None:
    recovered_repository = FakeRepository(
        status=PipelineStatus.RUNNING,
        latest={PipelineStage.COLLECTION: StageStatus.SUCCEEDED},
    )
    recovered_stages = SequenceStages()
    recovered = await PipelineCoordinator(
        recovered_repository,
        FakeLock(),
        recovered_stages,
        timezone="Asia/Shanghai",
    ).execute(SCHEDULED_FOR, PipelineTrigger.MAKEUP)

    assert recovered.run is not None and recovered.run.status is PipelineStatus.SUCCEEDED
    assert recovered_stages.calls == [
        PipelineStage.EXTRACTION,
        PipelineStage.MATCHING,
        PipelineStage.REPORT,
    ]
    assert recovered_repository.interrupt_calls == 1

    locked_repository = FakeRepository()
    locked = await PipelineCoordinator(
        locked_repository,
        FakeLock(False),
        SequenceStages(),
        timezone="Asia/Shanghai",
    ).execute(SCHEDULED_FOR, PipelineTrigger.SCHEDULED)
    assert locked.dispatch_status is DispatchStatus.LOCKED
    assert locked.run is None
    assert locked_repository.get_or_create_calls == 0


def _run(status: PipelineStatus) -> PipelineRunSnapshot:
    return PipelineRunSnapshot(
        id=1,
        job_name=DAILY_PIPELINE_JOB_NAME,
        scheduled_for=SCHEDULED_FOR,
        report_date=date(2026, 9, 6),
        timezone="Asia/Shanghai",
        trigger=PipelineTrigger.SCHEDULED,
        status=status,
        current_stage=None,
        started_at=None,
        finished_at=None,
        error_code=None,
        error_message=None,
    )
