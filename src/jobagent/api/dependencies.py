"""FastAPI dependency providers."""

from typing import cast

from fastapi import Request

from jobagent.db import DatabaseHealth


def get_database(request: Request) -> DatabaseHealth:
    """Return the application-scoped database service."""
    return cast(DatabaseHealth, request.app.state.database)
