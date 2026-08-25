"""Version-preserving PostgreSQL persistence for merged extraction results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobagent.core.exceptions import PermanentJobAgentError, TransientJobAgentError
from jobagent.db.models import (
    Attachment,
    FieldEvidence,
    JobPosition,
    JobPost,
    RawDocument,
    ValidationIssue,
)
from jobagent.extraction.contracts import FieldName
from jobagent.extraction.merging import (
    MergedEntityType,
    MergedEvidence,
    MergedExtraction,
    MergedField,
    normalized_json_value,
)
from jobagent.parsers import CellRangeLocation, LineRangeLocation, PageLocation, ParseSourceType

from .validation import ExtractionValidator, ReviewStatus, ValidationResult


class ExtractionWriteStatus(StrEnum):
    """Observable outcome of one versioned extraction persistence request."""

    CREATED = "created"
    UNCHANGED = "unchanged"


@dataclass(frozen=True, slots=True)
class ExtractionWriteResult:
    """Persisted entity identities and version outcome."""

    post_id: int
    position_ids: tuple[int, ...]
    version: int
    extraction_version: str
    result_hash: str
    status: ExtractionWriteStatus
    previous_post_id: int | None
    review_status: ReviewStatus
    recommendation_eligible: bool
    validation_version: str
    validation_error_count: int
    validation_warning_count: int


class SqlAlchemyExtractionRepository:
    """Append extraction versions atomically while retaining prior evidence."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        validator: ExtractionValidator | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._validator = validator or ExtractionValidator()

    async def save(self, merged: MergedExtraction) -> ExtractionWriteResult:
        """Create or idempotently reuse one merged extraction version."""
        post_values = _post_values(merged.post_fields)
        _validate_date_range(post_values)
        validation = self._validator.validate(merged)
        try:
            async with self._session_factory() as session, session.begin():
                await session.execute(select(func.pg_advisory_xact_lock(merged.document_id)))
                document = await session.get(RawDocument, merged.document_id)
                if document is None:
                    raise PermanentJobAgentError(
                        "The extraction source document does not exist.",
                        code="extraction.document_not_found",
                        details={"document_id": merged.document_id},
                    )
                await _validate_attachment_sources(session, merged)

                existing = await session.scalar(
                    select(JobPost).where(
                        JobPost.document_id == merged.document_id,
                        JobPost.extraction_version == merged.extraction_version,
                    )
                )
                if existing is not None:
                    if existing.result_hash != merged.result_hash:
                        raise PermanentJobAgentError(
                            "The same extraction version produced a different result.",
                            code="extraction.version_not_deterministic",
                            details={
                                "document_id": merged.document_id,
                                "extraction_version": merged.extraction_version,
                            },
                        )
                    position_ids = tuple(
                        await session.scalars(
                            select(JobPosition.id)
                            .where(JobPosition.post_id == existing.id)
                            .order_by(JobPosition.record_key)
                        )
                    )
                    counts = await _validation_counts(session, existing.id)
                    return ExtractionWriteResult(
                        post_id=existing.id,
                        position_ids=position_ids,
                        version=existing.version,
                        extraction_version=existing.extraction_version,
                        result_hash=existing.result_hash,
                        status=ExtractionWriteStatus.UNCHANGED,
                        previous_post_id=existing.supersedes_id,
                        review_status=ReviewStatus(existing.review_status),
                        recommendation_eligible=existing.recommendation_eligible,
                        validation_version=existing.validation_version,
                        validation_error_count=counts[0],
                        validation_warning_count=counts[1],
                    )

                current = await session.scalar(
                    select(JobPost)
                    .where(
                        JobPost.document_id == merged.document_id,
                        JobPost.is_current.is_(True),
                    )
                    .with_for_update()
                )
                version = 1 if current is None else current.version + 1
                previous_post_id = None if current is None else current.id
                if current is not None:
                    current.is_current = False

                post = JobPost(
                    document_id=merged.document_id,
                    extraction_version=merged.extraction_version,
                    version=version,
                    is_current=True,
                    supersedes_id=previous_post_id,
                    result_hash=merged.result_hash,
                    review_status=validation.review_status.value,
                    recommendation_eligible=validation.recommendation_eligible,
                    validation_version=validation.validation_version,
                    validated_at=datetime.now(UTC),
                    **post_values,
                )
                session.add(post)
                await session.flush()
                _add_validation_issues(session, post.id, validation)

                position_rows: list[tuple[JobPosition, tuple[MergedField, ...]]] = []
                for position in merged.positions:
                    values = _position_values(position.fields)
                    row = JobPosition(
                        post_id=post.id,
                        record_key=position.record_key,
                        name=None,
                        **values,
                    )
                    session.add(row)
                    position_rows.append((row, position.fields))
                await session.flush()

                _add_evidence(
                    session,
                    entity_type=MergedEntityType.JOB_POST,
                    entity_id=post.id,
                    fields=merged.post_fields,
                )
                for row, fields in position_rows:
                    _add_evidence(
                        session,
                        entity_type=MergedEntityType.JOB_POSITION,
                        entity_id=row.id,
                        fields=fields,
                    )
                return ExtractionWriteResult(
                    post_id=post.id,
                    position_ids=tuple(row.id for row, _fields in position_rows),
                    version=version,
                    extraction_version=merged.extraction_version,
                    result_hash=merged.result_hash,
                    status=ExtractionWriteStatus.CREATED,
                    previous_post_id=previous_post_id,
                    review_status=validation.review_status,
                    recommendation_eligible=validation.recommendation_eligible,
                    validation_version=validation.validation_version,
                    validation_error_count=validation.error_count,
                    validation_warning_count=validation.warning_count,
                )
        except SQLAlchemyError as error:
            raise TransientJobAgentError(
                "The database could not persist merged extraction results.",
                code="database.extraction_unavailable",
                details={"error_type": type(error).__name__},
            ) from error


