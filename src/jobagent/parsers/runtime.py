"""Explicit construction of the production parser registry."""

from jobagent.parsers.pdf import PdfTextParser, PdfTextPolicy
from jobagent.parsers.registry import ParserRegistry


def build_parser_registry(*, pdf_policy: PdfTextPolicy | None = None) -> ParserRegistry:
    """Register only parser implementations explicitly shipped by the application."""
    registry = ParserRegistry()
    registry.register(PdfTextParser(pdf_policy))
    return registry
