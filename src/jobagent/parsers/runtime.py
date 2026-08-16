"""Explicit construction of the production parser registry."""

from jobagent.parsers.excel import ExcelPositionTableParser, ExcelTablePolicy
from jobagent.parsers.pdf import PdfTextParser, PdfTextPolicy
from jobagent.parsers.registry import ParserRegistry


def build_parser_registry(
    *,
    pdf_policy: PdfTextPolicy | None = None,
    excel_policy: ExcelTablePolicy | None = None,
) -> ParserRegistry:
    """Register only parser implementations explicitly shipped by the application."""
    registry = ParserRegistry()
    registry.register(PdfTextParser(pdf_policy))
    registry.register(ExcelPositionTableParser(excel_policy))
    return registry
