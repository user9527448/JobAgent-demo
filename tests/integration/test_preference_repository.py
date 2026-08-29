"""PostgreSQL acceptance checks for JAI-022 preference persistence."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine, make_url

from jobagent.db import Database
from jobagent.preferences import PreferenceValues, SqlAlchemyPreferenceRepository

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).parents[2]


def test_preference_replacement_persists_values_timestamp_and_recompute_signal() -> None:
    database_url = _test_database_url()
    engine = create_engine(database_url)
    alembic_config = _alembic_config(database_url)
    _reset_test_schema(engine)

    async def scenario() -> None:
        database = Database(database_url.render_as_string(hide_password=False))
        repository = SqlAlchemyPreferenceRepository(database.session_factory)
        try:
            initial = await repository.get()
            assert initial.values == PreferenceValues()
            assert initial.recompute_required is False

            values = PreferenceValues(
                regions=("shanghai", "jiangsu"),
                education="bachelor_or_above",
                majors=("计算机科学",),
                job_keywords=("Python",),
                organization_types=("state_owned",),
                exclusions=("销售",),
            )
            updated = await repository.replace(values, trigger_recompute=True)
            persisted = await repository.get()

            assert updated.values == values
            assert persisted.values == values
            assert persisted.updated_at >= initial.updated_at
            assert persisted.recompute_required is True
            assert persisted.recompute_requested_at is not None

            deferred = await repository.replace(
                PreferenceValues(regions=("beijing",)),
                trigger_recompute=False,
            )
            assert deferred.values.regions == ("beijing",)
            assert deferred.recompute_required is True
            assert deferred.recompute_requested_at == persisted.recompute_requested_at
        finally:
            await database.close()

    try:
        command.upgrade(alembic_config, "head")
        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            runner.run(scenario())
    finally:
        _reset_test_schema(engine)
        engine.dispose()


def _test_database_url() -> URL:
    raw_url = os.getenv("JOBAGENT_TEST_DATABASE_URL")
    if raw_url is None:
        pytest.skip("Set JOBAGENT_TEST_DATABASE_URL to run PostgreSQL preference tests.")
    database_url = make_url(raw_url)
    if not (database_url.database or "").endswith("_test"):
        pytest.fail("Preference tests require a database whose name ends with '_test'.")
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
