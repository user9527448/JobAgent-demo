"""Stored-document reparsing with explicit versions and idempotent persistence."""

from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobagent.core.exceptions import PermanentJobAgentError, TransientJobAgentError
from jobagent.db.models import Attachment, RawDocument
from jobagent.extraction.merging import ExtractionMergeInput, ExtractionMerger, MergedExtraction
from jobagent.extraction.persistence import ExtractionWriteResult, SqlAlchemyExtractionRepository
from jobagent.extraction.rules import DeterministicFieldExtractor
from jobagent.parsers import (
    LineRangeLocation,
    ParseRequest,
    ParseResult,
    ParserRegistry,
    ParseSource,
    ParseSourceType,
    ParseStatus,
    TextBlock,
    TextBlockKind,
)

_EXTRACTION_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$")


class ReparsePipeline(Protocol):
    """Build one deterministic merged result from a stored document version."""

    async def build(self, document_id: int, extraction_version: str) -> MergedExtraction:
        """Return a merged result without persisting it."""


class ReparseOperations(Protocol):
    """Application boundary shared by the API and manual command."""

    async def reparse(self, document_id: int, extraction_version: str) -> ExtractionWriteResult:
        """Reparse and persist one specified immutable document."""


class ReparseService:
    """Coordinate deterministic reparsing and version-preserving persistence."""

    def __init__(
        self,
        pipeline: ReparsePipeline,
        repository: SqlAlchemyExtractionRepository,
    ) -> None:
        self._pipeline = pipeline
        self._repository = repository

    async def reparse(self, document_id: int, extraction_version: str) -> ExtractionWriteResult:
        if document_id <= 0:
            raise PermanentJobAgentError(
                "Document identifier must be positive.",
                code="reparse.document_id_invalid",
            )
        if _EXTRACTION_VERSION_PATTERN.fullmatch(extraction_version) is None:
            raise PermanentJobAgentError(
                "Extraction version must use 1-100 safe identifier characters.",
                code="reparse.extraction_version_invalid",
            )
        merged = await self._pipeline.build(document_id, extraction_version)
        if merged.document_id != document_id or merged.extraction_version != extraction_version:
            raise PermanentJobAgentError(
                "Reparse pipeline returned a result for another request.",
                code="reparse.pipeline_identity_mismatch",
            )
        return await self._repository.save(merged)


@dataclass(frozen=True, slots=True)
class _AttachmentSnapshot:
    id: int
    file_name: str
    mime_type: str | None
    sha256: str | None
    local_path: str | None
    size_bytes: int | None
    download_status: str


@dataclass(frozen=True, slots=True)
class _DocumentSnapshot:
    id: int
    canonical_url: str
    title: str
    raw_html: str | None
    raw_text: str | None
    attachments: tuple[_AttachmentSnapshot, ...]


