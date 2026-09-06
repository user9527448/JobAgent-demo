"""Production construction and logical schedule-time helpers."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from jobagent.core import Settings
from jobagent.db import Database

from .contracts import (
    DAILY_PIPELINE_JOB_NAME,
    PipelineExecutionResult,
    PipelineRunSnapshot,
    PipelineTrigger,
)
from .persistence import SqlAlchemyPipelineLock, SqlAlchemyPipelineRepository
from .pipeline import PipelineCoordinator, PipelinePolicy
from .stages import ProductionPipelineStages


class PipelineRuntime:
    """Own database resources and production pipeline collaborators."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.database = Database(settings.database_url.get_secret_value())
        self.repository = SqlAlchemyPipelineRepository(self.database.session_factory)
        self.coordinator = PipelineCoordinator(
            self.repository,
            SqlAlchemyPipelineLock(self.database.session_factory),
            ProductionPipelineStages(self.database.session_factory, settings),
            timezone=settings.timezone,
            policy=PipelinePolicy(
                max_attempts=settings.scheduler_stage_max_attempts,
                retry_delay_seconds=settings.scheduler_retry_delay_seconds,
            ),
        )

    async def execute(
        self,
        scheduled_for: datetime,
        trigger: PipelineTrigger,
    ) -> PipelineExecutionResult:
        return await self.coordinator.execute(scheduled_for, trigger)

    async def recover_incomplete(self) -> tuple[PipelineExecutionResult, ...]:
        """Resume persisted pending/running executions in oldest-first order."""
        incomplete = await self.repository.find_incomplete(DAILY_PIPELINE_JOB_NAME)
        results = [
            await self.coordinator.execute(run.scheduled_for, run.trigger) for run in incomplete
        ]
        return tuple(results)

    async def get_run(self, run_id: int) -> PipelineRunSnapshot | None:
        return await self.repository.get(run_id)

    async def close(self) -> None:
        await self.database.close()


def scheduled_slot_for_date(local_date: date, settings: Settings) -> datetime:
    """Convert one configured local daily slot to its canonical UTC identity."""
    zone = ZoneInfo(settings.timezone)
    local_slot = datetime.combine(
        local_date,
        time(settings.scheduler_hour, settings.scheduler_minute),
        tzinfo=zone,
    )
    return local_slot.astimezone(UTC)


def latest_due_slot(now: datetime, settings: Settings) -> datetime:
    """Return the latest configured slot at or before an aware instant."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("The scheduler clock must be timezone-aware.")
    local_now = now.astimezone(ZoneInfo(settings.timezone))
    local_date = local_now.date()
    slot = scheduled_slot_for_date(local_date, settings)
    if now.astimezone(UTC) < slot:
        slot = scheduled_slot_for_date(local_date - timedelta(days=1), settings)
    return slot
