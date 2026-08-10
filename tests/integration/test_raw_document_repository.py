"""PostgreSQL acceptance checks for immutable idempotent raw-document writes."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.orm import Session

from jobagent.crawlers import (
    RawDocumentInput,
    RawDocumentWriteStatus,
    SourceDefinition,
    SqlAlchemyRawDocumentRepository,
)
from jobagent.db.database import Database
from jobagent.db.models import RawDocument, Source

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).parents[2]


def test_concurrent_duplicates_are_idempotent_and_updates_preserve_evidence() -> None:
    database_url = _test_database_url()
    engine = create_engine(database_url)
    alembic_config = _alembic_config(database_url)
    _reset_test_schema(engine)

    try:
        command.upgrade(alembic_config, "head")
        with Session(engine) as session:
            source = Source(
                name="JAI-009 integration source",
                base_url="https://example.invalid/recruitment/",
                category="test",
                adapter="fake",
            )
            session.add(source)
            session.commit()
            source_definition = SourceDefinition(
                id=source.id,
                name=source.name,
                base_url=source.base_url,
                category=source.category,
                adapter=source.adapter,
                enabled=source.enabled,
            )

        first_input = RawDocumentInput(
            url="../jobs/1?utm_source=first",
            title="Original announcement",
            raw_html="<body>Original source evidence</body>",
        )
        equivalent_input = RawDocumentInput(
            url="https://EXAMPLE.invalid/jobs/1?fbclid=duplicate",
            title="Equivalent announcement",
            raw_text=" Original   source\nevidence ",
        )
        changed_input = RawDocumentInput(
            url="https://example.invalid/jobs/1",
            title="Updated announcement",
            raw_text="Updated source evidence",
            etag='"revision-2"',
            last_modified="Mon, 10 Aug 2026 01:00:00 GMT",
        )

        async def verify_repository() -> tuple[int, int]:
            database = Database(database_url.render_as_string(hide_password=False))
            repository = SqlAlchemyRawDocumentRepository(database.session_factory)
            try:
                assert await repository.get_validators(source_definition, "/jobs/missing") is None
                concurrent_results = await asyncio.gather(
                    repository.save(source_definition, first_input),
                    repository.save(source_definition, equivalent_input),
                )
                assert {result.status for result in concurrent_results} == {
                    RawDocumentWriteStatus.CREATED,
                    RawDocumentWriteStatus.UNCHANGED,
                }
                assert len({result.document_id for result in concurrent_results}) == 1
                assert all(result.version == 1 for result in concurrent_results)

                first_id = concurrent_results[0].document_id
                updated = await repository.save(source_definition, changed_input)
                assert updated.status is RawDocumentWriteStatus.UPDATED
                assert updated.version == 2
                assert updated.previous_document_id == first_id

                refreshed_validators_input = RawDocumentInput(
                    url="/jobs/1",
                    title="Updated announcement",
                    raw_text="Updated source evidence",
                    etag='"revision-2-cache"',
                )
                unchanged = await repository.save(
                    source_definition,
                    refreshed_validators_input,
                )
                assert unchanged.status is RawDocumentWriteStatus.UNCHANGED
                assert unchanged.document_id == updated.document_id
                assert unchanged.version == 2
                validators = await repository.get_validators(
                    source_definition,
                    "/jobs/1?utm_campaign=ignored",
                )
                assert validators is not None
                assert validators.etag == '"revision-2-cache"'
                assert validators.last_modified == "Mon, 10 Aug 2026 01:00:00 GMT"
                return first_id, updated.document_id
            finally:
                await database.close()

        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            first_id, updated_id = runner.run(verify_repository())

        with Session(engine) as session:
            versions = session.scalars(select(RawDocument).order_by(RawDocument.version)).all()

        assert [version.id for version in versions] == [first_id, updated_id]
        assert [version.version for version in versions] == [1, 2]
        assert [version.is_current for version in versions] == [False, True]
        assert (versions[0].raw_html, versions[0].raw_text) in {
            ("<body>Original source evidence</body>", None),
            (None, " Original   source\nevidence "),
        }
        assert versions[1].raw_text == "Updated source evidence"
        assert versions[1].etag == '"revision-2-cache"'
        assert versions[1].last_modified == "Mon, 10 Aug 2026 01:00:00 GMT"
        assert versions[0].supersedes_id is None
        assert versions[1].supersedes_id == versions[0].id
        assert len({version.canonical_url for version in versions}) == 1
    finally:
        _reset_test_schema(engine)
        engine.dispose()


def _test_database_url() -> URL:
    raw_url = os.getenv("JOBAGENT_TEST_DATABASE_URL")
    if raw_url is None:
        pytest.skip("Set JOBAGENT_TEST_DATABASE_URL to run PostgreSQL repository tests.")
    database_url = make_url(raw_url)
    if not (database_url.database or "").endswith("_test"):
        pytest.fail("Repository tests require a database whose name ends with '_test'.")
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
