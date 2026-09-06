"""PostgreSQL run ledger and cross-process advisory lock."""

from __future__ import annotations

import hashlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobagent.core.exceptions import (
    JsonValue,
    PermanentJobAgentError,
    TransientJobAgentError,
)
from jobagent.db.models import PipelineRun, PipelineStageRun

from .contracts import (
    PipelineRunSnapshot,
    PipelineStage,
    PipelineStatus,
    PipelineTrigger,
    StageAttemptSnapshot,
    StageStatus,
)

PIPELINE_LOCK_KEY = int.from_bytes(
    hashlib.sha256(b"jobagent.daily-pipeline.v1").digest()[:8],
    byteorder="big",
    signed=True,
)


class SqlAlchemyPipelineRepository:
    """Persist logical runs and immutable-numbered stage attempts."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_or_create(
        self,
        *,
        job_name: str,
        scheduled_for: datetime,
        report_date: date,
        timezone: str,
        trigger: PipelineTrigger,
    ) -> PipelineRunSnapshot:
        scheduled_for = _aware_utc(scheduled_for)
        try:
            async with self._session_factory() as session, session.begin():
                created_id = await session.scalar(
                    insert(PipelineRun)
                    .values(
                        job_name=job_name,
                        scheduled_for=scheduled_for,
                        report_date=report_date,
                        timezone=timezone,
                        trigger=trigger.value,
                        status=PipelineStatus.PENDING.value,
                    )
                    .on_conflict_do_nothing(
                        index_elements=[PipelineRun.job_name, PipelineRun.scheduled_for]
                    )
                    .returning(PipelineRun.id)
                )
                model = (
                    await session.get(PipelineRun, created_id)
                    if created_id is not None
                    else await session.scalar(
                        select(PipelineRun)
                        .where(
                            PipelineRun.job_name == job_name,
                            PipelineRun.scheduled_for == scheduled_for,
                        )
                        .with_for_update()
                    )
                )
                if model is None:
                    raise RuntimeError("Pipeline run upsert did not return a row.")
                if model.report_date != report_date or model.timezone != timezone:
                    raise PermanentJobAgentError(
                        "The logical pipeline run has conflicting calendar identity.",
                        code="pipeline.run_identity_conflict",
                        details={"run_id": model.id},
                    )
                return _run_snapshot(model)
        except SQLAlchemyError as error:
            raise _database_error("get or create pipeline run", error) from error

    async def get(self, run_id: int) -> PipelineRunSnapshot | None:
        try:
            async with self._session_factory() as session:
                model = await session.get(PipelineRun, run_id)
                return None if model is None else _run_snapshot(model)
        except SQLAlchemyError as error:
            raise _database_error("load pipeline run", error) from error

    async def find_incomplete(self, job_name: str) -> tuple[PipelineRunSnapshot, ...]:
        try:
            async with self._session_factory() as session:
                models = await session.scalars(
                    select(PipelineRun)
                    .where(
                        PipelineRun.job_name == job_name,
                        PipelineRun.status.in_(
                            [PipelineStatus.PENDING.value, PipelineStatus.RUNNING.value]
                        ),
                    )
                    .order_by(PipelineRun.scheduled_for, PipelineRun.id)
                )
                return tuple(_run_snapshot(model) for model in models)
        except SQLAlchemyError as error:
            raise _database_error("find incomplete pipeline runs", error) from error

    async def mark_running(self, run_id: int, stage: PipelineStage) -> PipelineRunSnapshot:
        now = datetime.now(UTC)
        try:
            async with self._session_factory() as session, session.begin():
                model = await _require_run(session, run_id)
                model.status = PipelineStatus.RUNNING.value
                model.current_stage = stage.value
                model.started_at = model.started_at or now
                model.finished_at = None
                model.error_code = None
                model.error_message = None
                model.updated_at = now
                await session.flush()
                return _run_snapshot(model)
        except SQLAlchemyError as error:
            raise _database_error("mark pipeline run running", error) from error

    async def interrupt_running_stages(self, run_id: int) -> int:
        now = datetime.now(UTC)
        try:
            async with self._session_factory() as session, session.begin():
                stage_ids = tuple(
                    await session.scalars(
                        select(PipelineStageRun.id).where(
                            PipelineStageRun.pipeline_run_id == run_id,
                            PipelineStageRun.status == StageStatus.RUNNING.value,
                        )
                    )
                )
                if stage_ids:
                    await session.execute(
                        update(PipelineStageRun)
                        .where(PipelineStageRun.id.in_(stage_ids))
                        .values(
                            status=StageStatus.INTERRUPTED.value,
                            finished_at=now,
                            error_code="pipeline.stage_interrupted",
                            error_message=(
                                "The previous process ended before this stage completed."
                            ),
                        )
                    )
                return len(stage_ids)
        except SQLAlchemyError as error:
            raise _database_error("interrupt stale pipeline stages", error) from error

    async def latest_stage_statuses(self, run_id: int) -> dict[PipelineStage, StageStatus]:
        try:
            async with self._session_factory() as session:
                models = await session.scalars(
                    select(PipelineStageRun)
                    .where(PipelineStageRun.pipeline_run_id == run_id)
                    .order_by(PipelineStageRun.stage, PipelineStageRun.attempt.desc())
                )
                latest: dict[PipelineStage, StageStatus] = {}
                for model in models:
                    latest.setdefault(PipelineStage(model.stage), StageStatus(model.status))
                return latest
        except SQLAlchemyError as error:
            raise _database_error("load pipeline stage statuses", error) from error

    async def start_stage(
        self,
        run_id: int,
        stage: PipelineStage,
    ) -> StageAttemptSnapshot:
        now = datetime.now(UTC)
        try:
            async with self._session_factory() as session, session.begin():
                run = await _require_run(session, run_id)
                latest_attempt = await session.scalar(
                    select(func.coalesce(func.max(PipelineStageRun.attempt), 0)).where(
                        PipelineStageRun.pipeline_run_id == run_id,
                        PipelineStageRun.stage == stage.value,
                    )
                )
                attempt = int(latest_attempt or 0) + 1
                model = PipelineStageRun(
                    pipeline_run_id=run_id,
                    stage=stage.value,
                    attempt=attempt,
                    status=StageStatus.RUNNING.value,
                    started_at=now,
                )
                session.add(model)
                run.status = PipelineStatus.RUNNING.value
                run.current_stage = stage.value
                run.started_at = run.started_at or now
                run.updated_at = now
                await session.flush()
                return _stage_snapshot(model)
        except SQLAlchemyError as error:
            raise _database_error("start pipeline stage", error) from error

    async def finish_stage(
        self,
        stage_run_id: int,
        *,
        status: StageStatus,
        output: dict[str, JsonValue] | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> StageAttemptSnapshot:
        if status is StageStatus.RUNNING:
            raise ValueError("A finished stage cannot remain running.")
        try:
            async with self._session_factory() as session, session.begin():
                model = await session.get(PipelineStageRun, stage_run_id, with_for_update=True)
                if model is None:
                    raise PermanentJobAgentError(
                        "The requested pipeline stage attempt does not exist.",
                        code="pipeline.stage_not_found",
                        details={"stage_run_id": stage_run_id},
                    )
                model.status = status.value
                model.output = output or {}
                model.error_code = error_code
                model.error_message = error_message
                model.finished_at = datetime.now(UTC)
                await session.flush()
                return _stage_snapshot(model)
        except SQLAlchemyError as error:
            raise _database_error("finish pipeline stage", error) from error

    async def finish_run(
        self,
        run_id: int,
        *,
        status: PipelineStatus,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> PipelineRunSnapshot:
        if status not in {
            PipelineStatus.SUCCEEDED,
            PipelineStatus.PARTIAL,
            PipelineStatus.FAILED,
            PipelineStatus.CANCELLED,
        }:
            raise ValueError("Pipeline completion requires a terminal status.")
        now = datetime.now(UTC)
        try:
            async with self._session_factory() as session, session.begin():
                model = await _require_run(session, run_id)
                model.status = status.value
                model.current_stage = None
                model.finished_at = now
                model.error_code = error_code
                model.error_message = error_message
                model.updated_at = now
                await session.flush()
                return _run_snapshot(model)
        except SQLAlchemyError as error:
            raise _database_error("finish pipeline run", error) from error

    async def list_stage_attempts(self, run_id: int) -> tuple[StageAttemptSnapshot, ...]:
        try:
            async with self._session_factory() as session:
                models = await session.scalars(
                    select(PipelineStageRun)
                    .where(PipelineStageRun.pipeline_run_id == run_id)
                    .order_by(PipelineStageRun.id)
                )
                return tuple(_stage_snapshot(model) for model in models)
        except SQLAlchemyError as error:
            raise _database_error("list pipeline stage attempts", error) from error


class SqlAlchemyPipelineLock:
    """Hold one PostgreSQL session advisory lock for the complete pipeline."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        lock_key: int = PIPELINE_LOCK_KEY,
    ) -> None:
        self._session_factory = session_factory
        self._lock_key = lock_key

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[bool]:
        acquired = False
        try:
            async with self._session_factory() as session:
                acquired = bool(
                    await session.scalar(select(func.pg_try_advisory_lock(self._lock_key)))
                )
                try:
                    yield acquired
                finally:
                    if acquired:
                        await session.scalar(select(func.pg_advisory_unlock(self._lock_key)))
        except SQLAlchemyError as error:
            raise _database_error("acquire pipeline lock", error) from error