class StoredDocumentReparsePipeline:
    """Rebuild deterministic parser/extraction output from persisted source bytes."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        attachment_storage_root: Path,
        parser_registry: ParserRegistry,
        extractor: DeterministicFieldExtractor,
        merger: ExtractionMerger | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._attachment_storage_root = attachment_storage_root.resolve()
        self._parser_registry = parser_registry
        self._extractor = extractor
        self._merger = merger or ExtractionMerger()

    async def build(self, document_id: int, extraction_version: str) -> MergedExtraction:
        snapshot = await self._load(document_id)
        extraction_results = []

        body_text = _document_text(snapshot)
        if body_text is not None:
            parsed_body = _document_parse_result(snapshot, body_text)
            extraction_results.append(
                self._extractor.extract(parsed_body, base_url=snapshot.canonical_url)
            )

        for attachment in snapshot.attachments:
            parsed_attachment = await asyncio.to_thread(self._parse_attachment, attachment)
            extraction_results.append(
                self._extractor.extract(parsed_attachment, base_url=snapshot.canonical_url)
            )

        if not extraction_results:
            raise PermanentJobAgentError(
                "Stored document has no reparsable body or attachments.",
                code="reparse.input_missing",
                details={"document_id": document_id},
            )
        return self._merger.merge(
            ExtractionMergeInput(
                document_id=document_id,
                extraction_version=extraction_version,
                deterministic_results=tuple(extraction_results),
            )
        )

    async def _load(self, document_id: int) -> _DocumentSnapshot:
        try:
            async with self._session_factory() as session:
                document = await session.get(RawDocument, document_id)
                if document is None:
                    raise PermanentJobAgentError(
                        "The requested raw document does not exist.",
                        code="reparse.document_not_found",
                        details={"document_id": document_id},
                    )
                attachments = tuple(
                    await session.scalars(
                        select(Attachment)
                        .where(Attachment.document_id == document_id)
                        .order_by(Attachment.id)
                    )
                )
                return _DocumentSnapshot(
                    id=document.id,
                    canonical_url=document.canonical_url,
                    title=document.title,
                    raw_html=document.raw_html,
                    raw_text=document.raw_text,
                    attachments=tuple(
                        _AttachmentSnapshot(
                            id=item.id,
                            file_name=item.file_name,
                            mime_type=item.mime_type,
                            sha256=item.sha256,
                            local_path=item.local_path,
                            size_bytes=item.size_bytes,
                            download_status=item.download_status,
                        )
                        for item in attachments
                    ),
                )
        except SQLAlchemyError as error:
            raise TransientJobAgentError(
                "Stored reparse input is temporarily unavailable.",
                code="database.reparse_input_unavailable",
                details={"error_type": type(error).__name__},
            ) from error

    def _parse_attachment(self, attachment: _AttachmentSnapshot) -> ParseResult:
        if (
            attachment.download_status != "stored"
            or attachment.mime_type is None
            or attachment.sha256 is None
            or attachment.local_path is None
            or attachment.size_bytes is None
        ):
            raise PermanentJobAgentError(
                "A referenced attachment is not stored and cannot be reparsed safely.",
                code="reparse.attachment_not_stored",
                details={"attachment_id": attachment.id},
            )
        object_path = (self._attachment_storage_root / attachment.local_path).resolve()
        if not object_path.is_relative_to(self._attachment_storage_root):
            raise PermanentJobAgentError(
                "Attachment storage path escapes the configured root.",
                code="reparse.attachment_path_invalid",
                details={"attachment_id": attachment.id},
            )
        try:
            content = object_path.read_bytes()
        except OSError as error:
            raise TransientJobAgentError(
                "Stored attachment bytes are temporarily unavailable.",
                code="reparse.attachment_storage_unavailable",
                details={"attachment_id": attachment.id, "error_type": type(error).__name__},
            ) from error
        if (
            len(content) != attachment.size_bytes
            or hashlib.sha256(content).hexdigest() != attachment.sha256
        ):
            raise PermanentJobAgentError(
                "Stored attachment failed its persisted integrity checks.",
                code="reparse.attachment_integrity_invalid",
                details={"attachment_id": attachment.id},
            )
        source = ParseSource(
            source_type=ParseSourceType.ATTACHMENT,
            source_id=attachment.id,
            source_name=attachment.file_name,
            media_type=attachment.mime_type,
        )
        result = self._parser_registry.parse(ParseRequest(source=source, content=content))
        if result.status is not ParseStatus.PARSED:
            raise PermanentJobAgentError(
                "Stored attachment did not produce a parsed intermediate result.",
                code="reparse.attachment_parse_incomplete",
                details={
                    "attachment_id": attachment.id,
                    "parse_status": result.status.value,
                    "issue_codes": [item.code.value for item in result.issues],
                },
            )
        return result


def _document_text(snapshot: _DocumentSnapshot) -> str | None:
    if snapshot.raw_text is not None and snapshot.raw_text.strip():
        return snapshot.raw_text.strip()
    if snapshot.raw_html is None or not snapshot.raw_html.strip():
        return None
    text = BeautifulSoup(snapshot.raw_html, "html.parser").get_text("\n", strip=True)
    return text or None


def _document_parse_result(snapshot: _DocumentSnapshot, text: str) -> ParseResult:
    source = ParseSource(
        source_type=ParseSourceType.DOCUMENT,
        source_id=snapshot.id,
        source_name=f"document-{snapshot.id}.txt",
        media_type="text/plain",
    )
    line_count = max(1, len(text.splitlines()))
    location = LineRangeLocation(source=source, start_line=1, end_line=line_count)
    return ParseResult(
        source=source,
        status=ParseStatus.PARSED,
        parser_name="raw-document-text-v1",
        blocks=(
            TextBlock(
                kind=TextBlockKind.OTHER,
                text=text,
                location=location,
            ),
        ),
    )
