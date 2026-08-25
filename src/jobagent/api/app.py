"""FastAPI application factory and lifecycle."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from jobagent import __version__
from jobagent.api.routes.extraction import router as extraction_router
from jobagent.api.routes.health import router as health_router
from jobagent.core import Settings, configure_logging, get_logger, get_settings
from jobagent.db import Database, DatabaseHealth, create_database
from jobagent.extraction import (
    DeterministicFieldExtractor,
    ExtractionMerger,
    ExtractionPolicy,
    ReparseOperations,
    ReparseService,
    SqlAlchemyExtractionRepository,
    StoredDocumentReparsePipeline,
)
from jobagent.parsers import build_parser_registry


def create_app(
    settings: Settings | None = None,
    database: DatabaseHealth | None = None,
    reparse_service: ReparseOperations | None = None,
) -> FastAPI:
    """Create an application with explicitly injectable infrastructure."""
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings)
    resolved_database = database or create_database(resolved_settings)
    resolved_reparse_service = reparse_service or _default_reparse_service(
        resolved_settings,
        resolved_database,
    )
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
    app.state.reparse_service = resolved_reparse_service
    app.include_router(health_router, prefix="/health", tags=["health"])
    app.include_router(extraction_router, prefix="/extraction", tags=["extraction"])
    return app


def _default_reparse_service(
    settings: Settings,
    database: DatabaseHealth,
) -> ReparseOperations | None:
    if not isinstance(database, Database):
        return None
    pipeline = StoredDocumentReparsePipeline(
        database.session_factory,
        settings.attachment_storage_path,
        build_parser_registry(),
        DeterministicFieldExtractor(ExtractionPolicy(timezone=settings.timezone)),
        ExtractionMerger(),
    )
    return ReparseService(
        pipeline,
        SqlAlchemyExtractionRepository(database.session_factory),
    )
