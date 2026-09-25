"""Stable read-only contracts consumed by the JAI-050 dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Protocol


class DeliveryEvidenceState(StrEnum):
    """Safe capability and ledger states exposed to the dashboard."""

    UNAVAILABLE_SCHEMA = "unavailable_schema"
    NO_REPORT = "no_report"
    NOT_CREATED = "not_created"
    PENDING = "pending"
    SENDING = "sending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ScheduleEvidence:
    """Evidence from the fixed APScheduler job-store row."""

    job_id: str
    present: bool
    next_run_at: datetime | None


@dataclass(frozen=True, slots=True)
class StageEvidence:
    """Latest persisted attempt for one stage of a pipeline run."""

    stage: str
    attempt: int
    status: str
    started_at: datetime
    finished_at: datetime | None


@dataclass(frozen=True, slots=True)
class PipelineRunEvidence:
    """One bounded run summary with its latest stage attempts."""

    id: int
    scheduled_for: datetime
    report_date: date
    trigger: str
    status: str
    current_stage: str | None
    started_at: datetime | None
    finished_at: datetime | None
    stages: tuple[StageEvidence, ...]


@dataclass(frozen=True, slots=True)
class ReportItemEvidence:
    """One ordered item from the immutable report payload."""

    group: str
    position_id: int | None
    match_result_id: int | None
    organization: str | None
    title: str | None
    region: str | None
    deadline: str | None
    score: int | None
    reason: str | None
    risks: tuple[str, ...]
    source_url: str | None


@dataclass(frozen=True, slots=True)
class ReportEvidence:
    """Latest immutable report plus bounded ordered items."""

    snapshot_id: int
    report_date: date
    report_version: str
    created_at: datetime
    item_count: int
    group_counts: dict[str, int]
    items: tuple[ReportItemEvidence, ...]


@dataclass(frozen=True, slots=True)
class DeliveryEvidence:
    """Safe delivery state without provider payloads or raw error text."""

    state: DeliveryEvidenceState
    channel: str | None = None
    updated_at: datetime | None = None
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class BriefingSnapshot:
    """Complete bounded evidence snapshot for the Morning Briefing."""

    generated_at: datetime
    timezone: str
    scheduler: ScheduleEvidence
    recent_runs: tuple[PipelineRunEvidence, ...]
    missing_record_dates: tuple[date, ...]
    latest_report: ReportEvidence | None
    delivery: DeliveryEvidence


class DashboardOperations(Protocol):
    """Application-facing read boundary for the product dashboard."""

    async def get_briefing(self) -> BriefingSnapshot: ...
