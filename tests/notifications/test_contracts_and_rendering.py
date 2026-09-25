"""Deterministic notification contracts and message splitting checks."""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime

import pytest

from jobagent.notifications import (
    DeliveryFailureKind,
    DeliveryProviderError,
    DeliveryRetryPolicy,
    DeterministicDeliveryRenderer,
    ProviderDeliveryResult,
    ProviderDeliveryStatus,
)
from jobagent.reports import DailyReportSnapshot, DeterministicDailyReportBuilder, render_markdown


def test_empty_report_renders_once_and_is_deterministic() -> None:
    snapshot = _snapshot()
    renderer = DeterministicDeliveryRenderer()

    first = renderer.render(snapshot)
    second = renderer.render(snapshot)

    assert first == second
    assert first.report_snapshot_id == 17
    assert first.delivery_version == "jai-027-v1"
    assert len(first.parts) == 1
    assert first.parts[0].title == "JOBAGENT 日报 2026-09-08 [1/1]"
    assert first.parts[0].content == snapshot.markdown
    assert first.parts[0].content_hash == _hash(snapshot.markdown)


def test_renderer_prefers_heading_and_line_boundaries_then_unicode_slices() -> None:
    markdown = (
        "# JOBAGENT 日报\n\n"
        "## 优先投递\n\n"
        "### 1. Python 工程师\n\n"
        "- 单位: 示例单位\n"
        "- 风险: " + "招" * 43 + "🙂\n"
        "## 今日新增\n\n本组暂无岗位。\n"
    )
    snapshot = _snapshot(markdown=markdown)
    message = DeterministicDeliveryRenderer(body_char_limit=32).render(snapshot)

    assert len(message.parts) > 1
    assert "".join(part.content for part in message.parts) == markdown
    assert all(len(part.content) <= 32 for part in message.parts)
    assert [part.part_number for part in message.parts] == list(range(1, len(message.parts) + 1))
    assert all(part.part_count == len(message.parts) for part in message.parts)
    assert message.parts[-1].content.endswith("本组暂无岗位。\n")


def test_renderer_rejects_unsafe_limits_and_too_small_title_cap() -> None:
    with pytest.raises(ValueError, match="body limit"):
        DeterministicDeliveryRenderer(body_char_limit=18_001)
    with pytest.raises(ValueError, match="title limit"):
        DeterministicDeliveryRenderer(title_char_limit=91)
    with pytest.raises(ValueError, match="title exceeds"):
        DeterministicDeliveryRenderer(title_char_limit=10).render(_snapshot())


def test_retry_policy_and_provider_failure_classes_are_explicit() -> None:
    policy = DeliveryRetryPolicy()
    assert policy.delay_after(1) == 30
    assert policy.delay_after(2) == 60
    with pytest.raises(ValueError, match="non-final"):
        policy.delay_after(3)
    with pytest.raises(ValueError, match="cover every retry"):
        DeliveryRetryPolicy(max_attempts=3, delays_seconds=(1.0,))

    transient = DeliveryProviderError(
        "pushplus.temporary",
        kind=DeliveryFailureKind.TRANSIENT,
    )
    unknown = DeliveryProviderError(
        "pushplus.unknown",
        kind=DeliveryFailureKind.UNKNOWN,
    )
    assert transient.retryable is True
    assert transient.ambiguous is False
    assert unknown.retryable is False
    assert unknown.ambiguous is True


def test_failed_provider_result_requires_only_a_safe_code() -> None:
    assert (
        ProviderDeliveryResult(
            ProviderDeliveryStatus.FAILED,
            error_code="pushplus.delivery_failed",
        ).error_code
        == "pushplus.delivery_failed"
    )
    with pytest.raises(ValueError, match="require a safe error code"):
        ProviderDeliveryResult(ProviderDeliveryStatus.FAILED)


def _snapshot(*, markdown: str | None = None) -> DailyReportSnapshot:
    report = DeterministicDailyReportBuilder().build(
        (),
        report_date=date(2026, 9, 8),
        timezone="Asia/Shanghai",
    )
    rendered = markdown if markdown is not None else render_markdown(report)
    return DailyReportSnapshot(
        id=17,
        report=report,
        content_hash=_hash(rendered),
        markdown=rendered,
        html="<!doctype html><title>test</title>",
        created_at=datetime(2026, 9, 8, tzinfo=UTC),
    )


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()
