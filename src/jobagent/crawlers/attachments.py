"""Attachment discovery, validation, atomic file storage, and persistence."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from html.parser import HTMLParser
from pathlib import Path
from typing import Protocol
from urllib.parse import unquote, urlsplit

import httpx
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobagent.core.exceptions import (
    ConfigurationError,
    JobAgentError,
    JsonValue,
    PermanentJobAgentError,
    TransientJobAgentError,
)
from jobagent.crawlers.documents import canonicalize_url
from jobagent.crawlers.http import SourceHttpClient
from jobagent.db.models import Attachment

_SUPPORTED_EXTENSIONS = frozenset({".pdf", ".xls", ".xlsx"})
_GENERIC_MIME_TYPES = frozenset({"", "application/octet-stream", "binary/octet-stream"})
_ALLOWED_MIME_TYPES = {
    ".pdf": frozenset({"application/pdf"}),
    ".xls": frozenset({"application/vnd.ms-excel"}),
    ".xlsx": frozenset(
        {
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/zip",
        }
    ),
}
_CANONICAL_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
_OLE_SIGNATURE = bytes.fromhex("D0CF11E0A1B11AE1")
_INVALID_FILENAME = re.compile(r"[\x00-\x1f<>:\"/\\|?*]+")


class AttachmentStoreStatus(StrEnum):
    """Observable file-storage result for one attachment URL."""

    STORED = "stored"
    REUSED = "reused"


@dataclass(frozen=True, slots=True)
class AttachmentStoragePolicy:
    """Local object-store limits and write granularity."""

    root: Path
    max_bytes: int = 25 * 1024 * 1024
    chunk_bytes: int = 64 * 1024

    def __post_init__(self) -> None:
        invalid: dict[str, JsonValue] = {}
        if not str(self.root):
            invalid["root"] = str(self.root)
        if self.max_bytes <= 0:
            invalid["max_bytes"] = self.max_bytes
        if self.chunk_bytes <= 0:
            invalid["chunk_bytes"] = self.chunk_bytes
        if invalid:
            raise ConfigurationError(
                "Attachment storage policy is invalid.",
                code="crawler.attachment_policy_invalid",
                details={"fields": invalid},
            )


@dataclass(frozen=True, slots=True)
class AttachmentCandidate:
    """One supported link discovered in announcement HTML."""

    url: str
    file_name: str
    extension: str


@dataclass(frozen=True, slots=True)
class AttachmentRecord:
    """Database state needed by the file-storage service."""

    id: int
    document_id: int
    url: str
    file_name: str
    download_status: str
    mime_type: str | None
    sha256: str | None
    local_path: str | None
    size_bytes: int | None
    error_message: str | None


@dataclass(frozen=True, slots=True)
class AttachmentStoreResult:
    """Stored attachment identity and content-addressed object metadata."""

    attachment_id: int
    status: AttachmentStoreStatus
    url: str
    file_name: str
    mime_type: str
    sha256: str
    local_path: str
    size_bytes: int


class AttachmentRepository(Protocol):
    """Database operations required by attachment file storage."""

    async def get_or_create(
        self,
        document_id: int,
        candidate: AttachmentCandidate,
    ) -> AttachmentRecord:
        """Return the unique database record for a document URL."""
        ...

    async def mark_stored(
        self,
        attachment_id: int,
        *,
        mime_type: str,
        sha256: str,
        local_path: str,
        size_bytes: int,
    ) -> AttachmentRecord:
        """Persist a complete validated object as stored."""
        ...

    async def mark_failed(self, attachment_id: int, *, error_message: str) -> None:
        """Record a safe terminal download failure."""
        ...


class SqlAlchemyAttachmentRepository:
    """Persist idempotent attachment metadata through short transactions."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_or_create(
        self,
        document_id: int,
        candidate: AttachmentCandidate,
    ) -> AttachmentRecord:
        lock_key = _attachment_lock_key(document_id, candidate.url)
        try:
            async with self._session_factory() as session, session.begin():
                await session.execute(select(func.pg_advisory_xact_lock(lock_key)))
                attachment = await session.scalar(
                    select(Attachment).where(
                        Attachment.document_id == document_id,
                        Attachment.url == candidate.url,
                    )
                )
                if attachment is None:
                    attachment = Attachment(
                        document_id=document_id,
                        url=candidate.url,
                        file_name=candidate.file_name,
                        download_status="pending",
                        parse_status="pending",
                    )
                    session.add(attachment)
                    await session.flush()
                return _attachment_record(attachment)
        except SQLAlchemyError as error:
            raise _database_error("load or create attachment", error) from error

    async def mark_stored(
        self,
        attachment_id: int,
        *,
        mime_type: str,
        sha256: str,
        local_path: str,
        size_bytes: int,
    ) -> AttachmentRecord:
        try:
            async with self._session_factory() as session, session.begin():
                attachment = await _require_attachment(session, attachment_id)
                attachment.mime_type = mime_type
                attachment.sha256 = sha256
                attachment.local_path = local_path
                attachment.size_bytes = size_bytes
                attachment.download_status = "stored"
                attachment.error_message = None
                attachment.downloaded_at = datetime.now(UTC)
                await session.flush()
                return _attachment_record(attachment)
        except SQLAlchemyError as error:
            raise _database_error("mark attachment stored", error) from error

    async def mark_failed(self, attachment_id: int, *, error_message: str) -> None:
        try:
            async with self._session_factory() as session, session.begin():
                attachment = await _require_attachment(session, attachment_id)
                attachment.mime_type = None
                attachment.sha256 = None
                attachment.local_path = None
                attachment.size_bytes = None
                attachment.download_status = "failed"
                attachment.error_message = error_message
                attachment.downloaded_at = None
        except SQLAlchemyError as error:
            raise _database_error("mark attachment failed", error) from error


