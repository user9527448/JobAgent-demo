"""PostgreSQL acceptance for specified-document idempotent reparsing."""

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

from jobagent.core.exceptions import PermanentJobAgentError
from jobagent.db import Database
from jobagent.db.models import JobPost, RawDocument, Source, ValidationIssue
from jobagent.extraction import (
    DeterministicFieldExtractor,
    ExtractionMerger,
    ExtractionPolicy,
    ExtractionWriteStatus,
    ReparseService,
    ReviewStatus,
    SqlAlchemyExtractionRepository,
    StoredDocumentReparsePipeline,
)
from jobagent.parsers import build_parser_registry

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).parents[2]


def test_reparse_is_idempotent_and_new_rule_version_preserves_history(tmp_path: Path) -> None:
    database_url = _test_database_url()
    engine = create_engine(database_url)
    alembic_config = _alembic_config(database_url)
    _reset_test_schema(engine)

    try:
        command.upgrade(alembic_config, "head")
        with Session(engine) as session:
            document = RawDocument(
                source=Source(
                    name="JAI-020 integration source",
                    base_url="https://example.invalid",
                    category="test",
                    adapter="fake",
                ),
                canonical_url="https://example.invalid/notices/20",
                title="Reparse validation announcement",
                raw_text=(
                    "招聘单位: 测试大学\n"
                    "招聘类型: 校园招聘\n"
                    "地区: 北京\n"
                    "报名开始时间: 2026-08-01\n"
                    "报名截止时间: 2026-08-31\n"
                    "报名链接: https://apply.example.invalid/jobs\n"
                    "学历: 本科\n"
                    "招聘人数: 3人"
                ),
                content_hash="b" * 64,
            )
            session.add(document)
            session.commit()
            document_id = document.id

        async def scenario() -> tuple[int, int]:
            database = Database(database_url.render_as_string(hide_password=False))
            pipeline = StoredDocumentReparsePipeline(
                database.session_factory,
                tmp_path,
                build_parser_registry(),
                DeterministicFieldExtractor(ExtractionPolicy(timezone="Asia/Shanghai")),
                ExtractionMerger(),
            )
            service = ReparseService(
                pipeline,
                SqlAlchemyExtractionRepository(database.session_factory),
            )
            try:
                first = await service.reparse(document_id, "rules-v1")
                repeated = await service.reparse(document_id, "rules-v1")
                second = await service.reparse(document_id, "rules-v2")
                with pytest.raises(PermanentJobAgentError) as captured:
                    await service.reparse(999_999, "rules-v1")
                assert captured.value.code == "reparse.document_not_found"

                assert first.status is ExtractionWriteStatus.CREATED
                assert first.review_status is ReviewStatus.APPROVED
                assert first.recommendation_eligible is True
                assert first.validation_error_count == first.validation_warning_count == 0
                assert repeated.status is ExtractionWriteStatus.UNCHANGED
                assert repeated.post_id == first.post_id
                assert repeated.result_hash == first.result_hash
                assert second.status is ExtractionWriteStatus.CREATED
                assert second.version == 2
                assert second.previous_post_id == first.post_id
                return first.post_id, second.post_id
            finally:
                await database.close()

        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            first_post_id, second_post_id = runner.run(scenario())

        with Session(engine) as session:
            posts = session.scalars(select(JobPost).order_by(JobPost.version)).all()
            issues = session.scalars(select(ValidationIssue)).all()

        assert [post.id for post in posts] == [first_post_id, second_post_id]
        assert [post.extraction_version for post in posts] == ["rules-v1", "rules-v2"]
        assert [post.is_current for post in posts] == [False, True]
        assert all(post.review_status == "approved" for post in posts)
        assert all(post.recommendation_eligible for post in posts)
        assert issues == []
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
