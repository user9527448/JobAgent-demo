"""Daily report generation, snapshot lookup, and rendering endpoints."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel

from jobagent.api.dependencies import get_report_service
from jobagent.core import PermanentJobAgentError, TransientJobAgentError
from jobagent.reports import DailyReportOperations, DailyReportSnapshot

router = APIRouter()


class DailyReportGenerateRequest(BaseModel):
    """Explicit local calendar date used as a deterministic report input."""

    report_date: date


class DailyReportSnapshotResponse(BaseModel):
    """Persisted structured report plus both stable renderings."""

    snapshot_id: int
    content_hash: str
    report: dict[str, object]
    markdown: str
    html: str
    created_at: datetime

    @classmethod
    def from_snapshot(cls, snapshot: DailyReportSnapshot) -> DailyReportSnapshotResponse:
        return cls(
            snapshot_id=snapshot.id,
            content_hash=snapshot.content_hash,
            report=cast(dict[str, object], snapshot.report.as_json()),
            markdown=snapshot.markdown,
            html=snapshot.html,
            created_at=snapshot.created_at,
        )


@router.post("/daily", response_model=DailyReportSnapshotResponse)
async def generate_daily_report(
    request: DailyReportGenerateRequest,
    service: Annotated[DailyReportOperations, Depends(get_report_service)],
) -> DailyReportSnapshotResponse:
    """Generate or idempotently reuse the report snapshot for one date."""
    try:
        snapshot = await service.generate(request.report_date)
    except (PermanentJobAgentError, TransientJobAgentError) as error:
        raise _report_http_error(error) from error
    return DailyReportSnapshotResponse.from_snapshot(snapshot)


@router.get("/daily/{snapshot_id}", response_model=DailyReportSnapshotResponse)
async def read_daily_report(
    snapshot_id: Annotated[int, Path(gt=0)],
    service: Annotated[DailyReportOperations, Depends(get_report_service)],
) -> DailyReportSnapshotResponse:
    """Read an immutable report snapshot without recomputing current data."""
    try:
        snapshot = await service.get(snapshot_id)
    except (PermanentJobAgentError, TransientJobAgentError) as error:
        raise _report_http_error(error) from error
    return DailyReportSnapshotResponse.from_snapshot(snapshot)


@router.get("/daily/{snapshot_id}/markdown", response_class=PlainTextResponse)
async def read_daily_report_markdown(
    snapshot_id: Annotated[int, Path(gt=0)],
    service: Annotated[DailyReportOperations, Depends(get_report_service)],
) -> PlainTextResponse:
    """Read the exact persisted Markdown rendering."""
    try:
        snapshot = await service.get(snapshot_id)
    except (PermanentJobAgentError, TransientJobAgentError) as error:
        raise _report_http_error(error) from error
    return PlainTextResponse(snapshot.markdown, media_type="text/markdown")


@router.get("/daily/{snapshot_id}/html", response_class=HTMLResponse)
async def read_daily_report_html(
    snapshot_id: Annotated[int, Path(gt=0)],
    service: Annotated[DailyReportOperations, Depends(get_report_service)],
) -> HTMLResponse:
    """Read the exact persisted, escaped HTML rendering."""
    try:
        snapshot = await service.get(snapshot_id)
    except (PermanentJobAgentError, TransientJobAgentError) as error:
        raise _report_http_error(error) from error
    return HTMLResponse(snapshot.html)


def _report_http_error(
    error: PermanentJobAgentError | TransientJobAgentError,
) -> HTTPException:
    if isinstance(error, TransientJobAgentError):
        response_status = status.HTTP_503_SERVICE_UNAVAILABLE
    elif error.code == "reports.snapshot_not_found":
        response_status = status.HTTP_404_NOT_FOUND
    else:
        response_status = status.HTTP_409_CONFLICT
    return HTTPException(status_code=response_status, detail=error.to_dict())