class AttachmentStorageService:
    """Download supported attachments into an atomic content-addressed store."""

    def __init__(
        self,
        policy: AttachmentStoragePolicy,
        repository: AttachmentRepository,
    ) -> None:
        self.policy = policy
        self._repository = repository
        self._root = policy.root.resolve()

    async def store(
        self,
        document_id: int,
        candidate: AttachmentCandidate,
        client: SourceHttpClient,
    ) -> AttachmentStoreResult:
        """Reuse or atomically download one attachment and record its outcome."""
        record = await self._repository.get_or_create(document_id, candidate)
        try:
            reused = self._reused_result(record)
            if reused is not None:
                return reused
            downloaded = await self._download(candidate, client)
            stored = await self._repository.mark_stored(
                record.id,
                mime_type=downloaded.mime_type,
                sha256=downloaded.sha256,
                local_path=downloaded.local_path,
                size_bytes=downloaded.size_bytes,
            )
        except JobAgentError as error:
            await self._repository.mark_failed(
                record.id,
                error_message=f"{error.code}: {error.message}",
            )
            raise
        except httpx.TransportError as error:
            failure = TransientJobAgentError(
                "Attachment download was interrupted.",
                code="crawler.attachment_download_interrupted",
                details={"error_type": type(error).__name__},
            )
            await self._repository.mark_failed(
                record.id,
                error_message=f"{failure.code}: {failure.message}",
            )
            raise failure from error
        except OSError as error:
            failure = TransientJobAgentError(
                "Attachment storage is temporarily unavailable.",
                code="crawler.attachment_storage_unavailable",
                details={"error_type": type(error).__name__},
            )
            await self._repository.mark_failed(
                record.id,
                error_message=f"{failure.code}: {failure.message}",
            )
            raise failure from error

        return AttachmentStoreResult(
            attachment_id=stored.id,
            status=AttachmentStoreStatus.STORED,
            url=stored.url,
            file_name=stored.file_name,
            mime_type=downloaded.mime_type,
            sha256=downloaded.sha256,
            local_path=downloaded.local_path,
            size_bytes=downloaded.size_bytes,
        )

    async def _download(
        self,
        candidate: AttachmentCandidate,
        client: SourceHttpClient,
    ) -> _DownloadedObject:
        temp_directory = self._root / ".tmp"
        temp_directory.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None

        try:
            async with client.stream(candidate.url) as fetched:
                if fetched.not_modified:
                    raise TransientJobAgentError(
                        "Attachment returned not-modified without a stored local object.",
                        code="crawler.attachment_not_modified_without_file",
                    )
                response = fetched.response
                reported_mime = _response_mime_type(response.headers.get("content-type"))
                _validate_reported_size(response.headers.get("content-length"), self.policy)

                file_descriptor, temp_name = tempfile.mkstemp(
                    prefix="attachment-",
                    suffix=".part",
                    dir=temp_directory,
                )
                temp_path = Path(temp_name)
                digest = hashlib.sha256()
                size_bytes = 0
                with os.fdopen(file_descriptor, "wb") as temporary_file:
                    async for chunk in response.aiter_bytes(self.policy.chunk_bytes):
                        size_bytes += len(chunk)
                        if size_bytes > self.policy.max_bytes:
                            raise _attachment_too_large(self.policy.max_bytes)
                        digest.update(chunk)
                        temporary_file.write(chunk)
                    temporary_file.flush()
                    os.fsync(temporary_file.fileno())

            if size_bytes == 0:
                raise PermanentJobAgentError(
                    "Attachment response was empty.",
                    code="crawler.attachment_content_invalid",
                )
            mime_type = _validate_file(temp_path, candidate.extension, reported_mime)
            sha256 = digest.hexdigest()
            relative_path = Path("objects") / sha256[:2] / f"{sha256}{candidate.extension}"
            final_path = self._root / relative_path
            final_path.parent.mkdir(parents=True, exist_ok=True)

            if final_path.exists():
                if _file_sha256(final_path) != sha256:
                    raise TransientJobAgentError(
                        "Attachment object path contains unexpected content.",
                        code="crawler.attachment_storage_collision",
                    )
                temp_path.unlink()
            else:
                temp_path.replace(final_path)
            temp_path = None
            return _DownloadedObject(
                mime_type=mime_type,
                sha256=sha256,
                local_path=relative_path.as_posix(),
                size_bytes=size_bytes,
            )
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    def _reused_result(self, record: AttachmentRecord) -> AttachmentStoreResult | None:
        if (
            record.download_status != "stored"
            or record.mime_type is None
            or record.sha256 is None
            or record.local_path is None
            or record.size_bytes is None
        ):
            return None
        object_path = (self._root / record.local_path).resolve()
        if not object_path.is_relative_to(self._root) or not object_path.is_file():
            return None
        if _file_sha256(object_path) != record.sha256:
            return None
        return AttachmentStoreResult(
            attachment_id=record.id,
            status=AttachmentStoreStatus.REUSED,
            url=record.url,
            file_name=record.file_name,
            mime_type=record.mime_type,
            sha256=record.sha256,
            local_path=record.local_path,
            size_bytes=record.size_bytes,
        )