async def _validate_attachment_sources(session: AsyncSession, merged: MergedExtraction) -> None:
    attachment_ids = {
        evidence.location.source.source_id
        for field in merged.post_fields
        for evidence in field.evidence
        if evidence.location.source.source_type is ParseSourceType.ATTACHMENT
    }
    attachment_ids.update(
        evidence.location.source.source_id
        for position in merged.positions
        for field in position.fields
        for evidence in field.evidence
        if evidence.location.source.source_type is ParseSourceType.ATTACHMENT
    )
    if not attachment_ids:
        return
    valid_ids = set(
        await session.scalars(
            select(Attachment.id).where(
                Attachment.id.in_(attachment_ids),
                Attachment.document_id == merged.document_id,
            )
        )
    )
    if valid_ids != attachment_ids:
        raise PermanentJobAgentError(
            "Extraction evidence references an attachment from another document.",
            code="extraction.attachment_source_mismatch",
            details={"document_id": merged.document_id},
        )


def _post_values(fields: tuple[MergedField, ...]) -> dict[str, object]:
    values = {field.name: field.normalized_value for field in fields}
    return {
        "organization": _text_value(values.get(FieldName.ORGANIZATION)),
        "category": _text_value(values.get(FieldName.CATEGORY)),
        "region": _region_value(values.get(FieldName.REGION)),
        "apply_url": _text_value(values.get(FieldName.APPLY_URL)),
        "start_at": _datetime_value(values.get(FieldName.START_AT)),
        "deadline": _datetime_value(values.get(FieldName.DEADLINE)),
    }


def _position_values(fields: tuple[MergedField, ...]) -> dict[str, object]:
    values = {field.name: field.normalized_value for field in fields}
    headcount = values.get(FieldName.HEADCOUNT)
    return {
        "location": _region_value(values.get(FieldName.REGION)),
        "education": _text_value(values.get(FieldName.EDUCATION)),
        "headcount": headcount if isinstance(headcount, int) else None,
    }


def _validate_date_range(values: dict[str, object]) -> None:
    start_at = values["start_at"]
    deadline = values["deadline"]
    if isinstance(start_at, datetime) and isinstance(deadline, datetime) and start_at > deadline:
        raise PermanentJobAgentError(
            "Merged application start is later than its deadline.",
            code="extraction.merged_date_range_invalid",
        )


def _text_value(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _region_value(value: object) -> str | None:
    if isinstance(value, tuple) and all(isinstance(item, str) for item in value):
        return ",".join(value)
    return value if isinstance(value, str) else None


def _datetime_value(value: object) -> datetime | None:
    return value if isinstance(value, datetime) else None


def _add_evidence(
    session: AsyncSession,
    *,
    entity_type: MergedEntityType,
    entity_id: int,
    fields: tuple[MergedField, ...],
) -> None:
    for field in fields:
        for evidence in field.evidence:
            location_values = _location_values(evidence)
            source = evidence.location.source
            session.add(
                FieldEvidence(
                    entity_type=entity_type.value,
                    entity_id=entity_id,
                    field_name=field.name.value,
                    source_type=source.source_type.value,
                    source_document_id=(
                        source.source_id if source.source_type is ParseSourceType.DOCUMENT else None
                    ),
                    source_attachment_id=(
                        source.source_id
                        if source.source_type is ParseSourceType.ATTACHMENT
                        else None
                    ),
                    raw_value=evidence.raw_value,
                    normalized_value=normalized_json_value(evidence.normalized_value),
                    extraction_method=evidence.method.value,
                    extraction_version=evidence.extractor_version,
                    is_selected=evidence.selected,
                    conflict=evidence.conflict,
                    quote_text=evidence.quote,
                    confidence=evidence.confidence,
                    **location_values,
                )
            )


def _add_validation_issues(
    session: AsyncSession,
    post_id: int,
    validation: ValidationResult,
) -> None:
    for finding in validation.findings:
        session.add(
            ValidationIssue(
                post_id=post_id,
                issue_key=finding.issue_key,
                code=finding.code.value,
                severity=finding.severity.value,
                entity_type=finding.entity_type.value,
                entity_key=finding.entity_key,
                field_name=None if finding.field_name is None else finding.field_name.value,
                reason=finding.reason,
            )
        )


async def _validation_counts(session: AsyncSession, post_id: int) -> tuple[int, int]:
    rows = (
        await session.execute(
            select(ValidationIssue.severity, func.count())
            .where(ValidationIssue.post_id == post_id)
            .group_by(ValidationIssue.severity)
        )
    ).all()
    error_count = sum(count for severity, count in rows if severity == "error")
    warning_count = sum(count for severity, count in rows if severity == "warning")
    return error_count, warning_count


def _location_values(evidence: MergedEvidence) -> dict[str, object]:
    location = evidence.location
    if isinstance(location, PageLocation):
        return {
            "page_number": location.page_number,
            "line_start": None,
            "line_end": None,
            "sheet_name": None,
            "cell_reference": None,
        }
    if isinstance(location, LineRangeLocation):
        return {
            "page_number": None,
            "line_start": location.start_line,
            "line_end": location.end_line,
            "sheet_name": None,
            "cell_reference": None,
        }
    assert isinstance(location, CellRangeLocation)
    cell_reference = (
        location.start_cell
        if location.start_cell == location.end_cell
        else f"{location.start_cell}:{location.end_cell}"
    )
    return {
        "page_number": None,
        "line_start": None,
        "line_end": None,
        "sheet_name": location.sheet_name,
        "cell_reference": cell_reference,
    }
