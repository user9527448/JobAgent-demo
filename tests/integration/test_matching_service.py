"""PostgreSQL acceptance checks for JAI-023 full matching recomputation."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.orm import Session

from jobagent.db import Database
from jobagent.db.models import (
    JobPosition,
    JobPost,
    MatchResult,
    RawDocument,
    Source,
    UserPreference,
)
from jobagent.matching import RecomputeStatus, SqlAlchemyMatchingService
from jobagent.preferences import PreferenceValues, SqlAlchemyPreferenceRepository

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).parents[2]
EVALUATED_AT = datetime(2026, 8, 30, 2, 0, tzinfo=UTC)


def test_preference_signal_recomputes_every_current_position_atomically() -> None:
    database_url = _test_database_url()
    sync_engine = create_engine(database_url)
    alembic_config = _alembic_config(database_url)
    _reset_test_schema(sync_engine)

    async def scenario() -> None:
        database = Database(database_url.render_as_string(hide_password=False))
        preferences = SqlAlchemyPreferenceRepository(database.session_factory)
        matching = SqlAlchemyMatchingService(database.session_factory)
        try:
            requested = await preferences.replace(
                PreferenceValues(
                    regions=("shanghai",),
                    education="bachelor",
                    majors=("computer science",),
                    job_keywords=("python",),
                    organization_types=("state_owned",),
                    exclusions=("sales",),
                ),
                trigger_recompute=True,
            )
            first = await matching.recompute_if_requested(evaluated_at=EVALUATED_AT)

            assert first.status is RecomputeStatus.COMPLETED
            assert first.processed_count == 2
            assert first.passed_count == 1
            assert first.filtered_count == 1
            assert first.created_count == 2
            assert first.unchanged_count == 0
            assert len(first.result_ids) == 2

            async with database.session_factory() as session:
                rows = list(await session.scalars(select(MatchResult).order_by(MatchResult.id)))
                profile = await session.get(UserPreference, 1)
                assert profile is not None
                assert profile.recompute_required is False
                assert profile.updated_at == requested.updated_at
                assert len(rows) == 2
                assert [row.score for row in rows] == [100, 0]
                assert [row.hard_filter_passed for row in rows] == [True, False]
                assert all(len(row.components) == 6 for row in rows)
                assert all(len(row.matched_rules) == 4 for row in rows)
                assert all(row.is_current for row in rows)

            second = await matching.recompute_if_requested(evaluated_at=EVALUATED_AT)
            assert second.status is RecomputeStatus.NOT_REQUIRED
            assert second.processed_count == 0
            assert second.result_ids == ()

            forced = await matching.recompute_if_requested(
                evaluated_at=EVALUATED_AT + timedelta(days=1),
                force=True,
            )
            assert forced.status is RecomputeStatus.COMPLETED
            assert forced.created_count == 2
            assert len(forced.result_ids) == 2

            await preferences.replace(
                PreferenceValues(
                    regions=("shanghai",),
                    education="bachelor",
                    majors=("computer science",),
                    job_keywords=("python",),
                    organization_types=("state_owned",),
                ),
                trigger_recompute=True,
            )
            third = await matching.recompute_if_requested(evaluated_at=EVALUATED_AT)
            assert third.status is RecomputeStatus.COMPLETED
            assert third.processed_count == 2
            assert third.passed_count == 2
            assert third.created_count == 2

            async with database.session_factory() as session:
                total = await session.scalar(select(func.count()).select_from(MatchResult))
                current = await session.scalar(
                    select(func.count())
                    .select_from(MatchResult)
                    .where(MatchResult.is_current.is_(True))
                )
                current_rows = list(
                    await session.scalars(
                        select(MatchResult)
                        .where(MatchResult.is_current.is_(True))
                        .order_by(MatchResult.position_id)
                    )
                )
                assert total == 6
                assert current == 2
                assert [row.score for row in current_rows] == [100, 100]
                assert all(row.supersedes_id is not None for row in current_rows)
        finally:
            await database.close()

    try:
        command.upgrade(alembic_config, "head")
        _seed_positions(sync_engine)
        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            runner.run(scenario())
    finally:
        _reset_test_schema(sync_engine)
        sync_engine.dispose()


def _seed_positions(engine: Engine) -> None:
    source = Source(
        name="JAI-023 matching source",
        base_url="https://example.invalid",
        category="state_owned",
        adapter="matching_test",
    )
    document = RawDocument(
        source=source,
        canonical_url="https://example.invalid/jobs/1",
        title="Python campus recruitment",
        raw_text="Synthetic matching evidence",
        content_hash="c" * 64,
    )
    post = JobPost(
        document=document,
        extraction_version="matching-fixture-v1",
        version=1,
        is_current=True,
        result_hash="d" * 64,
        review_status="approved",
        recommendation_eligible=True,
        validation_version="validation-v1",
        validated_at=EVALUATED_AT,
        organization="Example State Group",
        category="state_owned",
        region="shanghai",
        deadline=EVALUATED_AT + timedelta(days=2),
    )
    post.positions.extend(
        (
            JobPosition(
                record_key="position:1",
                name="Python Engineer",
                department="Data Platform",
                location="shanghai",
                education="bachelor_or_above",
                major="Computer Science",
                requirements="Build data services",
            ),
            JobPosition(
                record_key="position:2",
                name="Python Sales Engineer",
                department="Sales",
                location="shanghai",
                education="bachelor_or_above",
                major="Computer Science",
                requirements="Support enterprise sales",
            ),
        )
    )
    with Session(engine) as session:
        session.add(post)
        session.commit()


def _test_database_url() -> URL:
    raw_url = os.getenv("JOBAGENT_TEST_DATABASE_URL")
    if raw_url is None:
        pytest.skip("Set JOBAGENT_TEST_DATABASE_URL to run PostgreSQL matching tests.")
    database_url = make_url(raw_url)
    if not (database_url.database or "").endswith("_test"):
        pytest.fail("Matching tests require a database whose name ends with '_test'.")
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
