"""Stable contracts for deterministic daily reports and persisted snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Protocol

from jobagent.core.exceptions import JsonValue


class ReportGroup(StrEnum):
    """The four action-oriented JAI-024 report sections."""

    PRIORITY_APPLICATIONS = "priority_applications"
    CLOSING_SOON = "closing_soon"
    ADDED_TODAY = "added_today"
    NEEDS_CONFIRMATION = "needs_confirmation"


@dataclass(frozen=True, slots=True)
class ReportCandidate:
    """One current match result plus fields required to build a daily report."""

    position_id: int
    match_result_id: int
    score: int
    hard_filter_passed: bool
    organization: str | None
    title: str | None
    region: str | None
    deadline: datetime | None
    source_url: str
    added_at: datetime
    review_status: str
    validation_reasons: tuple[str, ...] = ()
    hard_filter_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.position_id <= 0 or self.match_result_id <= 0:
            raise ValueError("Report candidate identifiers must be positive.")
        if not 0 <= self.score <= 100:
            raise ValueError("Report candidate scores must be between 0 and 100.")
        if not self.source_url.strip():
            raise ValueError("Report candidates require an original-source URL.")
        _require_aware(self.added_at, "Report candidate added_at")
        if self.deadline is not None:
            _require_aware(self.deadline, "Report candidate deadline")


@dataclass(frozen=True, slots=True)
class DailyReportItem:
    """A rendered action item with explicit reason, risks, and source link."""

    position_id: int
    match_result_id: int
    organization: str | None
    title: str | None
    region: str | None
    deadline: datetime | None
    score: int
    reason: str
    risks: tuple[str, ...]
    source_url: str

    def as_json(self) -> dict[str, JsonValue]:
        """Return the canonical snapshot representation."""
        return {
            "position_id": self.position_id,
            "match_result_id": self.match_result_id,
            "organization": self.organization,
            "title": self.title,
            "region": self.region,
            "deadline": _iso(self.deadline),
            "score": self.score,
            "reason": self.reason,
            "risks": list(self.risks),
            "source_url": self.source_url,
        }


@dataclass(frozen=True, slots=True)
class DailyReportSection:
    """One stable report group, retained even when it has no items."""

    group: ReportGroup
    items: tuple[DailyReportItem, ...]

    def as_json(self) -> dict[str, JsonValue]:
        return {
            "group": self.group.value,
            "items": [item.as_json() for item in self.items],
        }


@dataclass(frozen=True, slots=True)
class DailyReport:
    """One deterministic report payload for a local calendar date."""

    report_date: date
    timezone: str
    report_version: str
    input_hash: str
    sections: tuple[DailyReportSection, ...]

    def __post_init__(self) -> None:
        if len(self.sections) != len(ReportGroup):
            raise ValueError("Daily reports require all four sections.")
        if tuple(section.group for section in self.sections) != tuple(ReportGroup):
            raise ValueError("Daily report sections must use the documented order.")
        if len(self.input_hash) != 64:
            raise ValueError("Daily report input hashes must be SHA-256 hex strings.")

    def as_json(self) -> dict[str, JsonValue]:
        return {
            "report_date": self.report_date.isoformat(),
            "timezone": self.timezone,
            "report_version": self.report_version,
            "input_hash": self.input_hash,
            "sections": [section.as_json() for section in self.sections],
        }


@dataclass(frozen=True, slots=True)
class DailyReportSnapshot:
    """A persisted report with both supported renderings."""

    id: int
    report: DailyReport
    content_hash: str
    markdown: str
    html: str
    created_at: datetime


class DailyReportOperations(Protocol):
    """Application-facing report generation and snapshot lookup boundary."""

    async def generate(self, report_date: date) -> DailyReportSnapshot: ...

    async def get(self, snapshot_id: int) -> DailyReportSnapshot: ...


def _require_aware(value: datetime, label: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must include timezone information.")


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
