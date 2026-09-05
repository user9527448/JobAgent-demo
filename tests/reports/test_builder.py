"""Deterministic JAI-024 grouping, ordering, risk, and rendering checks."""

from datetime import UTC, date, datetime, timedelta

import pytest

from jobagent.reports import (
    DailyReportSection,
    DeterministicDailyReportBuilder,
    ReportCandidate,
    ReportGroup,
    render_html,
    render_markdown,
)

REPORT_DATE = date(2026, 9, 3)
DAY_START = datetime(2026, 9, 3, tzinfo=UTC)


def test_builder_keeps_all_groups_and_empty_report_is_explicit() -> None:
    report = DeterministicDailyReportBuilder().build(
        (), report_date=REPORT_DATE, timezone="Asia/Shanghai"
    )

    assert tuple(section.group for section in report.sections) == tuple(ReportGroup)
    assert all(section.items == () for section in report.sections)
    assert render_markdown(report).count("本组暂无岗位。") == 4
    assert render_html(report).count("本组暂无岗位。") == 4


def test_builder_groups_overlapping_actions_and_retains_evidence_gaps() -> None:
    priority = _candidate(
        position_id=1,
        score=90,
        deadline=DAY_START + timedelta(days=2),
        added_at=DAY_START + timedelta(hours=1),
    )
    confirmation = _candidate(
        position_id=2,
        score=60,
        organization=None,
        region=None,
        deadline=DAY_START + timedelta(days=10),
        added_at=DAY_START - timedelta(days=1),
        review_status="review_required",
        validation_reasons=("附件表头需要人工确认。",),
    )
    filtered = _candidate(
        position_id=3,
        score=0,
        hard_filter_passed=False,
        deadline=DAY_START + timedelta(days=1),
        added_at=DAY_START + timedelta(hours=2),
        hard_filter_reasons=("The candidate education is below the requirement.",),
    )

    report = DeterministicDailyReportBuilder().build(
        (confirmation, filtered, priority), report_date=REPORT_DATE, timezone="UTC"
    )
    groups = {section.group: section.items for section in report.sections}

    assert [item.position_id for item in groups[ReportGroup.PRIORITY_APPLICATIONS]] == [1]
    assert [item.position_id for item in groups[ReportGroup.CLOSING_SOON]] == [1]
    assert [item.position_id for item in groups[ReportGroup.ADDED_TODAY]] == [1]
    assert [item.position_id for item in groups[ReportGroup.NEEDS_CONFIRMATION]] == [2]
    assert groups[ReportGroup.NEEDS_CONFIRMATION][0].organization is None
    assert groups[ReportGroup.NEEDS_CONFIRMATION][0].region is None
    assert groups[ReportGroup.NEEDS_CONFIRMATION][0].risks == (
        "校验状态: review_required。",
        "附件表头需要人工确认。",
        "缺少直接证据字段: organization, region。",
    )


def test_same_inputs_have_stable_hash_order_and_rendering() -> None:
    lower_id = _candidate(position_id=4, score=80)
    higher_id = _candidate(position_id=5, score=80)
    builder = DeterministicDailyReportBuilder()

    first = builder.build((higher_id, lower_id), report_date=REPORT_DATE, timezone="Asia/Shanghai")
    second = builder.build((lower_id, higher_id), report_date=REPORT_DATE, timezone="Asia/Shanghai")

    assert first == second
    priority = first.sections[0]
    assert isinstance(priority, DailyReportSection)
    assert [item.position_id for item in priority.items] == [4, 5]
    assert render_markdown(first) == render_markdown(second)
    assert render_html(first) == render_html(second)


def test_local_day_and_seven_day_boundaries_use_report_timezone() -> None:
    local_midnight_utc = datetime(2026, 9, 2, 16, tzinfo=UTC)
    before_closing_boundary = datetime(2026, 9, 9, 15, 59, 59, tzinfo=UTC)
    at_closing_boundary = datetime(2026, 9, 9, 16, tzinfo=UTC)
    included = _candidate(
        position_id=10,
        deadline=before_closing_boundary,
        added_at=local_midnight_utc,
    )
    excluded = _candidate(
        position_id=11,
        deadline=at_closing_boundary,
        added_at=local_midnight_utc - timedelta(seconds=1),
    )

    report = DeterministicDailyReportBuilder().build(
        (excluded, included), report_date=REPORT_DATE, timezone="Asia/Shanghai"
    )
    groups = {section.group: section.items for section in report.sections}

    assert [item.position_id for item in groups[ReportGroup.CLOSING_SOON]] == [10]
    assert [item.position_id for item in groups[ReportGroup.ADDED_TODAY]] == [10]


def test_html_escapes_source_content_and_retains_original_link() -> None:
    report = DeterministicDailyReportBuilder().build(
        (
            _candidate(
                title="<script>alert(1)</script>",
                source_url="https://example.invalid/jobs/1?a=1&b=2",
            ),
        ),
        report_date=REPORT_DATE,
        timezone="UTC",
    )

    rendered = render_html(report)
    assert "<script>" not in rendered
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered
    assert 'href="https://example.invalid/jobs/1?a=1&amp;b=2"' in rendered
    assert 'rel="noopener noreferrer"' in rendered


def test_report_boundaries_reject_naive_dates_and_unknown_versions() -> None:
    with pytest.raises(ValueError, match="timezone information"):
        _candidate(added_at=datetime(2026, 9, 3))
    with pytest.raises(ValueError, match="Unsupported report version"):
        DeterministicDailyReportBuilder().build(
            (),
            report_date=REPORT_DATE,
            timezone="UTC",
            report_version="future-v2",
        )
    with pytest.raises(ValueError, match="Unknown report timezone"):
        DeterministicDailyReportBuilder().build((), report_date=REPORT_DATE, timezone="Mars/Base")


def _candidate(
    *,
    position_id: int = 1,
    score: int = 80,
    hard_filter_passed: bool = True,
    organization: str | None = "示例单位",
    title: str | None = "Python 工程师",
    region: str | None = "shanghai",
    deadline: datetime | None = DAY_START + timedelta(days=20),
    source_url: str = "https://example.invalid/jobs/1",
    added_at: datetime = DAY_START - timedelta(days=2),
    review_status: str = "approved",
    validation_reasons: tuple[str, ...] = (),
    hard_filter_reasons: tuple[str, ...] = (),
) -> ReportCandidate:
    return ReportCandidate(
        position_id=position_id,
        match_result_id=100 + position_id,
        score=score,
        hard_filter_passed=hard_filter_passed,
        organization=organization,
        title=title,
        region=region,
        deadline=deadline,
        source_url=source_url,
        added_at=added_at,
        review_status=review_status,
        validation_reasons=validation_reasons,
        hard_filter_reasons=hard_filter_reasons,
    )
