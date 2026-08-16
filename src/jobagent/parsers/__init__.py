"""Traceable parser contracts and explicit MIME-based registration."""

from jobagent.parsers.contracts import (
    CellRangeLocation,
    DocumentParser,
    EvidenceLocation,
    LineRangeLocation,
    PageLocation,
    ParsedBlock,
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
from jobagent.parsers.excel import (
    EXCEL_PARSER_NAME,
    XLSX_MEDIA_TYPE,
    ExcelPositionTableParser,
    ExcelTablePolicy,
)
from jobagent.parsers.pdf import PDF_MEDIA_TYPE, PDF_PARSER_NAME, PdfTextParser, PdfTextPolicy
from jobagent.parsers.registry import ParserRegistry
from jobagent.parsers.regression import (
    GoldenDifference,
    GoldenReport,
    evaluate_golden_fixtures,
    serialize_parse_result,
)
from jobagent.parsers.runtime import build_parser_registry

__all__ = [
    "EXCEL_PARSER_NAME",
    "PDF_MEDIA_TYPE",
    "PDF_PARSER_NAME",
    "XLSX_MEDIA_TYPE",
    "CellRangeLocation",
    "DocumentParser",
    "EvidenceLocation",
    "ExcelPositionTableParser",
    "ExcelTablePolicy",
    "GoldenDifference",
    "GoldenReport",
    "LineRangeLocation",
    "PageLocation",
    "ParseErrorCode",
    "ParseIssue",
    "ParseRequest",
    "ParseResult",
    "ParseSource",
    "ParseSourceType",
    "ParseStatus",
    "ParsedBlock",
    "ParserRegistry",
    "PdfTextParser",
    "PdfTextPolicy",
    "TableBlock",
    "TableCell",
    "TextBlock",
    "TextBlockKind",
    "build_parser_registry",
    "evaluate_golden_fixtures",
    "normalize_media_type",
    "serialize_parse_result",
]
