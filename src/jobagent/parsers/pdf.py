"""Page-level PDF text parsing and deterministic low-text detection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import pymupdf

from jobagent.core.exceptions import JsonValue
from jobagent.parsers.contracts import (
    PageLocation,
    ParseErrorCode,
    ParseIssue,
    ParseRequest,
    ParseResult,
    ParseStatus,
    TextBlock,
    TextBlockKind,
)

PDF_MEDIA_TYPE: Final = "application/pdf"
PDF_PARSER_NAME: Final = "pdf_text"
_PDF_METADATA_KEYS: Final = (
    "format",
    "title",
    "author",
    "subject",
    "keywords",
    "creator",
    "producer",
    "creationDate",
    "modDate",
)


@dataclass(frozen=True, slots=True)
class PdfTextPolicy:
    """Deterministic threshold for flagging a PDF as requiring OCR review."""

    min_average_characters_per_page: int = 40

    def __post_init__(self) -> None:
        if self.min_average_characters_per_page <= 0:
            raise ValueError("PDF text threshold must be positive.")


class PdfTextParser:
    """Extract normalized page text with traceable one-based page locations."""

    def __init__(self, policy: PdfTextPolicy | None = None) -> None:
        self._policy = policy or PdfTextPolicy()

    @property
    def name(self) -> str:
        """Return the stable parser implementation name."""
        return PDF_PARSER_NAME

    @property
    def supported_media_types(self) -> tuple[str, ...]:
        """Return the only media type accepted by this parser."""
        return (PDF_MEDIA_TYPE,)

    def parse(self, request: ParseRequest) -> ParseResult:
        """Extract text or return a safe encrypted/corrupt/OCR-required result."""
        if request.source.media_type != PDF_MEDIA_TYPE:
            return _failed_result(
                request,
                code=ParseErrorCode.INVALID_INPUT,
                message="The PDF parser only accepts the application/pdf media type.",
            )
        try:
            document = pymupdf.open(  # type: ignore[no-untyped-call]
                stream=request.content,
                filetype="pdf",
            )
        except (pymupdf.EmptyFileError, pymupdf.FileDataError, ValueError):
            return _failed_result(
                request,
                code=ParseErrorCode.CORRUPT_DOCUMENT,
                message="The PDF is empty, corrupt, or not a valid PDF document.",
            )

        with document:
            if document.needs_pass or document.is_encrypted:
                return _failed_result(
                    request,
                    code=ParseErrorCode.ENCRYPTED_DOCUMENT,
                    message="The PDF is encrypted and cannot be parsed without a password.",
                )
            if document.page_count <= 0:
                return _failed_result(
                    request,
                    code=ParseErrorCode.CORRUPT_DOCUMENT,
                    message="The PDF contains no pages.",
                )

            try:
                blocks, page_stats, total_characters = _extract_page_blocks(document, request)
                document_metadata = _document_metadata(document)
            except (pymupdf.FileDataError, RuntimeError, ValueError):
                return _failed_result(
                    request,
                    code=ParseErrorCode.CORRUPT_DOCUMENT,
                    message="The PDF page tree or page content is corrupt.",
                )

            average_characters = total_characters / document.page_count
            pages_json: list[JsonValue] = list(page_stats)
            metadata: dict[str, JsonValue] = {
                "page_count": document.page_count,
                "text_characters": total_characters,
                "average_text_characters_per_page": average_characters,
                "pages": pages_json,
                "document_metadata": document_metadata,
            }
            if average_characters < self._policy.min_average_characters_per_page:
                return ParseResult(
                    source=request.source,
                    status=ParseStatus.OCR_REQUIRED,
                    parser_name=self.name,
                    blocks=blocks,
                    issues=(
                        ParseIssue(
                            code=ParseErrorCode.OCR_REQUIRED,
                            message=(
                                "The PDF text density is below the supported threshold; "
                                "manual or OCR handling is required."
                            ),
                            details={
                                "average_text_characters_per_page": average_characters,
                                "minimum_text_characters_per_page": (
                                    self._policy.min_average_characters_per_page
                                ),
                                "page_count": document.page_count,
                            },
                        ),
                    ),
                    metadata=metadata,
                )

            return ParseResult(
                source=request.source,
                status=ParseStatus.PARSED,
                parser_name=self.name,
                blocks=blocks,
                metadata=metadata,
            )


def _extract_page_blocks(
    document: pymupdf.Document,
    request: ParseRequest,
) -> tuple[tuple[TextBlock, ...], list[dict[str, JsonValue]], int]:
    blocks: list[TextBlock] = []
    page_stats: list[dict[str, JsonValue]] = []
    total_characters = 0
    for page_index in range(document.page_count):
        page_number = page_index + 1
        page = document.load_page(page_index)  # type: ignore[no-untyped-call]
        text = _normalize_page_text(page.get_text("text", sort=True))
        character_count = _text_character_count(text)
        total_characters += character_count
        page_stats.append(
            {
                "page_number": page_number,
                "text_characters": character_count,
            }
        )
        if text:
            blocks.append(
                TextBlock(
                    kind=TextBlockKind.PARAGRAPH,
                    text=text,
                    location=PageLocation(
                        source=request.source,
                        page_number=page_number,
                    ),
                )
            )
    return (tuple(blocks), page_stats, total_characters)


def _normalize_page_text(value: str) -> str:
    return "\n".join(
        normalized for line in value.splitlines() if (normalized := " ".join(line.split()))
    )


def _text_character_count(value: str) -> int:
    return sum(not character.isspace() for character in value)


def _document_metadata(document: pymupdf.Document) -> dict[str, JsonValue]:
    raw_metadata = document.metadata or {}
    return {
        key: value.strip()
        for key in _PDF_METADATA_KEYS
        if isinstance((value := raw_metadata.get(key)), str) and value.strip()
    }


def _failed_result(
    request: ParseRequest,
    *,
    code: ParseErrorCode,
    message: str,
) -> ParseResult:
    return ParseResult(
        source=request.source,
        status=ParseStatus.FAILED,
        parser_name=PDF_PARSER_NAME,
        issues=(ParseIssue(code=code, message=message),),
    )
