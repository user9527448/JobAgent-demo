"""Typed contracts for durable daily pipeline execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from jobagent.core.exceptions import JsonValue

DAILY_PIPELINE_JOB_NAME = "jobagent.daily-pipeline.v1"


class PipelineTrigger(StrEnum):
    """Supported ways to request one logical pipeline run."""

    SCHEDULED = "scheduled"
    MAKEUP = "makeup"


class PipelineStatus(StrEnum):
    """Durable lifecycle of a logical pipeline run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineStage(StrEnum):
    """Fixed, ordered stages in the MVP daily pipeline."""

    COLLECTION = "collection"
    EXTRACTION = "extraction"
    MATCHING = "matching"
    REPORT = "report"


PIPELINE_STAGE_ORDER = (
    PipelineStage.COLLECTION,
    PipelineStage.EXTRACTION,
    PipelineStage.MATCHING,
    PipelineStage.REPORT,
)


class StageStatus(StrEnum):
    """Durable lifecycle of one numbered stage attempt."""

    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class DispatchStatus(StrEnum):
    """Immediate outcome of trying to dispatch one logical run."""

    EXECUTED = "executed"
    REUSED = "reused"
    LOCKED = "locked"


@dataclass(frozen=True, slots=True)
class PipelineRunSnapshot:
    """Safe persisted view of one logical pipeline run."""

    id: int
    job_name: str
    scheduled_for: datetime
    report_date: date
    timezone: str
    trigger: PipelineTrigger
    status: PipelineStatus
    current_stage: PipelineStage | None
    started_at: datetime | None
    finished_at: datetime | None
    error_code: str | None
    error_message: str | None

    def as_json(self) -> dict[str, JsonValue]:
        """Return a stable JSON-safe operator payload."""
        return {
            "id": self.id,
            "job_name": self.job_name,
            "scheduled_for": self.scheduled_for.isoformat(),
            "report_date": self.report_date.isoformat(),
            "timezone": self.timezone,
            "trigger": self.trigger.value,
            "status": self.status.value,
            "current_stage": self.current_stage.value if self.current_stage else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "error_code": self.error_code,
            "error_message": self.error_message,
        }


@dataclass(frozen=True, slots=True)
class StageAttemptSnapshot:
    """Safe persisted view of one stage attempt."""

    id: int
    pipeline_run_id: int
    stage: PipelineStage
    attempt: int
    status: StageStatus
    started_at: datetime
    finished_at: datetime | None
    output: dict[str, JsonValue]
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True, slots=True)
class StageOutcome:
    """Successful or partial stage output ready for durable completion."""

    status: StageStatus
    output: dict[str, JsonValue]

    def __post_init__(self) -> None:
        if self.status not in {StageStatus.SUCCEEDED, StageStatus.PARTIAL}:
            raise ValueError("Stage outcomes must be succeeded or partial.")


@dataclass(frozen=True, slots=True)
class PipelineExecutionResult:
    """Dispatch result returned to scheduler and manual command boundaries."""

    dispatch_status: DispatchStatus
    run: PipelineRunSnapshot | None

    def as_json(self) -> dict[str, JsonValue]:
        return {
            "dispatch_status": self.dispatch_status.value,
            "run": None if self.run is None else self.run.as_json(),
        }
