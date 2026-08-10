"""Canonical raw-document preparation and immutable PostgreSQL persistence."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from html.parser import HTMLParser
from ipaddress import ip_address
from typing import Protocol
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobagent.core.exceptions import PermanentJobAgentError, TransientJobAgentError
from jobagent.crawlers.contracts import RawDocumentInput, SourceDefinition
from jobagent.crawlers.http import HttpCacheValidators
from jobagent.db.models import RawDocument

_UNRESERVED = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")
_PERCENT_ESCAPE = re.compile(r"%([0-9A-Fa-f]{2})")
_TRACKING_QUERY_KEYS = frozenset(
    {
        "fbclid",
        "gclid",
        "mc_cid",
        "mc_eid",
        "spm",
        "yclid",
    }
)
_IGNORED_HTML_ELEMENTS = frozenset({"noscript", "script", "style", "template"})


class RawDocumentWriteStatus(StrEnum):
    """Observable result of one idempotent raw-document write."""

    CREATED = "created"
    UNCHANGED = "unchanged"
    UPDATED = "updated"


@dataclass(frozen=True, slots=True)
class PreparedRawDocument:
    """Validated canonical input ready for immutable persistence."""

    canonical_url: str
    title: str
    raw_html: str | None
    raw_text: str | None
    published_at: datetime | None
    content_hash: str
    etag: str | None
    last_modified: str | None


@dataclass(frozen=True, slots=True)
class RawDocumentWriteResult:
    """Identity and version outcome returned by the persistence boundary."""

    document_id: int
    status: RawDocumentWriteStatus
    version: int
    canonical_url: str
    content_hash: str
    previous_document_id: int | None


class RawDocumentRepository(Protocol):
    """Persistence contract for canonical immutable source documents."""

    async def save(
        self,
        source: SourceDefinition,
        document: RawDocumentInput,
    ) -> RawDocumentWriteResult:
        """Create, reuse or version one raw document atomically."""
        ...

    async def get_validators(
        self,
        source: SourceDefinition,
        url: str,
    ) -> HttpCacheValidators | None:
        """Load conditional request validators for the current URL version."""
        ...


class SqlAlchemyRawDocumentRepository:
    """Persist immutable versions while exposing one current row per source URL."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def save(
        self,
        source: SourceDefinition,
        document: RawDocumentInput,
    ) -> RawDocumentWriteResult:
        prepared = prepare_raw_document(document, base_url=source.base_url)
        lock_key = _advisory_lock_key(source.id, prepared.canonical_url)

        try:
            async with self._session_factory() as session, session.begin():
                await session.execute(select(func.pg_advisory_xact_lock(lock_key)))
                current = await session.scalar(
                    select(RawDocument)
                    .where(
                        RawDocument.source_id == source.id,
                        RawDocument.canonical_url == prepared.canonical_url,
                        RawDocument.is_current.is_(True),
                    )
                    .with_for_update()
                )

                if current is not None and current.content_hash == prepared.content_hash:
                    _refresh_validators(current, prepared)
                    return _unchanged_result(current)

                version = 1 if current is None else current.version + 1
                previous_document_id = None if current is None else current.id
                if current is not None:
                    current.is_current = False

                persisted = RawDocument(
                    source_id=source.id,
                    canonical_url=prepared.canonical_url,
                    title=prepared.title,
                    raw_html=prepared.raw_html,
                    raw_text=prepared.raw_text,
                    published_at=prepared.published_at,
                    content_hash=prepared.content_hash,
                    etag=prepared.etag,
                    last_modified=prepared.last_modified,
                    version=version,
                    is_current=True,
                    supersedes_id=previous_document_id,
                )
                session.add(persisted)
                await session.flush()
                return RawDocumentWriteResult(
                    document_id=persisted.id,
                    status=(
                        RawDocumentWriteStatus.CREATED
                        if current is None
                        else RawDocumentWriteStatus.UPDATED
                    ),
                    version=version,
                    canonical_url=prepared.canonical_url,
                    content_hash=prepared.content_hash,
                    previous_document_id=previous_document_id,
                )
        except SQLAlchemyError as error:
            raise _database_error(error) from error

    async def get_validators(
        self,
        source: SourceDefinition,
        url: str,
    ) -> HttpCacheValidators | None:
        canonical_url = canonicalize_url(url, base_url=source.base_url)
        try:
            async with self._session_factory() as session:
                row = (
                    await session.execute(
                        select(RawDocument.etag, RawDocument.last_modified).where(
                            RawDocument.source_id == source.id,
                            RawDocument.canonical_url == canonical_url,
                            RawDocument.is_current.is_(True),
                        )
                    )
                ).one_or_none()
        except SQLAlchemyError as error:
            raise _database_error(error) from error
        if row is None:
            return None
        return HttpCacheValidators(etag=row.etag, last_modified=row.last_modified)


def canonicalize_url(url: str, *, base_url: str | None = None) -> str:
    """Resolve and canonicalize an HTTP(S) URL without dropping business parameters."""
    candidate = url.strip()
    if not candidate:
        raise _invalid_url("A raw document URL is required.")
    resolved = urljoin(base_url, candidate) if base_url is not None else candidate
    parsed = urlsplit(resolved)

    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise _invalid_url("Raw document URLs must use HTTP or HTTPS.")
    if parsed.username is not None or parsed.password is not None:
        raise _invalid_url("Raw document URLs must not contain credentials.")
    if parsed.hostname is None:
        raise _invalid_url("Raw document URLs must include a host.")

    try:
        port = parsed.port
    except ValueError as error:
        raise _invalid_url("Raw document URLs must include a valid port.") from error
    netloc = _canonical_netloc(parsed.hostname, port, scheme)
    path = _canonical_path(parsed.path)
    query_items = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not _is_tracking_query_key(key)
    ]
    query = urlencode(sorted(query_items))
    return urlunsplit((scheme, netloc, path, query, ""))


