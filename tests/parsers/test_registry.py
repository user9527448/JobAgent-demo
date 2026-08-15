from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import pytest

from jobagent.core.exceptions import ConfigurationError, PermanentJobAgentError
from jobagent.parsers import (
    PageLocation,
    ParseRequest,
    ParseResult,
    ParserRegistry,
    ParseSource,
    ParseSourceType,
    ParseStatus,
    TextBlock,
    TextBlockKind,
)


def _source(
    *,
    source_id: int = 5,
    media_type: str = "application/pdf",
) -> ParseSource:
    return ParseSource(
        source_type=ParseSourceType.ATTACHMENT,
        source_id=source_id,
        source_name=f"objects/source-{source_id}.pdf",
        media_type=media_type,
    )


@dataclass
class FakeParser:
    name: str = "fixture-pdf"
    supported_media_types: Iterable[str] = ("Application/PDF; version=1",)
    result_name: str | None = None
    result_source: ParseSource | None = None

    def parse(self, request: ParseRequest) -> ParseResult:
        source = self.result_source or request.source
        return ParseResult(
            source=source,
            status=ParseStatus.PARSED,
            parser_name=self.result_name or self.name,
            blocks=(
                TextBlock(
                    kind=TextBlockKind.PARAGRAPH,
                    text=request.content.decode(),
                    location=PageLocation(source=source, page_number=1),
                ),
            ),
        )


def test_registry_selects_parser_by_normalized_media_type() -> None:
    registry = ParserRegistry()
    parser = FakeParser()
    registry.register(parser)
    request = ParseRequest(source=_source(), content=b"parsed text")

    result = registry.parse(request)

    assert registry.select(" APPLICATION/PDF ; charset=binary") is parser
    assert registry.names == ("fixture-pdf",)
    assert registry.media_types == ("application/pdf",)
    assert result.status is ParseStatus.PARSED
    assert result.blocks[0].location.source == request.source


def test_registry_selects_html_pdf_and_excel_parsers_by_mime_type() -> None:
    registry = ParserRegistry()
    html = FakeParser(name="html", supported_media_types=("text/html",))
    pdf = FakeParser(name="pdf", supported_media_types=("application/pdf",))
    excel = FakeParser(
        name="excel",
        supported_media_types=(
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
    )

    registry.register(html)
    registry.register(pdf)
    registry.register(excel)

    assert registry.select("text/html") is html
    assert registry.select("application/pdf") is pdf
    assert registry.select("application/vnd.ms-excel") is excel
    assert (
        registry.select("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        is excel
    )


def test_registry_returns_explicit_unsupported_result() -> None:
    source = _source(media_type="application/msword")

    result = ParserRegistry().parse(ParseRequest(source=source, content=b"document"))

    assert result.status is ParseStatus.UNSUPPORTED
    assert result.issues[0].code.value == "parser.unsupported_media_type"


def test_registry_rejects_duplicate_parser_name() -> None:
    registry = ParserRegistry()
    registry.register(FakeParser())

    with pytest.raises(ConfigurationError) as error_info:
        registry.register(FakeParser(supported_media_types=("text/html",)))

    assert error_info.value.code == "parser.name_duplicate"


def test_registry_rejects_duplicate_media_type_atomically() -> None:
    registry = ParserRegistry()
    registry.register(FakeParser())

    with pytest.raises(ConfigurationError) as error_info:
        registry.register(
            FakeParser(
                name="second-parser",
                supported_media_types=("application/pdf", "text/html"),
            )
        )

    assert error_info.value.code == "parser.media_type_duplicate"
    assert registry.names == ("fixture-pdf",)
    assert registry.select("text/html") is None


@pytest.mark.parametrize(
    ("parser", "code"),
    [
        (FakeParser(name=" "), "parser.name_empty"),
        (FakeParser(name="empty-media", supported_media_types=()), "parser.media_types_empty"),
        (
            FakeParser(name="bad-media", supported_media_types=("not-a-media-type",)),
            "parser.media_type_invalid",
        ),
    ],
)
def test_registry_rejects_invalid_parser_declarations(
    parser: FakeParser,
    code: str,
) -> None:
    with pytest.raises(ConfigurationError) as error_info:
        ParserRegistry().register(parser)

    assert error_info.value.code == code


def test_registry_rejects_invalid_selection_media_type() -> None:
    with pytest.raises(PermanentJobAgentError) as error_info:
        ParserRegistry().select("pdf")

    assert error_info.value.code == "parser.media_type_invalid"


def test_registry_rejects_result_for_another_source() -> None:
    registry = ParserRegistry()
    registry.register(FakeParser(result_source=_source(source_id=6)))

    with pytest.raises(PermanentJobAgentError) as error_info:
        registry.parse(ParseRequest(source=_source(), content=b"text"))

    assert error_info.value.code == "parser.output_source_mismatch"


def test_registry_rejects_inconsistent_result_parser_name() -> None:
    registry = ParserRegistry()
    registry.register(FakeParser(result_name="another-parser"))

    with pytest.raises(PermanentJobAgentError) as error_info:
        registry.parse(ParseRequest(source=_source(), content=b"text"))

    assert error_info.value.code == "parser.output_name_mismatch"
