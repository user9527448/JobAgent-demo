"""Pure daily-report grouping, risk derivation, sorting, and hashing."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta
from typing import Final
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from jobagent.core.exceptions import JsonValue

from .contracts import (
    DailyReport,
    DailyReportItem,
    DailyReportSection,
    ReportCandidate,
    ReportGroup,
)

CURRENT_REPORT_VERSION: Final = "jai-024-v1"
PRIORITY_SCORE_MINIMUM: Final = 70
_CORE_FIELDS: Final = ("organization", "title", "region", "deadline", "source_url")


class DeterministicDailyReportBuilder:
    """Build the same four report sections for identical candidates and date."""

    def build(
        self,
        candidates: tuple[ReportCandidate, ...],
        *,
        report_date: date,
        timezone: str,
        report_version: str = CURRENT_REPORT_VERSION,
    ) -> DailyReport:
        if report_version != CURRENT_REPORT_VERSION:
            raise ValueError(f"Unsupported report version: {report_version}")
        try:
            zone = ZoneInfo(timezone)
        except ZoneInfoNotFoundError as error:
            raise ValueError(f"Unknown report timezone: {timezone}") from error
        day_start = datetime.combine(report_date, datetime.min.time(), zone).astimezone(UTC)
        next_day = datetime.combine(
            report_date + timedelta(days=1), datetime.min.time(), zone
        ).astimezone(UTC)
        closing_end = datetime.combine(
            report_date + timedelta(days=7), datetime.min.time(), zone
        ).astimezone(UTC)

        canonical = tuple(sorted(candidates, key=lambda item: item.position_id))
        input_hash = _hash(_input_payload(canonical, report_date, timezone, report_version))
        sections = (
            DailyReportSection(
                ReportGroup.PRIORITY_APPLICATIONS,
                _items(
                    (
                        candidate
                        for candidate in canonical
                        if candidate.hard_filter_passed
                        and candidate.score >= PRIORITY_SCORE_MINIMUM
                    ),
                    reason="规则评分达到优先投递阈值。",
                    order="score",
                    day_start=day_start,
                ),
            ),
            DailyReportSection(
                ReportGroup.CLOSING_SOON,
                _items(
                    (
                        candidate
                        for candidate in canonical
                        if candidate.hard_filter_passed
                        and candidate.deadline is not None
                        and day_start <= candidate.deadline.astimezone(UTC) < closing_end
                    ),
                    reason="有证据的报名截止时间在未来七个自然日内。",
                    order="deadline",
                    day_start=day_start,
                ),
            ),
            DailyReportSection(
                ReportGroup.ADDED_TODAY,
                _items(
                    (
                        candidate
                        for candidate in canonical
                        if candidate.hard_filter_passed
                        and day_start <= candidate.added_at.astimezone(UTC) < next_day
                    ),
                    reason="来源公告在本报告日期首次采集。",
                    order="added",
                    day_start=day_start,
                ),
            ),
            DailyReportSection(
                ReportGroup.NEEDS_CONFIRMATION,
                _items(
                    (
                        candidate
                        for candidate in canonical
                        if candidate.review_status != "approved" or _missing_fields(candidate)
                    ),
                    reason="校验状态或字段证据要求人工确认。",
                    order="risk",
                    day_start=day_start,
                ),
            ),
        )
        return DailyReport(
            report_date=report_date,
            timezone=timezone,
            report_version=report_version,
            input_hash=input_hash,
            sections=sections,
        )


def _items(
    candidates: Iterable[ReportCandidate],
    *,
    reason: str,
    order: str,
    day_start: datetime,
) -> tuple[DailyReportItem, ...]:
    materialized = tuple(candidates)
    if order == "deadline":
        ordered = sorted(materialized, key=_deadline_key)
    elif order == "added":
        ordered = sorted(materialized, key=_added_key)
    elif order == "risk":
        ordered = sorted(materialized, key=lambda item: _risk_key(item, day_start))
    else:
        ordered = sorted(materialized, key=_score_key)
    return tuple(
        DailyReportItem(
            position_id=item.position_id,
            match_result_id=item.match_result_id,
            organization=item.organization,
            title=item.title,
            region=item.region,
            deadline=item.deadline,
            score=item.score,
            reason=reason,
            risks=_risks(item, day_start),
            source_url=item.source_url,
        )
        for item in ordered
    )


def _missing_fields(candidate: ReportCandidate) -> tuple[str, ...]:
    values = {
        "organization": candidate.organization,
        "title": candidate.title,
        "region": candidate.region,
        "deadline": candidate.deadline,
        "source_url": candidate.source_url,
    }
    return tuple(name for name in _CORE_FIELDS if not _present(values[name]))


def _risks(candidate: ReportCandidate, day_start: datetime) -> tuple[str, ...]:
    risks: list[str] = []
    if candidate.review_status != "approved":
        risks.append(f"校验状态: {candidate.review_status}。")
    risks.extend(candidate.validation_reasons)
    if not candidate.hard_filter_passed:
        risks.extend(candidate.hard_filter_reasons)
    missing = _missing_fields(candidate)
    if missing:
        risks.append(f"缺少直接证据字段: {', '.join(missing)}。")
    if candidate.deadline is not None and day_start <= candidate.deadline.astimezone(
        UTC
    ) < day_start + timedelta(hours=72):
        risks.append("有证据的报名截止时间不足 72 小时。")
    if not risks:
        risks.append("未记录校验或字段证据风险。")
    return tuple(dict.fromkeys(risks))


def _score_key(candidate: ReportCandidate) -> tuple[object, ...]:
    return (
        -candidate.score,
        _deadline_value(candidate),
        _text(candidate.organization),
        _text(candidate.title),
        candidate.position_id,
    )


def _deadline_key(candidate: ReportCandidate) -> tuple[object, ...]:
    return (
        _deadline_value(candidate),
        -candidate.score,
        _text(candidate.organization),
        _text(candidate.title),
        candidate.position_id,
    )


def _added_key(candidate: ReportCandidate) -> tuple[object, ...]:
    return (
        -candidate.added_at.astimezone(UTC).timestamp(),
        -candidate.score,
        _text(candidate.organization),
        _text(candidate.title),
        candidate.position_id,
    )


def _risk_key(candidate: ReportCandidate, day_start: datetime) -> tuple[object, ...]:
    return (
        -len(_risks(candidate, day_start)),
        -candidate.score,
        _deadline_value(candidate),
        candidate.position_id,
    )


def _deadline_value(candidate: ReportCandidate) -> datetime:
    return (
        candidate.deadline.astimezone(UTC)
        if candidate.deadline is not None
        else datetime.max.replace(tzinfo=UTC)
    )


def _text(value: str | None) -> str:
    return unicodedata.normalize("NFKC", value or "").casefold()


def _present(value: object | None) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def _input_payload(
    candidates: tuple[ReportCandidate, ...],
    report_date: date,
    timezone: str,
    report_version: str,
) -> dict[str, JsonValue]:
    return {
        "report_date": report_date.isoformat(),
        "timezone": timezone,
        "report_version": report_version,
        "candidates": [
            {
                "position_id": item.position_id,
                "match_result_id": item.match_result_id,
                "score": item.score,
                "hard_filter_passed": item.hard_filter_passed,
                "organization": item.organization,
                "title": item.title,
                "region": item.region,
                "deadline": _iso(item.deadline),
                "source_url": item.source_url,
                "added_at": _iso(item.added_at),
                "review_status": item.review_status,
                "validation_reasons": list(item.validation_reasons),
                "hard_filter_reasons": list(item.hard_filter_reasons),
            }
            for item in candidates
        ],
    }


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _hash(payload: dict[str, JsonValue]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode()).hexdigest()