def normalize_document_content(*, raw_html: str | None, raw_text: str | None) -> str:
    """Return stable visible body text for semantic content fingerprints."""
    if raw_text is not None and raw_text.strip():
        candidate = raw_text
    elif raw_html is not None:
        parser = _VisibleTextParser()
        parser.feed(raw_html)
        parser.close()
        candidate = parser.visible_text
    else:
        candidate = ""

    normalized = " ".join(unicodedata.normalize("NFKC", candidate).split())
    if not normalized:
        raise PermanentJobAgentError(
            "A raw document must contain visible text for fingerprinting.",
            code="crawler.document_content_empty",
        )
    return normalized


def content_fingerprint(*, raw_html: str | None, raw_text: str | None) -> str:
    """Return a lowercase SHA-256 fingerprint of normalized visible content."""
    normalized = normalize_document_content(raw_html=raw_html, raw_text=raw_text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def prepare_raw_document(
    document: RawDocumentInput,
    *,
    base_url: str,
) -> PreparedRawDocument:
    """Canonicalize provenance and compute the stable content fingerprint."""
    return PreparedRawDocument(
        canonical_url=canonicalize_url(document.url, base_url=base_url),
        title=document.title,
        raw_html=document.raw_html,
        raw_text=document.raw_text,
        published_at=document.published_at,
        content_hash=content_fingerprint(
            raw_html=document.raw_html,
            raw_text=document.raw_text,
        ),
        etag=document.etag,
        last_modified=document.last_modified,
    )


def _canonical_netloc(hostname: str, port: int | None, scheme: str) -> str:
    host = hostname.rstrip(".")
    if not host:
        raise _invalid_url("Raw document URLs must include a valid host.")
    try:
        parsed_ip = ip_address(host)
    except ValueError:
        try:
            host = host.encode("idna").decode("ascii").lower()
        except UnicodeError as error:
            raise _invalid_url("Raw document URLs must include a valid host.") from error
    else:
        host = parsed_ip.compressed
        if parsed_ip.version == 6:
            host = f"[{host}]"

    default_port = 80 if scheme == "http" else 443
    return host if port is None or port == default_port else f"{host}:{port}"


def _canonical_path(path: str) -> str:
    normalized_escapes = _PERCENT_ESCAPE.sub(_normalize_escape, path)
    segments: list[str] = []
    for segment in normalized_escapes.split("/"):
        if segment in {"", "."}:
            continue
        if segment == "..":
            if segments:
                segments.pop()
            continue
        segments.append(segment)
    normalized = "/" + "/".join(segments)
    if path.endswith("/") and normalized != "/":
        normalized += "/"
    return normalized


def _normalize_escape(match: re.Match[str]) -> str:
    value = int(match.group(1), 16)
    character = chr(value)
    return character if character in _UNRESERVED else f"%{value:02X}"


def _is_tracking_query_key(key: str) -> bool:
    normalized = key.casefold()
    return normalized.startswith("utm_") or normalized in _TRACKING_QUERY_KEYS


def _advisory_lock_key(source_id: int, canonical_url: str) -> int:
    digest = hashlib.sha256(f"{source_id}\0{canonical_url}".encode()).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=True)


def _unchanged_result(current: RawDocument) -> RawDocumentWriteResult:
    return RawDocumentWriteResult(
        document_id=current.id,
        status=RawDocumentWriteStatus.UNCHANGED,
        version=current.version,
        canonical_url=current.canonical_url,
        content_hash=current.content_hash,
        previous_document_id=current.supersedes_id,
    )


def _refresh_validators(
    current: RawDocument,
    prepared: PreparedRawDocument,
) -> None:
    if prepared.etag is not None:
        current.etag = prepared.etag
    if prepared.last_modified is not None:
        current.last_modified = prepared.last_modified


def _database_error(error: SQLAlchemyError) -> TransientJobAgentError:
    return TransientJobAgentError(
        "Raw document persistence is temporarily unavailable.",
        code="database.raw_document_unavailable",
        details={"error_type": type(error).__name__},
    )


def _invalid_url(message: str) -> PermanentJobAgentError:
    return PermanentJobAgentError(message, code="crawler.document_url_invalid")


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._body_depth = 0
        self._ignored_depth = 0
        self._all_text: list[str] = []
        self._body_text: list[str] = []

    @property
    def visible_text(self) -> str:
        body = " ".join(self._body_text)
        return body if body.strip() else " ".join(self._all_text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = tag.casefold()
        if normalized in _IGNORED_HTML_ELEMENTS:
            self._ignored_depth += 1
        if normalized == "body":
            self._body_depth += 1

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.casefold()
        if normalized in _IGNORED_HTML_ELEMENTS and self._ignored_depth:
            self._ignored_depth -= 1
        if normalized == "body" and self._body_depth:
            self._body_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        self._all_text.append(data)
        if self._body_depth:
            self._body_text.append(data)
