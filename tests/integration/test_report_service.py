"""PostgreSQL acceptance for JAI-024 report querying and snapshots."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.orm import Session

from jobagent.db import Database
from jobagent.db.models import (
    DailyReportSnapshot,
    JobPosition,
    JobPost,
    MatchResult,
    RawDocument,
    Source,
    UserPreference,
    ValidationIssue,
)
from jobagent.reports import ReportGroup, SqlAlchemyDailyReportService

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).parents[2]
REPORT_DATE = date(2026, 9, 3)
DAY_START = datetime(2026, 9, 3, tzinfo=UTC)


def test_report_service_groups_renders_and_reuses_identical_snapshot() -> None:
    database_url = _test_database_url()
    engine = create_engine(database_url)
    alembic_config = _alembic_config(database_url)
    _reset_test_schema(engine)

    async def scenario() -> None:
        database = Database(database_url.render_as_string(hide_password=False))
        service = SqlAlchemyDailyReportService(database.session_factory, "UTC")
        try:
            first = await service.generate(REPORT_DATE)
            second = await service.generate(REPORT_DATE)
            loaded = await service.get(first.id)

            assert first.id == second.id == loaded.id
            assert first.content_hash == second.content_hash == loaded.content_hash
            groups = {section.group: section.items for section in first.report.sections}
            assert [item.position_id for item in groups[ReportGroup.PRIORITY_APPLICATIONS]] == [1]
            assert [item.position_id for item in groups[ReportGroup.CLOSING_SOON]] == [1]
            assert [item.position_id for item in groups[ReportGroup.ADDED_TODAY]] == [1]
            assert [item.position_id for item in groups[ReportGroup.NEEDS_CONFIRMATION]] == [2]
            assert groups[ReportGroup.NEEDS_CONFIRMATION][0].organization is None
            assert any(
                "人工确认" in risk for risk in groups[ReportGroup.NEEDS_CONFIRMATION][0].risks
            )
            assert "https://example.invalid/jobs/1" in first.markdown
            assert 'rel="noopener noreferrer"' in first.html

            async with database.session_factory() as session:
                count = await session.scalar(select(func.count()).select_from(DailyReportSnapshot))
                assert count == 1
        finally:
            await database.close()

    try:
        command.upgrade(alembic_config, "head")
        _seed_report_inputs(engine)
        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            runner.run(scenario())
    finally:
        _reset_test_schema(engine)
        engine.dispose()


def _seed_report_inputs(engine: Engine) -> None:
    source = Source(
        name="JAI-024 report source",
        base_url="https://example.invalid",
        category="state_owned",
        adapter="report_test",
    )
    first_document = RawDocument(
        source=source,
        canonical_url="https://example.invalid/jobs/1",
        title="Priority recruitment",
        raw_text="Synthetic priority evidence",
        fetched_at=DAY_START + timedelta(hours=1),
        content_hash="1" * 64,
    )
    first_post = JobPost(
        document=first_document,
        extraction_version="report-fixture-v1",
        version=1,
        is_current=True,
        result_hash="2" * 64,
        review_status="approved",
        recommendation_eligible=True,
        validation_version="validation-v1",
        validated_at=DAY_START,
        organization="示例国企",
        category="state_owned",
        region="shanghai",
        deadline=DAY_START + timedelta(days=2),
    )
    first_position = JobPosition(
        post=first_post,
        record_key="position:1",
        name="Python 工程师",
        location="shanghai",
        education="bachelor",
    )

    second_document = RawDocument(
        source=source,
        canonical_url="https://example.invalid/jobs/2",
        title="Needs confirmation",
        raw_text="Synthetic incomplete evidence",
        fetched_at=DAY_START - timedelta(days=1),
        content_hash="3" * 64,
    )
    second_post = JobPost(
        document=second_document,
        extraction_version="report-fixture-v1",
        version=1,
        is_current=True,
        result_hash="4" * 64,
        review_status="review_required",
        recommendation_eligible=True,
        validation_version="validation-v1",
        validated_at=DAY_START,
        organization=None,
        category="state_owned",
        region=None,
        deadline=DAY_START + timedelta(days=10),
    )
    second_position = JobPosition(
        post=second_post,
        record_key="position:2",
        name="数据岗位",
        education="bachelor",
    )
    second_post.validation_issues.append(
        ValidationIssue(
            issue_key="5" * 64,
            code="validation.missing_region",
            severity="warning",
            entity_type="job_post",
            entity_key="post",
            field_name="region",
            reason="地区字段需要人工确认。",
        )
    )

    with Session(engine) as session:
        session.add_all((first_position, second_position))
        session.flush()
        preference = session.get(UserPreference, 1)
        assert preference is not None
        session.add_all(
            (
                _match(first_position.id, 90, preference.updated_at, "6"),
                _match(second_position.id, 60, preference.updated_at, "7"),
            )
        )
        session.commit()


def _match(
    position_id: int,
    score: int,
    preference_updated_at: datetime,
    hash_character: str,
) -> MatchResult:
    return MatchResult(
        position_id=position_id,
        preference_id=1,
        score_version="jai-023-v1",
        input_hash=hash_character * 64,
        preference_hash="8" * 64,
        result_hash="9" * 64 if position_id == 1 else "a" * 64,
        hard_filter_passed=True,
        score=score,
        components=[],
        matched_rules=[],
        evaluated_at=DAY_START,
        preference_updated_at=preference_updated_at,
        is_current=True,
    )


def _test_database_url() -> URL:
    raw_url = os.getenv("JOBAGENT_TEST_DATABASE_URL")
    if raw_url is None:
        pytest.skip("Set JOBAGENT_TEST_DATABASE_URL to run PostgreSQL report tests.")
    database_url = make_url(raw_url)
    if not (database_url.database or "").endswith("_test"):
        pytest.fail("Report tests require a database whose name ends with '_test'.")
    return database_url


def _alembic_config(database_url: URL) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    rendered_url = database_url.render_as_string(hide_password=False).replace("%", "%%")
    config.set_main_option("sqlalchemy.url", rendered_url)
    return config


def _reset_test_schema(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
