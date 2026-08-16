from __future__ import annotations

import pytest

from jobagent.parsers import (
    CellRangeLocation,
    LineRangeLocation,
    PageLocation,
    ParseErrorCode,
    ParseIssue,
    ParseRequest,
    ParseResult,
    ParseSource,
    ParseSourceType,
    ParseStatus,
    TableBlock,
    TableCell,
    TextBlock,
    TextBlockKind,
    normalize_media_type,
)


def _source(
    *,
    source_id: int = 9,
    source_name: str = "objects/ab/report.pdf",
    media_type: str = "application/pdf",
    source_type: ParseSourceType = ParseSourceType.ATTACHMENT,
) -> ParseSource:
    return ParseSource(
        source_type=source_type,
        source_id=source_id,
        source_name=source_name,
        media_type=media_type,
    )


def test_media_type_and_source_are_normalized() -> None:
    source = _source(source_name="  report.pdf  ", media_type=" Application/PDF ; version=1 ")

    assert normalize_media_type("Text/HTML; charset=utf-8") == "text/html"
    assert source.source_name == "report.pdf"
    assert source.media_type == "application/pdf"


@pytest.mark.parametrize(
    "value",
    ["", "pdf", "/pdf", "application/", "application /pdf", "application/pdf/zip"],
)
def test_invalid_media_type_is_rejected(value: str) -> None:
    with pytest.raises(ValueError, match="type/subtype"):
        normalize_media_type(value)


def test_parse_request_requires_content() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        ParseRequest(source=_source(), content=b"")


def test_locations_preserve_page_line_and_cell_coordinates() -> None:
    pdf_source = _source()
    html_source = _source(
        source_id=10,
        source_name="https://example.test/jobs/10",
        media_type="text/html",
        source_type=ParseSourceType.DOCUMENT,
    )
    workbook_source = _source(
        source_id=11,
        source_name="objects/cd/positions.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    page = PageLocation(source=pdf_source, page_number=2)
    lines = LineRangeLocation(source=html_source, start_line=4, end_line=8)
    cells = CellRangeLocation(
        source=workbook_source,
        sheet_name=" Positions ",
        start_cell=" a2 ",
        end_cell=" c5 ",
    )

    assert page.page_number == 2
    assert page.source.media_type == "application/pdf"
    assert (lines.start_line, lines.end_line) == (4, 8)
    assert lines.source.source_type is ParseSourceType.DOCUMENT
    assert (cells.sheet_name, cells.start_cell, cells.end_cell) == ("Positions", "A2", "C5")


@pytest.mark.parametrize(
    ("location", "message"),
    [
        (lambda source: PageLocation(source=source, page_number=0), "Page number"),
        (
            lambda source: LineRangeLocation(source=source, start_line=3, end_line=2),
            "End line",
        ),
        (
            lambda source: CellRangeLocation(
                source=source,
                sheet_name=" ",
                start_cell="A1",
                end_cell="A2",
            ),
            "Worksheet name",
        ),
        (
            lambda source: CellRangeLocation(
                source=source,
                sheet_name="Sheet1",
                start_cell="A0",
                end_cell="row2",
            ),
            "A1 notation",
        ),
        (
            lambda source: CellRangeLocation(
                source=source,
                sheet_name="Sheet1",
                start_cell="B2",
                end_cell="A1",
            ),
            "End cell",
        ),
    ],
)
def test_invalid_locations_are_rejected(location: object, message: str) -> None:
    location_factory = location
    assert callable(location_factory)
    with pytest.raises(ValueError, match=message):
        location_factory(_source())


def test_text_and_table_blocks_retain_source_evidence() -> None:
    source = _source(media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    heading = TextBlock(
        kind=TextBlockKind.HEADING,
        text="Open positions",
        location=LineRangeLocation(source=source, start_line=1, end_line=1),
    )
    table_location = CellRangeLocation(
        source=source,
        sheet_name="Positions",
        start_cell="A1",
        end_cell="B2",
    )
    table = TableBlock(
        location=table_location,
        rows=(
            (
                TableCell(
                    value="Role",
                    location=CellRangeLocation(
                        source=source,
                        sheet_name="Positions",
                        start_cell="A1",
                        end_cell="A1",
                    ),
                ),
                TableCell(
                    value="Location",
                    location=CellRangeLocation(
                        source=source,
                        sheet_name="Positions",
                        start_cell="B1",
                        end_cell="B1",
                    ),
                ),
            ),
        ),
    )

    result = ParseResult(
        source=source,
        status=ParseStatus.PARSED,
        parser_name="xlsx",
        blocks=(heading, table),
    )

    assert result.blocks[0].location.source is source
    assert table.rows[0][1].location.source is source
    cell_location = table.rows[0][1].location
    assert isinstance(cell_location, CellRangeLocation)
    assert cell_location.end_cell == "B1"


def test_table_rejects_cells_from_another_source() -> None:
    source = _source()
    other_source = _source(source_id=10)

    with pytest.raises(ValueError, match="table block source"):
        TableBlock(
            location=PageLocation(source=source, page_number=1),
            rows=(
                (
                    TableCell(
                        value="wrong",
                        location=PageLocation(source=other_source, page_number=1),
                    ),
                ),
            ),
        )


def test_result_requires_traceable_blocks_for_parsed_status() -> None:
    with pytest.raises(ValueError, match="at least one block"):
        ParseResult(source=_source(), status=ParseStatus.PARSED, parser_name="pdf")


def test_result_requires_diagnostic_for_non_parsed_status() -> None:
    with pytest.raises(ValueError, match="diagnostic issue"):
        ParseResult(source=_source(), status=ParseStatus.FAILED, parser_name="pdf")


def test_unsupported_result_contains_stable_error_code() -> None:
    source = _source(media_type="application/msword")

    result = ParseResult.unsupported(source)

    assert result.status is ParseStatus.UNSUPPORTED
    assert result.parser_name is None
    assert result.blocks == ()
    assert result.issues[0].code is ParseErrorCode.UNSUPPORTED_MEDIA_TYPE
    assert result.issues[0].details == {"media_type": "application/msword"}


def test_ocr_required_result_can_retain_partial_traceable_blocks() -> None:
    source = _source()
    result = ParseResult(
        source=source,
        status=ParseStatus.OCR_REQUIRED,
        parser_name="pdf",
        blocks=(
            TextBlock(
                kind=TextBlockKind.PARAGRAPH,
                text="Sparse extracted text",
                location=PageLocation(source=source, page_number=1),
            ),
        ),
        issues=(
            ParseIssue(
                code=ParseErrorCode.OCR_REQUIRED,
                message="Text density is below the supported threshold.",
            ),
        ),
    )

    location = result.blocks[0].location
    assert isinstance(location, PageLocation)
    assert location.page_number == 1
