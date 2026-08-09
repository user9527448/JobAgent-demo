"""PostgreSQL migration and persistence acceptance checks for JAI-006."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from jobagent.db.models import RawDocument, Source

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).parents[2]
CORE_TABLES = {
    "attachments",
    "crawl_runs",
    "field_evidence",
    "job_positions",
    "job_posts",
    "raw_documents",
    "sources",
}


def test_empty_database_upgrade_constraints_utc_and_downgrade() -> None:
    database_url = _test_database_url()
    engine = create_engine(database_url)
    alembic_config = _alembic_config(database_url)
    _reset_test_schema(engine)

    try:
        command.upgrade(alembic_config, "head")
        assert set(inspect(engine).get_table_names()) >= CORE_TABLES
        command.check(alembic_config)
        _verify_persistence_invariants(engine)

        command.downgrade(alembic_config, "base")
        assert not (CORE_TABLES & set(inspect(engine).get_table_names()))
    finally:
        engine.dispose()


def _test_database_url() -> URL:
    raw_url = os.getenv("JOBAGENT_TEST_DATABASE_URL")
    if raw_url is None:
        pytest.skip("Set JOBAGENT_TEST_DATABASE_URL to run PostgreSQL migration tests.")
    database_url = make_url(raw_url)
    database_name = database_url.database or ""
    if not database_name.endswith("_test"):
        pytest.fail("Migration tests require a database whose name ends with '_test'.")
    return database_url


def _alembic_config(database_url: URL) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    rendered_url = database_url.render_as_string(hide_password=False).replace("%", "%%")
    config.set_main_option("sqlalchemy.url", rendered_url)
    return config


def _reset_test_schema(engine: Engine) -> None:
    # The caller validates the _test suffix before this destructive reset.
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))


def _verify_persistence_invariants(engine: Engine) -> None:
    source = Source(
        name="JAI-006 integration source",
        base_url="https://example.invalid",
        category="public_institution",
        adapter="integration_test",
    )
    shanghai_time = datetime(2026, 8, 9, 16, 30, tzinfo=timezone(timedelta(hours=8)))
    document = RawDocument(
        source=source,
        canonical_url="https://example.invalid/jobs/1",
        title="Integration document",
        raw_text="Immutable source text",
        published_at=shanghai_time,
        content_hash="a" * 64,
    )

    with Session(engine) as session:
        session.add(document)
        session.commit()
        document_id = document.id
        source_id = source.id

        assert document.published_at == datetime(2026, 8, 9, 8, 30, tzinfo=UTC)
        source.enabled = False
        session.commit()
        assert (
            session.scalar(
                select(func.count()).select_from(RawDocument).where(RawDocument.id == document_id)
            )
            == 1
        )

    duplicate = RawDocument(
        source_id=source_id,
        canonical_url="https://example.invalid/jobs/1",
        title="Duplicate",
        raw_text="Must be rejected",
        content_hash="b" * 64,
    )
    with Session(engine) as session:
        session.add(duplicate)
        with pytest.raises(IntegrityError):
            session.commit()

    with Session(engine) as session:
        persisted_source = session.get(Source, source_id)
        assert persisted_source is not None
        session.delete(persisted_source)
        with pytest.raises(IntegrityError):
            session.commit()
