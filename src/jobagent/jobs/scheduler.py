"""APScheduler 3 construction and the importable daily job target."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore  # type: ignore[import-untyped]
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore[import-untyped]
from apscheduler.triggers.cron import CronTrigger  # type: ignore[import-untyped]

from jobagent.core import Settings, configure_logging, get_settings

from .contracts import DAILY_PIPELINE_JOB_NAME, PipelineExecutionResult, PipelineTrigger
from .runtime import PipelineRuntime, latest_due_slot


async def scheduled_pipeline_job() -> None:
    """Importable persistent-job target that executes the latest due logical slot."""
    settings = get_settings()
    runtime = PipelineRuntime(settings)
    try:
        await runtime.execute(
            latest_due_slot(datetime.now(UTC), settings),
            PipelineTrigger.SCHEDULED,
        )
    finally:
        await runtime.close()


def build_scheduler(
    settings: Settings,
    *,
    jobstore: Any | None = None,
    job_target: Callable[[], object] = scheduled_pipeline_job,
) -> Any:
    """Build one configured scheduler with a fixed replaceable cron job."""
    resolved_jobstore = jobstore or SQLAlchemyJobStore(
        url=settings.database_url.get_secret_value(),
        tablename="apscheduler_jobs",
        engine_options={"pool_pre_ping": True},
    )
    scheduler = AsyncIOScheduler(
        jobstores={"default": resolved_jobstore},
        timezone=ZoneInfo(settings.timezone),
    )
    scheduler.add_job(
        job_target,
        CronTrigger(
            hour=settings.scheduler_hour,
            minute=settings.scheduler_minute,
            timezone=ZoneInfo(settings.timezone),
        ),
        id=DAILY_PIPELINE_JOB_NAME,
        name="JOBAGENT daily pipeline",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=settings.scheduler_misfire_grace_seconds,
    )
    return scheduler


async def serve_scheduler() -> None:
    """Recover incomplete work, then serve the single persistent scheduler."""
    settings = get_settings()
    configure_logging(settings)
    runtime = PipelineRuntime(settings)
    try:
        await runtime.recover_incomplete()
    finally:
        await runtime.close()

    scheduler = build_scheduler(settings)
    scheduler.start()
    try:
        await asyncio.Event().wait()
    finally:
        scheduler.shutdown(wait=True)


async def run_makeup(settings: Settings, scheduled_for: datetime) -> PipelineExecutionResult:
    """Execute one manual logical slot without starting the scheduler loop."""
    runtime = PipelineRuntime(settings)
    try:
        return await runtime.execute(scheduled_for, PipelineTrigger.MAKEUP)
    finally:
        await runtime.close()
