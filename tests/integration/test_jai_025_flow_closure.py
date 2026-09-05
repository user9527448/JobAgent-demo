"""PostgreSQL acceptance for the deterministic pre-scheduler MVP flow."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.orm import Session

from jobagent.db import Database
from jobagent.db.models import DailyReportSnapshot, MatchResult, RawDocument, Source
from jobagent.extraction import (
    DeterministicFieldExtractor,
    ExtractionMerger,
    ExtractionPolicy,
    ReparseService,
    SqlAlchemyExtractionRepository,
    StoredDocumentReparsePipeline,
)
from jobagent.matching import LEGACY_SCORE_VERSION, RecomputeStatus, SqlAlchemyMatchingService
from jobagent.parsers import build_parser_registry
from jobagent.preferences import PreferenceValues, SqlAlchemyPreferenceRepository
from jobagent.reports import ReportGroup, SqlAlchemyDailyReportService

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).parents[2]
EVALUATED_AT = datetime(2026, 9, 5, 2, 0, tzinfo=UTC)
REPORT_DATE = date(2026, 9, 5)


def test_raw_document_closes_extraction_matching_and_report_flow(tmp_path: Path) -> None:
    database_url = _test_database_url()
    sync_engine = create_engine(database_url)
    alembic_config = _alembic_config(database_url)
    _reset_test_schema(sync_engine)

    try:
        command.upgrade(alembic_config, "head")
        document_id = _seed_raw_document(sync_engine)

        async def scenario() -> None:
            database = Database(database_url.render_as_string(hide_password=False))
            try:
                reparse = ReparseService(
                    StoredDocumentReparsePipeline(
                        database.session_factory,
                        tmp_path,
                        build_parser_registry(),
                        DeterministicFieldExtractor(ExtractionPolicy(timezone="Asia/Shanghai")),
                        ExtractionMerger(),
                    ),
                    SqlAlchemyExtractionRepository(database.session_factory),
                )
                extracted = await reparse.reparse(document_id, "jai-025-flow-v1")
                assert len(extracted.position_ids) == 1
                assert extracted.recommendation_eligible is True

                preferences = SqlAlchemyPreferenceRepository(database.session_factory)
                await preferences.replace(PreferenceValues(), trigger_recompute=True)
                matching = SqlAlchemyMatchingService(database.session_factory)
                first_match = await matching.recompute_if_requested(
                    evaluated_at=EVALUATED_AT,
                    score_version=LEGACY_SCORE_VERSION,
                )
                assert first_match.status is RecomputeStatus.COMPLETED
                assert first_match.processed_count == first_match.passed_count == 1

                reports = SqlAlchemyDailyReportService(
                    database.session_factory,
                    "Asia/Shanghai",
                )
                first_report = await reports.generate(REPORT_DATE)
                repeated_match = await matching.recompute_if_requested(
                    evaluated_at=EVALUATED_AT,
                    score_version=LEGACY_SCORE_VERSION,
                )
                repeated_report = await reports.generate(REPORT_DATE)

                assert repeated_match.status is RecomputeStatus.NOT_REQUIRED
                assert repeated_report.id == first_report.id
                groups = {section.group: section.items for section in first_report.report.sections}
                assert len(groups[ReportGroup.PRIORITY_APPLICATIONS]) == 1
                assert len(groups[ReportGroup.CLOSING_SOON]) == 1
                assert len(groups[ReportGroup.ADDED_TODAY]) == 1
                assert groups[ReportGroup.NEEDS_CONFIRMATION] == ()
            finally:
                await database.close()

        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            runner.run(scenario())

        with Session(sync_engine) as session:
            assert session.scalar(select(func.count()).select_from(MatchResult)) == 1
            assert session.scalar(select(func.count()).select_from(DailyReportSnapshot)) == 1
    finally:
        _reset_test_schema(sync_engine)
        sync_engine.dispose()


def _seed_raw_document(engine: Engine) -> int:
    with Session(engine) as session:
        document = RawDocument(
            source=Source(
                name="JAI-025 flow source",
                base_url="https://example.invalid",
                category="public_exam",
                adapter="flow_test",
            ),
            canonical_url="https://example.invalid/notices/25",
            title="Synthetic public-institution recruitment",
            raw_text=(
                "招聘单位: 测试大学\n"
                "招聘类型: 事业单位\n"
                "地区: 上海\n"
                "报名开始时间: 2026-09-01\n"
                "报名截止时间: 2026-09-10\n"
                "报名链接: https://apply.example.invalid/jobs\n"
                "学历: 本科\n"
                "招聘人数: 3人"
            ),
            fetched_at=EVALUATED_AT,
            content_hash="f" * 64,
        )
        session.add(document)
        session.commit()
        return document.id


def _test_database_url() -> URL:
    raw_url = os.getenv("JOBAGENT_TEST_DATABASE_URL")
    if raw_url is None:
        pytest.skip("Set JOBAGENT_TEST_DATABASE_URL to run PostgreSQL flow tests.")
    database_url = make_url(raw_url)
    if not (database_url.database or "").endswith("_test"):
        pytest.fail("Flow tests require a database whose name ends with '_test'.")
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
