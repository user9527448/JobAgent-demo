"""Production adapters for collection, extraction, matching, and reporting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from sqlalchemy import exists, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobagent.core import JobAgentError, PermanentJobAgentError, Settings, TransientJobAgentError
from jobagent.core.exceptions import JsonValue
from jobagent.crawlers import (
    CollectionOrchestrator,
    HttpSourcePolicy,
    SourceHttpClient,
    SqlAlchemyCrawlRunRepository,
    SqlAlchemyRawDocumentRepository,
    build_adapter_registry,
    load_source_catalog,
    match_catalog_entry,
)
from jobagent.crawlers.contracts import SourceDefinition
from jobagent.db.models import JobPost, RawDocument, Source
from jobagent.extraction import (
    DeterministicFieldExtractor,
    ExtractionMerger,
    ExtractionPolicy,
    ReparseService,
    SqlAlchemyExtractionRepository,
    StoredDocumentReparsePipeline,
)
from jobagent.matching import CURRENT_SCORE_VERSION, SqlAlchemyMatchingService
from jobagent.parsers import build_parser_registry
from jobagent.reports import SqlAlchemyDailyReportService

from .contracts import PipelineStage, StageOutcome, StageStatus
from .pipeline import PipelineContext

SCHEDULED_EXTRACTION_VERSION = "jai-026-v1"
SCHEDULER_USER_AGENT = (
    "JOBAGENT/0.1 (+personal recruitment intelligence; scheduled public-source run)"
)


@dataclass(frozen=True, slots=True)
class _SourceFailure:
    source_id: int
    code: str
    retryable: bool

    def as_json(self) -> dict[str, JsonValue]:
        return {
            "source_id": self.source_id,
            "code": self.code,
            "retryable": self.retryable,
        }


class ProductionPipelineStages:
    """Connect the durable coordinator to existing application services."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings,
    ) -> None:
        self._session_factory = session_factory
        self._settings = settings
        pipeline = StoredDocumentReparsePipeline(
            session_factory,
            settings.attachment_storage_path,
            build_parser_registry(),
            DeterministicFieldExtractor(ExtractionPolicy(timezone=settings.timezone)),
            ExtractionMerger(),
        )
        self._reparse = ReparseService(
            pipeline,
            SqlAlchemyExtractionRepository(session_factory),
        )
        self._matching = SqlAlchemyMatchingService(session_factory)
        self._reports = SqlAlchemyDailyReportService(session_factory, settings.timezone)

    async def run(self, stage: PipelineStage, context: PipelineContext) -> StageOutcome:
        operations = {
            PipelineStage.COLLECTION: self._collect,
            PipelineStage.EXTRACTION: self._extract,
            PipelineStage.MATCHING: self._match,
            PipelineStage.REPORT: self._report,
        }
        return await operations[stage](context)

    async def _collect(self, context: PipelineContext) -> StageOutcome:
        del context
        sources = await self._enabled_sources()
        if not sources:
            raise PermanentJobAgentError(
                "No enabled sources are configured for the daily pipeline.",
                code="pipeline.sources_empty",
            )
        catalog = load_source_catalog(self._settings.source_catalog_path)
        run_ids: list[int] = []
        failures: list[_SourceFailure] = []
        partial_sources = 0
        successful_sources = 0
        for source in sources:
            try:
                entry = match_catalog_entry(catalog, source)
                policy = HttpSourcePolicy(
                    source_id=source.id,
                    user_agent=SCHEDULER_USER_AGENT,
                    min_interval_seconds=1.0,
                    max_concurrency=1,
                )
                async with SourceHttpClient(policy) as http_client:
                    result = await CollectionOrchestrator(
                        build_adapter_registry(source, entry, http_client),
                        SqlAlchemyCrawlRunRepository(self._session_factory),
                        SqlAlchemyRawDocumentRepository(self._session_factory),
                    ).run(source.id)
                run_ids.append(result.run_id)
                if result.status == "succeeded":
                    successful_sources += 1
                else:
                    partial_sources += 1
            except JobAgentError as error:
                failures.append(_SourceFailure(source.id, error.code, error.retryable))

        output: dict[str, JsonValue] = {
            "source_count": len(sources),
            "successful_sources": successful_sources,
            "partial_sources": partial_sources,
            "crawl_run_ids": cast(list[JsonValue], run_ids),
            "failures": cast(list[JsonValue], [failure.as_json() for failure in failures]),
        }
        if any(failure.retryable for failure in failures):
            raise TransientJobAgentError(
                "One or more source collection attempts failed temporarily.",
                code="pipeline.collection_transient",
                details=output,
            )
        if failures and not (successful_sources or partial_sources):
            raise PermanentJobAgentError(
                "All enabled source collection attempts failed permanently.",
                code="pipeline.collection_failed",
                details=output,
            )
        status = StageStatus.PARTIAL if failures or partial_sources else StageStatus.SUCCEEDED
        return StageOutcome(status, output)

    async def _extract(self, context: PipelineContext) -> StageOutcome:
        del context
        document_ids = await self._pending_document_ids()
        post_ids: list[int] = []
        position_ids: list[int] = []
        permanent_failures: list[dict[str, JsonValue]] = []
        transient_failures: list[dict[str, JsonValue]] = []
        for document_id in document_ids:
            try:
                result = await self._reparse.reparse(
                    document_id,
                    SCHEDULED_EXTRACTION_VERSION,
                )
            except JobAgentError as error:
                failure: dict[str, JsonValue] = {
                    "document_id": document_id,
                    "code": error.code,
                    "retryable": error.retryable,
                }
                (transient_failures if error.retryable else permanent_failures).append(failure)
            else:
                post_ids.append(result.post_id)
                position_ids.extend(result.position_ids)

        output: dict[str, JsonValue] = {
            "input_document_ids": cast(list[JsonValue], document_ids),
            "post_ids": cast(list[JsonValue], post_ids),
            "position_ids": cast(list[JsonValue], position_ids),
            "extraction_version": SCHEDULED_EXTRACTION_VERSION,
            "permanent_failures": cast(list[JsonValue], permanent_failures),
            "transient_failures": cast(list[JsonValue], transient_failures),
        }
        if transient_failures:
            raise TransientJobAgentError(
                "One or more documents could not be extracted temporarily.",
                code="pipeline.extraction_transient",
                details=output,
            )
        return StageOutcome(
            StageStatus.PARTIAL if permanent_failures else StageStatus.SUCCEEDED,
            output,
        )

    async def _match(self, context: PipelineContext) -> StageOutcome:
        result = await self._matching.recompute_if_requested(
            evaluated_at=context.scheduled_for,
            score_version=CURRENT_SCORE_VERSION,
            force=True,
        )
        return StageOutcome(
            StageStatus.SUCCEEDED,
            {
                "score_version": result.score_version,
                "evaluated_at": result.evaluated_at.isoformat(),
                "result_ids": list(result.result_ids),
                "processed_count": result.processed_count,
                "passed_count": result.passed_count,
                "filtered_count": result.filtered_count,
                "created_count": result.created_count,
                "unchanged_count": result.unchanged_count,
            },
        )

    async def _report(self, context: PipelineContext) -> StageOutcome:
        snapshot = await self._reports.generate(context.report_date)
        return StageOutcome(
            StageStatus.SUCCEEDED,
            {
                "report_snapshot_id": snapshot.id,
                "report_version": snapshot.report.report_version,
                "content_hash": snapshot.content_hash,
            },
        )

    async def _enabled_sources(self) -> tuple[SourceDefinition, ...]:
        try:
            async with self._session_factory() as session:
                models = await session.scalars(
                    select(Source).where(Source.enabled.is_(True)).order_by(Source.id)
                )
                return tuple(
                    SourceDefinition(
                        id=model.id,
                        name=model.name,
                        base_url=model.base_url,
                        category=model.category,
                        adapter=model.adapter,
                        enabled=model.enabled,
                    )
                    for model in models
                )
        except SQLAlchemyError as error:
            raise TransientJobAgentError(
                "Enabled sources could not be loaded.",
                code="pipeline.sources_unavailable",
            ) from error

    async def _pending_document_ids(self) -> list[int]:
        already_extracted = exists(
            select(JobPost.id).where(
                JobPost.document_id == RawDocument.id,
                JobPost.extraction_version == SCHEDULED_EXTRACTION_VERSION,
            )
        )
        try:
            async with self._session_factory() as session:
                return list(
                    await session.scalars(
                        select(RawDocument.id)
                        .where(RawDocument.is_current.is_(True), ~already_extracted)
                        .order_by(RawDocument.id)
                    )
                )
        except SQLAlchemyError as error:
            raise TransientJobAgentError(
                "Pending extraction documents could not be loaded.",
                code="pipeline.documents_unavailable",
            ) from error
