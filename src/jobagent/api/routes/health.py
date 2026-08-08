"""Liveness and readiness endpoints."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel

from jobagent.api.dependencies import get_database
from jobagent.core import JobAgentError, get_logger
from jobagent.db import DatabaseHealth

router = APIRouter()
logger = get_logger(__name__)


class HealthResponse(BaseModel):
    """Stable health response contract."""

    status: Literal["alive", "ready", "not_ready"]
    checks: dict[str, str] | None = None


@router.get("/live", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    """Report process liveness without contacting dependencies."""
    return HealthResponse(status="alive")


@router.get("/ready", response_model=HealthResponse)
async def readiness(
    response: Response,
    database: Annotated[DatabaseHealth, Depends(get_database)],
) -> HealthResponse:
    """Report whether required dependencies can serve application traffic."""
    try:
        await database.ping()
    except JobAgentError as error:
        logger.warning(
            "health.database_unavailable",
            extra={"error_code": error.code, "retryable": error.retryable},
        )
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="not_ready", checks={"database": "unavailable"})

    return HealthResponse(status="ready", checks={"database": "available"})
