"""JAI-021 acceptance for sources 4-5 persistence and fixture completeness."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.orm import Session

from jobagent.crawlers import (
    RawDocumentInput,
    RawDocumentWriteStatus,
    SourceDefinition,
    SqlAlchemyRawDocumentRepository,
)
from jobagent.crawlers.ncss import parse_ncss_detail, parse_ncss_list
from jobagent.crawlers.shanghai_rsj import parse_shanghai_public_institution_detail
from jobagent.crawlers.stability import evaluate_source_stability
from jobagent.db.database import Database
from jobagent.db.models import RawDocument, Source

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).parents[2]
FIXTURE_ROOT = PROJECT_ROOT / "tests" / "fixtures"


def test_sources_four_and_five_are_complete_and_idempotent() -> None:
    database_url = _test_database_url()
    engine = create_engine(database_url)
    _reset_test_schema(engine)

    try:
        command.upgrade(_alembic_config(database_url), "head")
        sources = _create_sources(engine)
        documents = _source_documents()
        assert all(
            evaluate_source_stability(
                key,
                attempted=len(source_documents),
                documents=source_documents,
                failed=0,
            ).core_field_completeness
            == 1.0
            for key, source_documents in documents.items()
        )

        async def verify_two_writes() -> tuple[int, list[int]]:
            database = Database(database_url.render_as_string(hide_password=False))
            repository = SqlAlchemyRawDocumentRepository(database.session_factory)
            try:
                first = [
                    await repository.save(sources[key], document)
                    for key, source_documents in documents.items()
                    for document in source_documents
                ]
                second = [
                    await repository.save(sources[key], document)
                    for key, source_documents in documents.items()
                    for document in source_documents
                ]
                assert all(write.status is RawDocumentWriteStatus.CREATED for write in first)
                assert all(write.status is RawDocumentWriteStatus.UNCHANGED for write in second)
                assert [write.document_id for write in first] == [
                    write.document_id for write in second
                ]
                return len(first), [write.version for write in second]
            finally:
                await database.close()

        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            expected_count, versions = runner.run(verify_two_writes())

        with Session(engine) as session:
            count = session.scalar(select(func.count()).select_from(RawDocument))
        assert count == expected_count == 6
        assert versions == [1] * 6
    finally:
        _reset_test_schema(engine)
        engine.dispose()


def _create_sources(engine: Engine) -> dict[str, SourceDefinition]:
    records = (
        (
            "ncss-jobs",
            Source(
                name="JAI-021 国家大学生就业服务平台",
                base_url="https://www.ncss.cn/",
                category="campus",
                adapter="ncss_jobs",
            ),
        ),
        (
            "shanghai-public-institution",
            Source(
                name="JAI-021 上海事业单位公开招聘",
                base_url="https://rsj.sh.gov.cn/",
                category="public_exam",
                adapter="shanghai_public_institution",
            ),
        ),
    )
    definitions: dict[str, SourceDefinition] = {}
    with Session(engine) as session:
        session.add_all([record for _, record in records])
        session.flush()
        for key, record in records:
            definitions[key] = SourceDefinition(
                id=record.id,
                name=record.name,
                base_url=record.base_url,
                category=record.category,
                adapter=record.adapter,
                enabled=record.enabled,
            )
        session.commit()
    return definitions


def _source_documents() -> dict[str, tuple[RawDocumentInput, ...]]:
    ncss_dir = FIXTURE_ROOT / "ncss"
    ncss_items = parse_ncss_list(
        (ncss_dir / "list.json").read_bytes(),
        base_url="https://www.ncss.cn/",
        include_keywords=("校招", "校园招聘", "应届", "毕业生"),
        exclude_keywords=("实习",),
    )
    ncss_documents = tuple(
        parse_ncss_detail(
            (ncss_dir / fixture_name).read_bytes(),
            detail_url=item.url,
            metadata=item.metadata,
            official_owner="教育部学生服务与素质发展中心",
        )
        for item, fixture_name in zip(
            ncss_items,
            ("detail-software.html", "detail-data.html", "detail-mechanical.html"),
            strict=True,
        )
    )

    shanghai_dir = FIXTURE_ROOT / "shanghai_rsj"
    shanghai_documents = tuple(
        parse_shanghai_public_institution_detail(
            (shanghai_dir / fixture_name).read_bytes(),
            detail_url=f"https://rsj.sh.gov.cn{path}",
            official_owner="上海市人力资源和社会保障局",
        )
        for fixture_name, path in (
            ("detail-museum.html", "/tzpgg_17408/20260825/t0035_9000001.html"),
            (
                "detail-research.html",
                "/tzpgg_17408/20260824/0123456789abcdef0123456789abcdef.html",
            ),
            ("detail-service.html", "/tzpgg_17408/20260823/t0035_9000003.html"),
        )
    )
    return {
        "ncss-jobs": ncss_documents,
        "shanghai-public-institution": shanghai_documents,
    }


def _test_database_url() -> URL:
    raw_url = os.getenv("JOBAGENT_TEST_DATABASE_URL")
    if raw_url is None:
        pytest.skip("Set JOBAGENT_TEST_DATABASE_URL to run PostgreSQL repository tests.")
    database_url = make_url(raw_url)
    if not (database_url.database or "").endswith("_test"):
        pytest.fail("Repository tests require a database whose name ends with '_test'.")
    return database_url


def _alembic_config(database_url: URL) -> Config:
    config = Config(PROJECT_ROOT / "alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url.render_as_string(hide_password=False))
    return config


def _reset_test_schema(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
