"""PostgreSQL daily-report queries and immutable snapshot persistence."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date, datetime
from typing import cast

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobagent.core import PermanentJobAgentError, TransientJobAgentError
from jobagent.core.exceptions import JsonValue
from jobagent.db.models import (
    DailyReportSnapshot as DailyReportSnapshotModel,
)
from jobagent.db.models import (
    JobPosition,
    JobPost,
    MatchResult,
    RawDocument,
    ValidationIssue,
)

from .builder import CURRENT_REPORT_VERSION, DeterministicDailyReportBuilder
from .contracts import (
    DailyReport,
    DailyReportItem,
    DailyReportSection,
    DailyReportSnapshot,
    ReportCandidate,
    ReportGroup,
)
from .rendering import render_html, render_markdown


class SqlAlchemyDailyReportService:
    """Generate reports from current matches and persist idempotent snapshots."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        timezone: str,
        builder: DeterministicDailyReportBuilder | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._timezone = timezone
        self._builder = builder or DeterministicDailyReportBuilder()

    async def generate(self, report_date: date) -> DailyReportSnapshot:
        """Build and persist one report, reusing an identical existing snapshot."""
        try:
            async with self._session_factory() as session, session.begin():
                candidates = await _load_candidates(session)
                report = self._builder.build(
                    candidates,
                    report_date=report_date,
                    timezone=self._timezone,
                )
                payload = report.as_json()
                markdown = render_markdown(report)
                html = render_html(report)
                content_hash = _hash(payload)
                existing = await session.scalar(
                    select(DailyReportSnapshotModel).where(
                        DailyReportSnapshotModel.report_date == report_date,
                        DailyReportSnapshotModel.timezone == self._timezone,
                        DailyReportSnapshotModel.report_version == CURRENT_REPORT_VERSION,
                        DailyReportSnapshotModel.input_hash == report.input_hash,
                    )
                )
                if existing is not None:
                    if (
                        existing.content_hash != content_hash
                        or existing.markdown != markdown
                        or existing.html != html
                    ):
                        raise PermanentJobAgentError(
                            "The same report version and inputs produced different content.",
                            code="reports.version_not_deterministic",
                            details={"report_date": report_date.isoformat()},
                        )
                    return _snapshot(existing)

                model = DailyReportSnapshotModel(
                    report_date=report_date,
                    timezone=self._timezone,
                    report_version=CURRENT_REPORT_VERSION,
                    input_hash=report.input_hash,
                    content_hash=content_hash,
                    payload=payload,
                    markdown=markdown,
                    html=html,
                )
                session.add(model)
                await session.flush()
                return _snapshot(model)
        except SQLAlchemyError as error:
            raise TransientJobAgentError(
                "The daily report could not be generated.",
                code="reports.database_unavailable",
            ) from error

    async def get(self, snapshot_id: int) -> DailyReportSnapshot:
        """Load one immutable snapshot without recomputing current data."""
        if snapshot_id <= 0:
            raise ValueError("Report snapshot IDs must be positive.")
        try:
            async with self._session_factory() as session:
                model = await session.get(DailyReportSnapshotModel, snapshot_id)
        except SQLAlchemyError as error:
            raise TransientJobAgentError(
                "The daily report snapshot could not be loaded.",
                code="reports.database_unavailable",
            ) from error
        if model is None:
            raise PermanentJobAgentError(
                f"Daily report snapshot {snapshot_id} does not exist.",
                code="reports.snapshot_not_found",
                details={"snapshot_id": snapshot_id},
            )
        return _snapshot(model)