def discover_attachment_links(raw_html: str, *, base_url: str) -> tuple[AttachmentCandidate, ...]:
    """Discover unique PDF/XLS/XLSX anchors from announcement HTML."""
    parser = _AnchorParser()
    parser.feed(raw_html)
    parser.close()
    candidates: list[AttachmentCandidate] = []
    seen_urls: set[str] = set()

    for href, display_text in parser.links:
        extension = _supported_extension(href) or _supported_extension(display_text)
        if extension is None:
            continue
        try:
            url = canonicalize_url(href, base_url=base_url)
        except PermanentJobAgentError:
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)
        candidates.append(
            AttachmentCandidate(
                url=url,
                file_name=_attachment_file_name(display_text, url, extension),
                extension=extension,
            )
        )
    return tuple(candidates)


@dataclass(frozen=True, slots=True)
class _DownloadedObject:
    mime_type: str
    sha256: str
    local_path: str
    size_bytes: int


async def _require_attachment(session: AsyncSession, attachment_id: int) -> Attachment:
    attachment = await session.get(Attachment, attachment_id)
    if attachment is None:
        raise PermanentJobAgentError(
            f"Attachment {attachment_id} does not exist.",
            code="crawler.attachment_not_found",
            details={"attachment_id": attachment_id},
        )
    return attachment


