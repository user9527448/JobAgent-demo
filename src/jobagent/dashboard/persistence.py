"""PostgreSQL evidence aggregation for the JAI-050 Morning Briefing."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobagent.core import TransientJobAgentError
from jobagent.core.exceptions import JsonValue
from jobagent.db.models import (
    APSchedulerJob,
    DailyReportSnapshot,
    NotificationDelivery,
    PipelineRun,
    PipelineStageRun,
)
from jobagent.jobs import DAILY_PIPELINE_JOB_NAME, PipelineStage

from .contracts import (
    BriefingSnapshot,
    DeliveryEvidence,
    DeliveryEvidenceState,
    PipelineRunEvidence,
    ReportEvidence,
    ReportItemEvidence,
    ScheduleEvidence,
    StageEvidence,
)

RECENT_RUN_LIMIT = 7
REPORT_ITEM_LIMIT = 20


class SqlAlchemyDashboardService:
    """Load a bounded, deterministic, and read-only dashboard snapshot."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        timezone: str,
        scheduler_hour: int,
        scheduler_minute: int,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._timezone = timezone
        self._zone = ZoneInfo(timezone)
        self._scheduler_hour = scheduler_hour
        self._scheduler_minute = scheduler_minute
        self._clock = clock or (lambda: datetime.now(UTC))

    async def get_briefing(self) -> BriefingSnapshot:
        """Return current evidence without creating or modifying any ledger row."""
        generated_at = self._clock().astimezone(UTC)
        try:
            async with self._session_factory() as session:
                scheduler = await self._load_scheduler(session)
                run_models = tuple(
                    await session.scalars(
                        select(PipelineRun)
                        .order_by(PipelineRun.scheduled_for.desc(), PipelineRun.id.desc())
                        .limit(RECENT_RUN_LIMIT)
                    )
                )
                stages_by_run = await self._load_latest_stages(session, run_models)
                recent_runs = tuple(
                    _run_evidence(model, stages_by_run.get(model.id, ())) for model in run_models
                )
                report_model = await session.scalar(
                    select(DailyReportSnapshot)
                    .order_by(
                        DailyReportSnapshot.report_date.desc(),
                        DailyReportSnapshot.created_at.desc(),
                        DailyReportSnapshot.id.desc(),
                    )
                    .limit(1)
                )
                report = None if report_model is None else _report_evidence(report_model)
                delivery = await self._load_delivery(session, report_model)
        except SQLAlchemyError as error:
            raise TransientJobAgentError(
                "Dashboard evidence is temporarily unavailable.",
                code="dashboard.database_unavailable",
            ) from error

        return BriefingSnapshot(
            generated_at=generated_at,
            timezone=self._timezone,
            scheduler=scheduler,
            recent_runs=recent_runs,
            missing_record_dates=self._missing_record_dates(
                generated_at,
                scheduler,
                recent_runs,
            ),
            latest_report=report,
            delivery=delivery,
        )

    async def _load_scheduler(self, session: AsyncSession) -> ScheduleEvidence:
        model = await session.get(APSchedulerJob, DAILY_PIPELINE_JOB_NAME)
        next_run_at = (
            datetime.fromtimestamp(model.next_run_time, UTC)
            if model is not None and model.next_run_time is not None
            else None
        )
        return ScheduleEvidence(
            job_id=DAILY_PIPELINE_JOB_NAME,
            present=model is not None,
            next_run_at=next_run_at,
        )

    async def _load_latest_stages(
        self,
        session: AsyncSession,
        runs: tuple[PipelineRun, ...],
    ) -> dict[int, tuple[StageEvidence, ...]]:
        run_ids = tuple(model.id for model in runs)
        if not run_ids:
            return {}
        models = tuple(
            await session.scalars(
                select(PipelineStageRun)
                .where(PipelineStageRun.pipeline_run_id.in_(run_ids))
                .order_by(
                    PipelineStageRun.pipeline_run_id,
                    PipelineStageRun.stage,
                    PipelineStageRun.attempt.desc(),
                )
            )
        )
        latest: dict[tuple[int, str], PipelineStageRun] = {}
        for model in models:
            latest.setdefault((model.pipeline_run_id, model.stage), model)

        result: dict[int, tuple[StageEvidence, ...]] = {}
        stage_order = {stage.value: index for index, stage in enumerate(PipelineStage)}
        for run_id in run_ids:
            selected = [model for (owner_id, _), model in latest.items() if owner_id == run_id]
            selected.sort(key=lambda model: stage_order.get(model.stage, len(stage_order)))
            result[run_id] = tuple(_stage_evidence(model) for model in selected)
        return result

    async def _load_delivery(
        self,
        session: AsyncSession,
        report: DailyReportSnapshot | None,
    ) -> DeliveryEvidence:
        table_name = await session.scalar(
            select(func.to_regclass("public.notification_deliveries"))
        )
        if table_name is None:
            return DeliveryEvidence(DeliveryEvidenceState.UNAVAILABLE_SCHEMA)
        if report is None:
            return DeliveryEvidence(DeliveryEvidenceState.NO_REPORT)
        model = await session.scalar(
            select(NotificationDelivery)
            .where(NotificationDelivery.report_snapshot_id == report.id)
            .order_by(NotificationDelivery.id.desc())
            .limit(1)
        )
        if model is None:
            return DeliveryEvidence(DeliveryEvidenceState.NOT_CREATED)
        return DeliveryEvidence(
            state=DeliveryEvidenceState(model.status),
            channel=model.channel,
            updated_at=model.updated_at,
            error_code=model.error_code,
        )

    def _missing_record_dates(
        self,
        generated_at: datetime,
        scheduler: ScheduleEvidence,
        runs: tuple[PipelineRunEvidence, ...],
    ) -> tuple[date, ...]:
        if not scheduler.present:
            return ()
        local_now = generated_at.astimezone(self._zone)
        scheduled_today = datetime.combine(
            local_now.date(),
            time(self._scheduler_hour, self._scheduler_minute),
            self._zone,
        )
        last_expected_date = (
            local_now.date()
            if local_now >= scheduled_today
            else local_now.date() - timedelta(days=1)
        )
        observed = {run.report_date for run in runs}
        if not observed:
            return ()
        first_expected_date = max(
            last_expected_date - timedelta(days=RECENT_RUN_LIMIT - 1),
            min(observed),
        )
        return tuple(
            candidate
            for offset in range((last_expected_date - first_expected_date).days + 1)
            if (candidate := first_expected_date + timedelta(days=offset)) not in observed
        )


