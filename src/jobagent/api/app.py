"""FastAPI application factory and lifecycle."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from jobagent import __version__
from jobagent.api.routes.health import router as health_router
from jobagent.core import Settings, configure_logging, get_logger, get_settings
from jobagent.db import DatabaseHealth, create_database


def create_app(
    settings: Settings | None = None,
    database: DatabaseHealth | None = None,
) -> FastAPI:
    """Create an application with explicitly injectable infrastructure."""
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings)
    resolved_database = database or create_database(resolved_settings)
    logger = get_logger(__name__)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "application.started",
            extra={"app_name": resolved_settings.app_name, "version": __version__},
        )
        try:
            yield
        finally:
            await resolved_database.close()
            logger.info("application.stopped")

    app = FastAPI(
        title="JOBAGENT API",
        version=__version__,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.database = resolved_database
    app.include_router(health_router, prefix="/health", tags=["health"])
    return app