def _attachment_record(attachment: Attachment) -> AttachmentRecord:
    return AttachmentRecord(
        id=attachment.id,
        document_id=attachment.document_id,
        url=attachment.url,
        file_name=attachment.file_name,
        download_status=attachment.download_status,
        mime_type=attachment.mime_type,
        sha256=attachment.sha256,
        local_path=attachment.local_path,
        size_bytes=attachment.size_bytes,
        error_message=attachment.error_message,
    )


def _attachment_lock_key(document_id: int, url: str) -> int:
    digest = hashlib.sha256(f"{document_id}\0{url}".encode()).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=True)


def _database_error(operation: str, error: SQLAlchemyError) -> TransientJobAgentError:
    return TransientJobAgentError(
        f"Database could not {operation}.",
        code="database.attachment_unavailable",
        details={"error_type": type(error).__name__},
    )


def _response_mime_type(header: str | None) -> str:
    if header is None:
        return ""
    return header.split(";", 1)[0].strip().lower()


def _validate_reported_size(header: str | None, policy: AttachmentStoragePolicy) -> None:
    if header is None:
        return
    try:
        reported = int(header)
    except ValueError:
        return
    if reported > policy.max_bytes:
        raise _attachment_too_large(policy.max_bytes)


def _attachment_too_large(max_bytes: int) -> PermanentJobAgentError:
    return PermanentJobAgentError(
        "Attachment exceeds the configured size limit.",
        code="crawler.attachment_too_large",
        details={"max_bytes": max_bytes},
    )


def _validate_file(path: Path, extension: str, reported_mime: str) -> str:
    detected_extension = _detect_file_extension(path)
    if detected_extension != extension:
        raise PermanentJobAgentError(
            "Attachment content does not match its declared file type.",
            code="crawler.attachment_content_invalid",
            details={"declared_extension": extension},
        )
    if (
        reported_mime not in _GENERIC_MIME_TYPES
        and reported_mime not in _ALLOWED_MIME_TYPES[extension]
    ):
        raise PermanentJobAgentError(
            "Attachment response MIME type does not match its file type.",
            code="crawler.attachment_mime_invalid",
            details={"mime_type": reported_mime, "declared_extension": extension},
        )
    return _CANONICAL_MIME_TYPES[extension]


def _detect_file_extension(path: Path) -> str | None:
    with path.open("rb") as source_file:
        prefix = source_file.read(4096)
    if b"%PDF-" in prefix[:1024]:
        return ".pdf"
    if prefix.startswith(_OLE_SIGNATURE):
        return ".xls"
    if prefix.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(path) as workbook:
                names = set(workbook.namelist())
        except zipfile.BadZipFile:
            return None
        if "[Content_Types].xml" in names and "xl/workbook.xml" in names:
            return ".xlsx"
    return None


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _supported_extension(value: str) -> str | None:
    path = unquote(urlsplit(value.strip()).path)
    extension = Path(path).suffix.lower()
    return extension if extension in _SUPPORTED_EXTENSIONS else None


def _attachment_file_name(display_text: str, url: str, extension: str) -> str:
    display_name = " ".join(display_text.split())
    url_name = Path(unquote(urlsplit(url).path)).name
    preferred = display_name if _supported_extension(display_name) else url_name
    sanitized = _INVALID_FILENAME.sub("_", preferred).strip(" .")
    if not sanitized:
        sanitized = f"attachment{extension}"
    if not sanitized.lower().endswith(extension):
        sanitized += extension
    maximum_stem_length = 240 - len(extension)
    stem = sanitized[: -len(extension)]
    return f"{stem[:maximum_stem_length]}{extension}"


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "a" or self._href is not None:
            return
        attributes = {name.casefold(): value for name, value in attrs}
        href = attributes.get("href")
        if href:
            self._href = href
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() != "a" or self._href is None:
            return
        self.links.append((self._href, "".join(self._text)))
        self._href = None
        self._text = []
