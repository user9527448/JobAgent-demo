from __future__ import annotations

from pathlib import Path
from typing import cast

import pymupdf
import pytest

from jobagent.parsers import (
    PDF_MEDIA_TYPE,
    PDF_PARSER_NAME,
    PageLocation,
    ParseErrorCode,
    ParseRequest,
    ParseSource,
    ParseSourceType,
    ParseStatus,
    PdfTextParser,
    PdfTextPolicy,
    TextBlock,
    build_parser_registry,
)

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "jining"


def _source(source_id: int = 14, media_type: str = PDF_MEDIA_TYPE) -> ParseSource:
    return ParseSource(
        source_type=ParseSourceType.ATTACHMENT,
        source_id=source_id,
        source_name="objects/pdf/positions.pdf",
        media_type=media_type,
    )


def _request(content: bytes, source_id: int = 14) -> ParseRequest:
    return ParseRequest(source=_source(source_id), content=content)


def _text_pdf(*pages: str, title: str = "Fixture PDF", encrypted: bool = False) -> bytes:
    with pymupdf.open() as document:  # type: ignore[no-untyped-call]
        document.set_metadata({"title": title, "author": "JOBAGENT fixture"})
        for text in pages:
            page = document.new_page()
            text_rect = (
                page.rect.x0 + 36,
                page.rect.y0 + 36,
                page.rect.x1 - 36,
                page.rect.y1 - 36,
            )
            page.insert_textbox(text_rect, text, fontsize=10)
        if encrypted:
            return cast(
                bytes,
                document.tobytes(
                    encryption=pymupdf.PDF_ENCRYPT_AES_256,  # type: ignore[attr-defined]
                    owner_pw="fixture-owner",
                    user_pw="fixture-user",
                    permissions=0,
                ),
            )
        return cast(bytes, document.tobytes())


def _image_only_pdf() -> bytes:
    with pymupdf.open() as document:  # type: ignore[no-untyped-call]
        page = document.new_page()
        pixmap = pymupdf.Pixmap(  # type: ignore[no-untyped-call]
            pymupdf.csGRAY,
            pymupdf.IRect(0, 0, 20, 20),  # type: ignore[no-untyped-call]
            False,
        )
        pixmap.clear_with(128)  # type: ignore[no-untyped-call]
        page.insert_image(page.rect, pixmap=pixmap)
        return cast(bytes, document.tobytes())


def test_pdf_parser_extracts_traceable_text_from_real_fixture() -> None:
    result = build_parser_registry().parse(_request((FIXTURE_DIR / "positions.pdf").read_bytes()))

    assert result.status is ParseStatus.PARSED
    assert result.parser_name == PDF_PARSER_NAME
    text_blocks = [block for block in result.blocks if isinstance(block, TextBlock)]
    page_locations = [
        block.location for block in text_blocks if isinstance(block.location, PageLocation)
    ]
    assert len(text_blocks) == len(page_locations) == 4
    assert [location.page_number for location in page_locations] == [1, 2, 3, 4]
    assert "2026年度济宁市属事业单位公开招聘" in text_blocks[0].text
    assert result.metadata["page_count"] == 4
    text_characters = result.metadata["text_characters"]
    assert isinstance(text_characters, int)
    assert text_characters > 100


def test_pdf_parser_preserves_safe_document_and_page_metadata() -> None:
    content = _text_pdf("A sufficiently long text page. " * 10, title="Metadata example")

    result = PdfTextParser().parse(_request(content))

    assert result.status is ParseStatus.PARSED
    document_metadata = result.metadata["document_metadata"]
    pages = result.metadata["pages"]
    assert isinstance(document_metadata, dict)
    assert document_metadata["title"] == "Metadata example"
    assert document_metadata["author"] == "JOBAGENT fixture"
    assert isinstance(pages, list)
    assert pages == [{"page_number": 1, "text_characters": result.metadata["text_characters"]}]


def test_image_only_pdf_is_marked_ocr_required_without_running_ocr() -> None:
    result = PdfTextParser().parse(_request(_image_only_pdf()))

    assert result.status is ParseStatus.OCR_REQUIRED
    assert result.blocks == ()
    assert result.issues[0].code is ParseErrorCode.OCR_REQUIRED
    assert result.issues[0].retryable is False
    assert result.metadata["average_text_characters_per_page"] == 0.0


def test_low_text_pdf_retains_partial_page_evidence_for_manual_review() -> None:
    result = PdfTextParser().parse(_request(_text_pdf("short text")))

    assert result.status is ParseStatus.OCR_REQUIRED
    assert len(result.blocks) == 1
    location = result.blocks[0].location
    assert isinstance(location, PageLocation)
    assert location.page_number == 1


def test_custom_text_threshold_is_deterministic() -> None:
    parser = PdfTextParser(PdfTextPolicy(min_average_characters_per_page=5))

    result = parser.parse(_request(_text_pdf("short text")))

    assert result.status is ParseStatus.PARSED


def test_encrypted_pdf_returns_diagnostic_failure() -> None:
    result = PdfTextParser().parse(_request(_text_pdf("Protected content. " * 10, encrypted=True)))

    assert result.status is ParseStatus.FAILED
    assert result.blocks == ()
    assert result.issues[0].code is ParseErrorCode.ENCRYPTED_DOCUMENT
    assert "password" in result.issues[0].message.lower()


@pytest.mark.parametrize("content", [b"not a PDF", b"%PDF-1.7\ncorrupt"])
def test_corrupt_pdf_returns_diagnostic_failure(content: bytes) -> None:
    result = PdfTextParser().parse(_request(content))

    assert result.status is ParseStatus.FAILED
    assert result.issues[0].code is ParseErrorCode.CORRUPT_DOCUMENT


def test_pdf_parser_rejects_non_pdf_request_when_called_directly() -> None:
    request = ParseRequest(
        source=_source(media_type="application/octet-stream"),
        content=_text_pdf("A sufficiently long text page. " * 10),
    )

    result = PdfTextParser().parse(request)

    assert result.status is ParseStatus.FAILED
    assert result.issues[0].code is ParseErrorCode.INVALID_INPUT


def test_pdf_policy_rejects_non_positive_threshold() -> None:
    with pytest.raises(ValueError, match="threshold must be positive"):
        PdfTextPolicy(min_average_characters_per_page=0)


def test_default_registry_registers_pdf_and_excel_parsers_explicitly() -> None:
    registry = build_parser_registry()

    assert PDF_PARSER_NAME in registry.names
    assert PDF_MEDIA_TYPE in registry.media_types
    assert registry.select(PDF_MEDIA_TYPE) is not None
