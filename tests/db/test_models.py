"""Unit checks for model registry and UTC persistence boundaries."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy.engine.default import DefaultDialect

from jobagent.db.models import Base, UTCDateTime

EXPECTED_TABLES = {
    "attachments",
    "crawl_runs",
    "daily_report_snapshots",
    "field_evidence",
    "job_positions",
    "job_posts",
    "match_results",
    "raw_documents",
    "sources",
    "user_preferences",
    "validation_issues",
}


def test_model_registry_contains_all_current_tables() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_historical_foreign_keys_restrict_deletion() -> None:
    foreign_keys = {
        foreign_key
        for table in Base.metadata.tables.values()
        for foreign_key in table.foreign_key_constraints
    }

    assert foreign_keys
    assert all(foreign_key.ondelete == "RESTRICT" for foreign_key in foreign_keys)


def test_utc_datetime_normalizes_an_aware_value() -> None:
    column_type = UTCDateTime()
    shanghai_offset = timezone(timedelta(hours=8))

    normalized = column_type.process_bind_param(
        datetime(2026, 8, 9, 16, 30, tzinfo=shanghai_offset),
        DefaultDialect(),
    )

    assert normalized == datetime(2026, 8, 9, 8, 30, tzinfo=UTC)


def test_utc_datetime_rejects_a_naive_value() -> None:
    with pytest.raises(ValueError, match="timezone information"):
        UTCDateTime().process_bind_param(datetime(2026, 8, 9, 8, 30), DefaultDialect())