async def _require_run(session: AsyncSession, run_id: int) -> PipelineRun:
    model = await session.get(PipelineRun, run_id, with_for_update=True)
    if model is None:
        raise PermanentJobAgentError(
            "The requested pipeline run does not exist.",
            code="pipeline.run_not_found",
            details={"run_id": run_id},
        )
    return model


def _run_snapshot(model: PipelineRun) -> PipelineRunSnapshot:
    return PipelineRunSnapshot(
        id=model.id,
        job_name=model.job_name,
        scheduled_for=model.scheduled_for,
        report_date=model.report_date,
        timezone=model.timezone,
        trigger=PipelineTrigger(model.trigger),
        status=PipelineStatus(model.status),
        current_stage=(PipelineStage(model.current_stage) if model.current_stage else None),
        started_at=model.started_at,
        finished_at=model.finished_at,
        error_code=model.error_code,
        error_message=model.error_message,
    )


def _stage_snapshot(model: PipelineStageRun) -> StageAttemptSnapshot:
    return StageAttemptSnapshot(
        id=model.id,
        pipeline_run_id=model.pipeline_run_id,
        stage=PipelineStage(model.stage),
        attempt=model.attempt,
        status=StageStatus(model.status),
        started_at=model.started_at,
        finished_at=model.finished_at,
        output=model.output,
        error_code=model.error_code,
        error_message=model.error_message,
    )


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Pipeline schedule times must be timezone-aware.")
    return value.astimezone(UTC)


def _database_error(operation: str, error: SQLAlchemyError) -> TransientJobAgentError:
    return TransientJobAgentError(
        f"Database could not {operation}.",
        code="pipeline.database_unavailable",
        details={"error_type": type(error).__name__},
    )
