"""FastAPI application factory and lifecycle."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from jobagent import __version__
from jobagent.api.routes.extraction import router as extraction_router
from jobagent.api.routes.health import router as health_router
from jobagent.api.routes.preferences import router as preferences_router
from jobagent.api.routes.reports import router as reports_router
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
from jobagent.preferences import PreferenceOperations, SqlAlchemyPreferenceRepository
from jobagent.reports import DailyReportOperations, SqlAlchemyDailyReportService


def create_app(
    settings: Settings | None = None,
    database: DatabaseHealth | None = None,
    reparse_service: ReparseOperations | None = None,
    preference_service: PreferenceOperations | None = None,
    report_service: DailyReportOperations | None = None,
) -> FastAPI:
    """Create an application with explicitly injectable infrastructure."""
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings)
    resolved_database = database or create_database(resolved_settings)
    resolved_reparse_service = reparse_service or _default_reparse_service(
        resolved_settings,
        resolved_database,
    )
    resolved_preference_service = preference_service or _default_preference_service(
        resolved_database
    )
    resolved_report_service = report_service or _default_report_service(
        resolved_database,
        resolved_settings.timezone,
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
    app.state.preference_service = resolved_preference_service
    app.state.report_service = resolved_report_service
    app.include_router(health_router, prefix="/health", tags=["health"])
    app.include_router(extraction_router, prefix="/extraction", tags=["extraction"])
    app.include_router(preferences_router, prefix="/preferences", tags=["preferences"])
    app.include_router(reports_router, prefix="/reports", tags=["reports"])
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


def _default_preference_service(
    database: DatabaseHealth,
) -> PreferenceOperations | None:
    if not isinstance(database, Database):
        return None
    return SqlAlchemyPreferenceRepository(database.session_factory)


def _default_report_service(
    database: DatabaseHealth,
    timezone: str,
) -> DailyReportOperations | None:
    if not isinstance(database, Database):
        return None
    return SqlAlchemyDailyReportService(database.session_factory, timezone)
