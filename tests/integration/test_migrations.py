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

from jobagent.db.models import RawDocument, Source, UserPreference

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).parents[2]
CORE_TABLES = {
    "apscheduler_jobs",
    "attachments",
    "crawl_runs",
    "daily_report_snapshots",
    "field_evidence",
    "job_positions",
    "job_posts",
    "match_results",
    "pipeline_runs",
    "pipeline_stage_runs",
    "raw_documents",
    "sources",
    "user_preferences",
    "validation_issues",
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


def test_jai_019_and_jai_020_upgrades_backfill_existing_structured_rows() -> None:
    database_url = _test_database_url()
    engine = create_engine(database_url)
    alembic_config = _alembic_config(database_url)
    _reset_test_schema(engine)

    try:
        command.upgrade(alembic_config, "0003_attachment_storage")
        with engine.begin() as connection:
            source_id = connection.scalar(
                text(
                    "INSERT INTO sources (name, base_url, category, adapter) "
                    "VALUES ('legacy extraction source', 'https://example.invalid', "
                    "'test', 'legacy') RETURNING id"
                )
            )
            document_id = connection.scalar(
                text(
                    "INSERT INTO raw_documents "
                    "(source_id, canonical_url, title, raw_text, content_hash) "
                    "VALUES (:source_id, 'https://example.invalid/legacy', 'Legacy', "
                    "'Legacy evidence', :content_hash) RETURNING id"
                ),
                {"source_id": source_id, "content_hash": "b" * 64},
            )
            post_id = connection.scalar(
                text(
                    "INSERT INTO job_posts (document_id, organization) "
                    "VALUES (:document_id, 'Legacy organization') RETURNING id"
                ),
                {"document_id": document_id},
            )
            position_id = connection.scalar(
                text(
                    "INSERT INTO job_positions (post_id, name) "
                    "VALUES (:post_id, 'Legacy position') RETURNING id"
                ),
                {"post_id": post_id},
            )
            evidence_id = connection.scalar(
                text(
                    "INSERT INTO field_evidence "
                    "(entity_type, entity_id, field_name, source_type, source_document_id, "
                    "quote_text, confidence) VALUES "
                    "('job_post', :post_id, 'organization', 'document', :document_id, "
                    "'Legacy organization', 1.0) RETURNING id"
                ),
                {"post_id": post_id, "document_id": document_id},
            )

        command.upgrade(alembic_config, "head")
        command.check(alembic_config)

        with engine.connect() as connection:
            post = connection.execute(
                text(
                    "SELECT extraction_version, version, is_current, result_hash, "
                    "review_status, recommendation_eligible, validation_version, "
                    "validated_at IS NOT NULL "
                    "FROM job_posts WHERE id = :id"
                ),
                {"id": post_id},
            ).one()
            position = connection.execute(
                text("SELECT record_key, name FROM job_positions WHERE id = :id"),
                {"id": position_id},
            ).one()
            evidence = connection.execute(
                text(
                    "SELECT raw_value, normalized_value, extraction_method, "
                    "extraction_version, is_selected, conflict "
                    "FROM field_evidence WHERE id = :id"
                ),
                {"id": evidence_id},
            ).one()
            validation_issue_count = connection.scalar(
                text("SELECT count(*) FROM validation_issues WHERE post_id = :post_id"),
                {"post_id": post_id},
            )

        assert post == (
            "legacy-v1",
            1,
            True,
            "0" * 64,
            "review_required",
            False,
            "legacy-unvalidated",
            True,
        )
        assert position == (f"legacy:{position_id}", "Legacy position")
        assert evidence == (
            "Legacy organization",
            None,
            "legacy",
            "legacy-v1",
            True,
            False,
        )
        assert validation_issue_count == 0
    finally:
        _reset_test_schema(engine)
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
    with Session(engine) as session:
        preferences = session.get(UserPreference, 1)
        assert preferences is not None
        assert preferences.regions == []
        assert preferences.education is None
        assert preferences.majors == []
        assert preferences.job_keywords == []
        assert preferences.organization_types == []
        assert preferences.exclusions == []
        assert preferences.recompute_required is False
        assert preferences.recompute_requested_at is None

    with Session(engine) as session:
        session.add(UserPreference(id=2))
        with pytest.raises(IntegrityError):
            session.commit()

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(text("UPDATE user_preferences SET education = 'unknown' WHERE id = 1"))

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(text("UPDATE user_preferences SET regions = '{}'::jsonb WHERE id = 1"))

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
