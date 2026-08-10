"""PostgreSQL and filesystem acceptance check for JAI-010 attachment storage."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.orm import Session

from jobagent.crawlers import (
    AttachmentCandidate,
    AttachmentStoragePolicy,
    AttachmentStorageService,
    AttachmentStoreStatus,
    HttpSourcePolicy,
    SourceHttpClient,
    SqlAlchemyAttachmentRepository,
)
from jobagent.db.database import Database
from jobagent.db.models import Attachment, RawDocument, Source

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).parents[2]


def test_repeated_attachment_storage_reuses_one_database_row_and_file(tmp_path: Path) -> None:
    database_url = _test_database_url()
    engine = create_engine(database_url)
    alembic_config = _alembic_config(database_url)
    _reset_test_schema(engine)
    content = b"%PDF-1.7\nJAI-010 integration attachment"
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            headers={"Content-Type": "application/pdf"},
            content=content,
            request=request,
        )

    try:
        command.upgrade(alembic_config, "head")
        with Session(engine) as session:
            document = RawDocument(
                source=Source(
                    name="JAI-010 integration source",
                    base_url="https://example.invalid",
                    category="test",
                    adapter="fake",
                ),
                canonical_url="https://example.invalid/notices/1",
                title="Attachment integration document",
                raw_text="Document body",
                content_hash="a" * 64,
            )
            session.add(document)
            session.commit()
            document_id = document.id

        candidate = AttachmentCandidate(
            url="https://example.invalid/files/positions.pdf",
            file_name="positions.pdf",
            extension=".pdf",
        )

        async def verify_storage() -> tuple[int, str]:
            database = Database(database_url.render_as_string(hide_password=False))
            repository = SqlAlchemyAttachmentRepository(database.session_factory)
            service = AttachmentStorageService(AttachmentStoragePolicy(tmp_path), repository)
            policy = HttpSourcePolicy(
                source_id=1,
                user_agent="JOBAGENT/0.1 (+https://example.invalid/contact)",
                min_interval_seconds=0,
                max_attempts=1,
            )
            try:
                async with SourceHttpClient(
                    policy,
                    transport=httpx.MockTransport(handler),
                ) as client:
                    first = await service.store(document_id, candidate, client)
                    second = await service.store(document_id, candidate, client)
                assert first.status is AttachmentStoreStatus.STORED
                assert second.status is AttachmentStoreStatus.REUSED
                assert first.attachment_id == second.attachment_id
                return first.attachment_id, first.local_path
            finally:
                await database.close()

        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            attachment_id, local_path = runner.run(verify_storage())

        with Session(engine) as session:
            attachments = session.scalars(select(Attachment)).all()

        assert len(attachments) == 1
        assert attachments[0].id == attachment_id
        assert attachments[0].download_status == "stored"
        assert attachments[0].parse_status == "pending"
        assert attachments[0].size_bytes == len(content)
        assert attachments[0].downloaded_at is not None
        assert (tmp_path / local_path).read_bytes() == content
        assert calls == 1
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
