"""Checks for adapter contract value-object invariants."""

from datetime import UTC, datetime

import pytest

from jobagent.crawlers import CrawlItemFailure, CrawlRunSummary, RawDocumentInput


def test_raw_document_requires_source_content() -> None:
    with pytest.raises(ValueError, match="HTML or text"):
        RawDocumentInput(url="https://example.invalid/1", title="Missing content")


def test_run_summary_parses_current_and_legacy_failures_safely() -> None:
    summary = CrawlRunSummary(
        run_id=9,
        source_id=7,
        status="partial",
        started_at=datetime(2026, 8, 14, tzinfo=UTC),
        finished_at=datetime(2026, 8, 14, 0, 1, tzinfo=UTC),
        stats={
            "failures": [
                {
                    "url": "https://example.invalid/current",
                    "step": "fetch_detail",
                    "code": "current",
                    "message": "safe",
                    "retryable": True,
                },
                {
                    "url": "https://example.invalid/legacy",
                    "code": "legacy",
                    "message": "safe",
                    "retryable": False,
                },
                {"url": 123},
            ]
        },
        error_message=None,
    )

    assert summary.failures == (
        CrawlItemFailure(
            url="https://example.invalid/current",
            step="fetch_detail",
            code="current",
            message="safe",
            retryable=True,
        ),
        CrawlItemFailure(
            url="https://example.invalid/legacy",
            step="unknown",
            code="legacy",
            message="safe",
            retryable=False,
        ),
    )
    assert summary.to_dict()["finished_at"] == "2026-08-14T00:01:00+00:00"
