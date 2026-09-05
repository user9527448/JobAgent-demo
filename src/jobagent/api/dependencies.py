"""FastAPI dependency providers."""

from typing import cast

from fastapi import HTTPException, Request, status

from jobagent.db import DatabaseHealth
from jobagent.extraction.reparse import ReparseOperations
from jobagent.preferences import PreferenceOperations
from jobagent.reports import DailyReportOperations


def get_database(request: Request) -> DatabaseHealth:
    """Return the application-scoped database service."""
    return cast(DatabaseHealth, request.app.state.database)


def get_reparse_service(request: Request) -> ReparseOperations:
    """Return reparsing operations or an explicit service-unavailable response."""
    service = cast(ReparseOperations | None, request.app.state.reparse_service)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "reparse.service_unavailable",
                "message": "Reparse service is unavailable for this application instance.",
            },
        )
    return service


def get_preference_service(request: Request) -> PreferenceOperations:
    """Return preference operations or an explicit service-unavailable response."""
    service = cast(PreferenceOperations | None, request.app.state.preference_service)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "preferences.service_unavailable",
                "message": "Preference service is unavailable for this application instance.",
            },
        )
    return service


def get_report_service(request: Request) -> DailyReportOperations:
    """Return daily-report operations or an explicit unavailable response."""
    service = cast(DailyReportOperations | None, request.app.state.report_service)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "reports.service_unavailable",
                "message": "Daily report service is unavailable for this application instance.",
            },
        )
    return service
