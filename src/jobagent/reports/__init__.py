"""Deterministic daily report construction, rendering, and persistence."""

from .builder import (
    CURRENT_REPORT_VERSION,
    PRIORITY_SCORE_MINIMUM,
    DeterministicDailyReportBuilder,
)
from .contracts import (
    DailyReport,
    DailyReportItem,
    DailyReportOperations,
    DailyReportSection,
    DailyReportSnapshot,
    ReportCandidate,
    ReportGroup,
)
from .persistence import SqlAlchemyDailyReportService
from .rendering import render_html, render_markdown

__all__ = [
    "CURRENT_REPORT_VERSION",
    "PRIORITY_SCORE_MINIMUM",
    "DailyReport",
    "DailyReportItem",
    "DailyReportOperations",
    "DailyReportSection",
    "DailyReportSnapshot",
    "DeterministicDailyReportBuilder",
    "ReportCandidate",
    "ReportGroup",
    "SqlAlchemyDailyReportService",
    "render_html",
    "render_markdown",
]
