"""Read-only Morning Briefing endpoint."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict

from jobagent.api.dependencies import get_dashboard_service
from jobagent.core import TransientJobAgentError
from jobagent.dashboard import DashboardOperations, DeliveryEvidenceState

router = APIRouter()


class DashboardModel(BaseModel):
    """Shared attribute-based Pydantic conversion configuration."""

    model_config = ConfigDict(from_attributes=True)


class ScheduleEvidenceResponse(DashboardModel):
    job_id: str
    present: bool
    next_run_at: datetime | None


class StageEvidenceResponse(DashboardModel):
    stage: str
    attempt: int
    status: str
    started_at: datetime
    finished_at: datetime | None


class PipelineRunEvidenceResponse(DashboardModel):
    id: int
    scheduled_for: datetime
    report_date: date
    trigger: str
    status: str
    current_stage: str | None
    started_at: datetime | None
    finished_at: datetime | None
    stages: tuple[StageEvidenceResponse, ...]


class ReportItemEvidenceResponse(DashboardModel):
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


class ReportEvidenceResponse(DashboardModel):
    snapshot_id: int
    report_date: date
    report_version: str
    created_at: datetime
    item_count: int
    group_counts: dict[str, int]
    items: tuple[ReportItemEvidenceResponse, ...]


class DeliveryEvidenceResponse(DashboardModel):
    state: DeliveryEvidenceState
    channel: str | None
    updated_at: datetime | None
    error_code: str | None


class DashboardBriefingResponse(DashboardModel):
    generated_at: datetime
    timezone: str
    scheduler: ScheduleEvidenceResponse
    recent_runs: tuple[PipelineRunEvidenceResponse, ...]
    missing_record_dates: tuple[date, ...]
    latest_report: ReportEvidenceResponse | None
    delivery: DeliveryEvidenceResponse


@router.get("/briefing", response_model=DashboardBriefingResponse)
async def read_briefing(
    service: Annotated[DashboardOperations, Depends(get_dashboard_service)],
) -> DashboardBriefingResponse:
    """Return a bounded snapshot of persisted operational evidence."""
    try:
        snapshot = await service.get_briefing()
    except TransientJobAgentError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": error.code,
                "message": "Dashboard evidence is temporarily unavailable.",
                "category": "transient",
                "retryable": True,
            },
        ) from error
    return DashboardBriefingResponse.model_validate(snapshot)