async def _load_candidates(session: AsyncSession) -> tuple[ReportCandidate, ...]:
    rows = (
        await session.execute(
            select(MatchResult, JobPosition, JobPost, RawDocument)
            .join(JobPosition, MatchResult.position_id == JobPosition.id)
            .join(JobPost, JobPosition.post_id == JobPost.id)
            .join(RawDocument, JobPost.document_id == RawDocument.id)
            .where(
                MatchResult.is_current.is_(True),
                JobPost.is_current.is_(True),
            )
            .order_by(JobPosition.id)
        )
    ).all()
    post_ids = sorted({post.id for _match, _position, post, _document in rows})
    reasons: dict[int, list[str]] = defaultdict(list)
    if post_ids:
        issues = await session.scalars(
            select(ValidationIssue)
            .where(ValidationIssue.post_id.in_(post_ids))
            .order_by(ValidationIssue.post_id, ValidationIssue.id)
        )
        for issue in issues:
            reasons[issue.post_id].append(issue.reason)

    return tuple(
        ReportCandidate(
            position_id=position.id,
            match_result_id=match.id,
            score=match.score,
            hard_filter_passed=match.hard_filter_passed,
            organization=post.organization,
            title=position.name or document.title,
            region=position.location or post.region,
            deadline=post.deadline,
            source_url=document.canonical_url,
            added_at=document.fetched_at,
            review_status=post.review_status,
            validation_reasons=tuple(reasons[post.id]),
            hard_filter_reasons=_failed_filter_reasons(match.matched_rules),
        )
        for match, position, post, document in rows
    )


def _failed_filter_reasons(rules: list[dict[str, JsonValue]]) -> tuple[str, ...]:
    return tuple(
        cast(str, rule["explanation"])
        for rule in rules
        if rule.get("passed") is False and isinstance(rule.get("explanation"), str)
    )


def _snapshot(model: DailyReportSnapshotModel) -> DailyReportSnapshot:
    return DailyReportSnapshot(
        id=model.id,
        report=_report(model.payload),
        content_hash=model.content_hash,
        markdown=model.markdown,
        html=model.html,
        created_at=model.created_at,
    )


def _report(payload: dict[str, JsonValue]) -> DailyReport:
    sections_value = payload.get("sections")
    if not isinstance(sections_value, list):
        raise ValueError("Persisted daily report sections are invalid.")
    sections: list[DailyReportSection] = []
    for section_value in sections_value:
        if not isinstance(section_value, dict):
            raise ValueError("Persisted daily report section is invalid.")
        items_value = section_value.get("items")
        if not isinstance(items_value, list):
            raise ValueError("Persisted daily report items are invalid.")
        sections.append(
            DailyReportSection(
                group=ReportGroup(str(section_value["group"])),
                items=tuple(_item(cast(dict[str, JsonValue], value)) for value in items_value),
            )
        )
    return DailyReport(
        report_date=date.fromisoformat(str(payload["report_date"])),
        timezone=str(payload["timezone"]),
        report_version=str(payload["report_version"]),
        input_hash=str(payload["input_hash"]),
        sections=tuple(sections),
    )


def _item(payload: dict[str, JsonValue]) -> DailyReportItem:
    deadline_value = payload.get("deadline")
    risks_value = payload.get("risks")
    if not isinstance(risks_value, list) or not all(isinstance(item, str) for item in risks_value):
        raise ValueError("Persisted daily report risks are invalid.")
    return DailyReportItem(
        position_id=int(str(payload["position_id"])),
        match_result_id=int(str(payload["match_result_id"])),
        organization=_optional_text(payload.get("organization")),
        title=_optional_text(payload.get("title")),
        region=_optional_text(payload.get("region")),
        deadline=(
            datetime.fromisoformat(str(deadline_value).replace("Z", "+00:00"))
            if deadline_value is not None
            else None
        ),
        score=int(str(payload["score"])),
        reason=str(payload["reason"]),
        risks=tuple(cast(list[str], risks_value)),
        source_url=str(payload["source_url"]),
    )


def _optional_text(value: JsonValue) -> str | None:
    return value if isinstance(value, str) else None


def _hash(payload: dict[str, JsonValue]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode()).hexdigest()