def _run_evidence(
    model: PipelineRun,
    stages: tuple[StageEvidence, ...],
) -> PipelineRunEvidence:
    return PipelineRunEvidence(
        id=model.id,
        scheduled_for=model.scheduled_for,
        report_date=model.report_date,
        trigger=model.trigger,
        status=model.status,
        current_stage=model.current_stage,
        started_at=model.started_at,
        finished_at=model.finished_at,
        stages=stages,
    )


def _stage_evidence(model: PipelineStageRun) -> StageEvidence:
    return StageEvidence(
        stage=model.stage,
        attempt=model.attempt,
        status=model.status,
        started_at=model.started_at,
        finished_at=model.finished_at,
    )


def _report_evidence(model: DailyReportSnapshot) -> ReportEvidence:
    items: list[ReportItemEvidence] = []
    group_counts: dict[str, int] = {}
    sections = model.payload.get("sections")
    if isinstance(sections, list):
        for raw_section in sections:
            if not isinstance(raw_section, dict):
                continue
            group = _string(raw_section.get("group")) or "unknown"
            raw_items = raw_section.get("items")
            if not isinstance(raw_items, list):
                group_counts[group] = 0
                continue
            group_counts[group] = len(raw_items)
            for raw_item in raw_items:
                if not isinstance(raw_item, dict) or len(items) >= REPORT_ITEM_LIMIT:
                    continue
                items.append(_report_item(group, raw_item))
    return ReportEvidence(
        snapshot_id=model.id,
        report_date=model.report_date,
        report_version=model.report_version,
        created_at=model.created_at,
        item_count=sum(group_counts.values()),
        group_counts=group_counts,
        items=tuple(items),
    )


def _report_item(group: str, value: dict[str, JsonValue]) -> ReportItemEvidence:
    raw_risks = value.get("risks")
    risks = (
        tuple(item for item in raw_risks if isinstance(item, str))
        if isinstance(raw_risks, list)
        else ()
    )
    return ReportItemEvidence(
        group=group,
        position_id=_integer(value.get("position_id")),
        match_result_id=_integer(value.get("match_result_id")),
        organization=_string(value.get("organization")),
        title=_string(value.get("title")),
        region=_string(value.get("region")),
        deadline=_string(value.get("deadline")),
        score=_integer(value.get("score")),
        reason=_string(value.get("reason")),
        risks=risks,
        source_url=_string(value.get("source_url")),
    )


def _string(value: JsonValue | None) -> str | None:
    return value if isinstance(value, str) else None


def _integer(value: JsonValue | None) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None
