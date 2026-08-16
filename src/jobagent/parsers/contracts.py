"""Typed parser inputs and traceable intermediate document structures."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol, TypeAlias

from jobagent.core.exceptions import JsonValue

_MEDIA_TYPE_PATTERN = re.compile(r"^[^\s/]+/[^\s/]+$")
_CELL_REFERENCE_PATTERN = re.compile(r"^([A-Z]+)([1-9][0-9]*)$")


class ParseSourceType(StrEnum):
    """Persisted source entity that supplied parser input."""

    DOCUMENT = "document"
    ATTACHMENT = "attachment"


class ParseStatus(StrEnum):
    """Statuses shared with the attachment parsing state machine."""

    PENDING = "pending"
    PARSED = "parsed"
    OCR_REQUIRED = "ocr_required"
    UNSUPPORTED = "unsupported"
    FAILED = "failed"


class ParseErrorCode(StrEnum):
    """Stable parser error codes suitable for persistence and diagnostics."""

    UNSUPPORTED_MEDIA_TYPE = "parser.unsupported_media_type"
    INVALID_INPUT = "parser.invalid_input"
    INVALID_OUTPUT = "parser.invalid_output"
    CORRUPT_DOCUMENT = "parser.corrupt_document"
    ENCRYPTED_DOCUMENT = "parser.encrypted_document"
    OCR_REQUIRED = "parser.ocr_required"
    HEADER_NOT_RECOGNIZED = "parser.header_not_recognized"
    PARSER_FAILED = "parser.failed"


class TextBlockKind(StrEnum):
    """Portable text semantics emitted by format-specific parsers."""

    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST_ITEM = "list_item"
    OTHER = "other"


def normalize_media_type(value: str) -> str:
    """Return a canonical lower-case media type without optional parameters."""
    normalized = value.partition(";")[0].strip().lower()
    if _MEDIA_TYPE_PATTERN.fullmatch(normalized) is None:
        raise ValueError("Media type must use the 'type/subtype' form.")
    return normalized


@dataclass(frozen=True, slots=True)
class ParseSource:
    """Immutable identity and media metadata for one parser input."""

    source_type: ParseSourceType
    source_id: int
    source_name: str
    media_type: str

    def __post_init__(self) -> None:
        if self.source_id <= 0:
            raise ValueError("Parser source ID must be positive.")
        normalized_name = self.source_name.strip()
        if not normalized_name:
            raise ValueError("Parser source name cannot be empty.")
        object.__setattr__(self, "source_name", normalized_name)
        object.__setattr__(self, "media_type", normalize_media_type(self.media_type))


@dataclass(frozen=True, slots=True)
class ParseRequest:
    """Validated in-memory content presented to one format-specific parser."""

    source: ParseSource
    content: bytes

    def __post_init__(self) -> None:
        if not self.content:
            raise ValueError("Parser input content cannot be empty.")


@dataclass(frozen=True, slots=True)
class PageLocation:
    """A one-based page within a source file."""

    source: ParseSource
    page_number: int

    def __post_init__(self) -> None:
        if self.page_number <= 0:
            raise ValueError("Page number must be positive and one-based.")


@dataclass(frozen=True, slots=True)
class LineRangeLocation:
    """An inclusive one-based line range within a source file or raw document."""

    source: ParseSource
    start_line: int
    end_line: int

    def __post_init__(self) -> None:
        if self.start_line <= 0:
            raise ValueError("Start line must be positive and one-based.")
        if self.end_line < self.start_line:
            raise ValueError("End line cannot precede start line.")


@dataclass(frozen=True, slots=True)
class CellRangeLocation:
    """An inclusive cell range within one worksheet of a source file."""

    source: ParseSource
    sheet_name: str
    start_cell: str
    end_cell: str

    def __post_init__(self) -> None:
        sheet_name = self.sheet_name.strip()
        start_cell = self.start_cell.strip().upper()
        end_cell = self.end_cell.strip().upper()
        if not sheet_name:
            raise ValueError("Worksheet name cannot be empty.")
        start_match = _CELL_REFERENCE_PATTERN.fullmatch(start_cell)
        end_match = _CELL_REFERENCE_PATTERN.fullmatch(end_cell)
        if start_match is None or end_match is None:
            raise ValueError("Cell range endpoints must use one-based A1 notation.")
        start_row, start_column = _cell_coordinates(start_match.group(1), start_match.group(2))
        end_row, end_column = _cell_coordinates(end_match.group(1), end_match.group(2))
        if end_row < start_row or end_column < start_column:
            raise ValueError("End cell cannot precede start cell.")
        object.__setattr__(self, "sheet_name", sheet_name)
        object.__setattr__(self, "start_cell", start_cell)
        object.__setattr__(self, "end_cell", end_cell)


EvidenceLocation: TypeAlias = PageLocation | LineRangeLocation | CellRangeLocation


@dataclass(frozen=True, slots=True)
class TextBlock:
    """One textual intermediate block with an exact source locator."""

    kind: TextBlockKind
    text: str
    location: EvidenceLocation
    metadata: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("Text block content cannot be empty.")


@dataclass(frozen=True, slots=True)
class TableCell:
    """One table cell with its own source locator."""

    value: str
    location: EvidenceLocation


@dataclass(frozen=True, slots=True)
class TableBlock:
    """A rectangular or ragged table whose cells retain evidence locations."""

    rows: tuple[tuple[TableCell, ...], ...]
    location: EvidenceLocation
    metadata: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.rows or any(not row for row in self.rows):
            raise ValueError("Table blocks must contain at least one non-empty row.")
        for cell in _table_cells(self.rows):
            if cell.location.source != self.location.source:
                raise ValueError("Every table cell must reference the table block source.")


ParsedBlock: TypeAlias = TextBlock | TableBlock


@dataclass(frozen=True, slots=True)
class ParseIssue:
    """A safe, machine-readable parser failure or manual-review reason."""

    code: ParseErrorCode
    message: str
    retryable: bool = False
    details: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError("Parse issue message cannot be empty.")


@dataclass(frozen=True, slots=True)
class ParseResult:
    """One completed parser outcome in the standard intermediate format."""

    source: ParseSource
    status: ParseStatus
    parser_name: str | None = None
    blocks: tuple[ParsedBlock, ...] = ()
    issues: tuple[ParseIssue, ...] = ()
    metadata: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        parser_name = self.parser_name.strip() if self.parser_name is not None else None
        if parser_name == "":
            raise ValueError("Parser name cannot be empty.")
        object.__setattr__(self, "parser_name", parser_name)

        if self.status is ParseStatus.PENDING:
            raise ValueError("A completed parse result cannot remain pending.")
        if self.status is ParseStatus.PARSED and (parser_name is None or not self.blocks):
            raise ValueError("A parsed result requires a parser name and at least one block.")
        if self.status is not ParseStatus.PARSED and not self.issues:
            raise ValueError("A non-parsed result requires at least one diagnostic issue.")
        for block in self.blocks:
            if block.location.source != self.source:
                raise ValueError("Every parsed block must reference the result source.")

    @classmethod
    def unsupported(cls, source: ParseSource) -> ParseResult:
        """Build an explicit unsupported result instead of silently skipping input."""
        return cls(
            source=source,
            status=ParseStatus.UNSUPPORTED,
            issues=(
                ParseIssue(
                    code=ParseErrorCode.UNSUPPORTED_MEDIA_TYPE,
                    message=f"No parser is registered for media type '{source.media_type}'.",
                    details={"media_type": source.media_type},
                ),
            ),
        )


class DocumentParser(Protocol):
    """Format-specific parser contract used by the common registry."""

    @property
    def name(self) -> str:
        """Return a stable parser implementation name."""
        ...

    @property
    def supported_media_types(self) -> Iterable[str]:
        """Return every media type handled by this parser."""
        ...

    def parse(self, request: ParseRequest) -> ParseResult:
        """Parse content without discarding its persisted source identity."""
        ...


def _table_cells(rows: tuple[tuple[TableCell, ...], ...]) -> Iterable[TableCell]:
    for row in rows:
        yield from row


def _cell_coordinates(column_name: str, row_text: str) -> tuple[int, int]:
    column_number = 0
    for character in column_name:
        column_number = (column_number * 26) + ord(character) - ord("A") + 1
    return (int(row_text), column_number)
