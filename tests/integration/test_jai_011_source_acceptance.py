"""JAI-011 acceptance for three-source document and attachment idempotency."""

from __future__ import annotations

import asyncio
import io
import os
import zipfile
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.orm import Session

from jobagent.crawlers import (
    AttachmentStoragePolicy,
    AttachmentStorageService,
    AttachmentStoreStatus,
    HttpSourcePolicy,
    RawDocumentInput,
    RawDocumentWriteStatus,
    SourceDefinition,
    SourceHttpClient,
    SqlAlchemyAttachmentRepository,
    SqlAlchemyRawDocumentRepository,
    discover_attachment_links,
)
from jobagent.crawlers.firstjob import materialize_firstjob_fair, parse_firstjob_list
from jobagent.crawlers.jiangsu import parse_jiangsu_detail
from jobagent.crawlers.sasac import parse_sasac_detail
from jobagent.db.database import Database
from jobagent.db.models import Attachment, RawDocument, Source

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).parents[2]
FIXTURE_ROOT = PROJECT_ROOT / "tests" / "fixtures"


def test_three_sources_persist_twice_without_duplicate_documents_or_attachments(
    tmp_path: Path,
) -> None:
    database_url = _test_database_url()
    engine = create_engine(database_url)
    _reset_test_schema(engine)

    try:
        command.upgrade(_alembic_config(database_url), "head")
        sources = _create_sources(engine)
        documents = _source_documents()
        attachment_bodies: dict[str, tuple[str, bytes]] = {}

        async def verify_two_runs() -> tuple[int, int]:
            database = Database(database_url.render_as_string(hide_password=False))
            raw_repository = SqlAlchemyRawDocumentRepository(database.session_factory)
            attachment_repository = SqlAlchemyAttachmentRepository(database.session_factory)
            attachment_service = AttachmentStorageService(
                AttachmentStoragePolicy(tmp_path),
                attachment_repository,
            )
            try:
                first_writes = [
                    await raw_repository.save(sources[source_key], document)
                    for source_key, source_documents in documents.items()
                    for document in source_documents
                ]
                second_writes = [
                    await raw_repository.save(sources[source_key], document)
                    for source_key, source_documents in documents.items()
                    for document in source_documents
                ]
                assert all(
                    result.status is RawDocumentWriteStatus.CREATED for result in first_writes
                )
                assert all(
                    result.status is RawDocumentWriteStatus.UNCHANGED for result in second_writes
                )
                assert [result.document_id for result in first_writes] == [
                    result.document_id for result in second_writes
                ]
                assert all(result.version == 1 for result in second_writes)

                source_order = tuple(documents)
                writes_by_source = {
                    key: first_writes[index * 3 : (index + 1) * 3]
                    for index, key in enumerate(source_order)
                }
                attachment_pairs = (
                    ("sasac", documents["sasac"][0], writes_by_source["sasac"][0].document_id),
                    (
                        "jiangsu",
                        documents["jiangsu"][0],
                        writes_by_source["jiangsu"][0].document_id,
                    ),
                )
                download_calls = 0

                def handler(request: httpx.Request) -> httpx.Response:
                    nonlocal download_calls
                    download_calls += 1
                    mime_type, body = attachment_bodies[str(request.url)]
                    return httpx.Response(
                        200,
                        headers={"Content-Type": mime_type},
                        content=body,
                        request=request,
                    )

                for source_key, document, document_id in attachment_pairs:
                    assert document.raw_html is not None
                    candidates = discover_attachment_links(
                        document.raw_html,
                        base_url=document.url,
                    )
                    assert len(candidates) == 1
                    candidate = candidates[0]
                    attachment_bodies[candidate.url] = _attachment_body(candidate.extension)
                    policy = HttpSourcePolicy(
                        source_id=sources[source_key].id,
                        user_agent="JOBAGENT/JAI-011-acceptance",
                        min_interval_seconds=0,
                        max_attempts=1,
                    )
                    async with SourceHttpClient(
                        policy,
                        transport=httpx.MockTransport(handler),
                    ) as client:
                        first = await attachment_service.store(document_id, candidate, client)
                        second = await attachment_service.store(document_id, candidate, client)
                    assert first.status is AttachmentStoreStatus.STORED
                    assert second.status is AttachmentStoreStatus.REUSED
                    assert first.attachment_id == second.attachment_id

                firstjob_document = documents["firstjob"][0]
                assert firstjob_document.raw_html is None
                assert firstjob_document.metadata["poster_url"] == (
                    "https://www.firstjob.shec.edu.cn/stu_backend/api/public/"
                    "posters/information.png"
                )
                assert download_calls == 2
                return len(first_writes), len(attachment_pairs)
            finally:
                await database.close()

        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            expected_documents, expected_attachments = runner.run(verify_two_runs())

        with Session(engine) as session:
            document_count = session.scalar(select(func.count()).select_from(RawDocument))
            attachment_count = session.scalar(select(func.count()).select_from(Attachment))
            versions = session.scalars(select(RawDocument.version)).all()

        assert document_count == expected_documents == 9
        assert attachment_count == expected_attachments == 2
        assert versions == [1] * 9
        assert len(list((tmp_path / "objects").rglob("*.*"))) == 2
    finally:
        _reset_test_schema(engine)
        engine.dispose()


def _create_sources(engine: Engine) -> dict[str, SourceDefinition]:
    records = (
        (
            "sasac",
            Source(
                name="JAI-011 国资委招聘",
                base_url="https://www.sasac.gov.cn/",
                category="state_owned",
                adapter="sasac_recruitment",
            ),
        ),
        (
            "jiangsu",
            Source(
                name="JAI-011 江苏人事考试",
                base_url="https://jshrss.jiangsu.gov.cn/",
                category="public_exam",
                adapter="jiangsu_personnel_exam",
            ),
        ),
        (
            "firstjob",
            Source(
                name="JAI-011 上海学生就业招聘会",
                base_url="https://www.firstjob.shec.edu.cn/",
                category="campus",
                adapter="shanghai_firstjob",
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
    sasac_dir = FIXTURE_ROOT / "sasac"
    sasac_documents = tuple(
        parse_sasac_detail(
            (sasac_dir / fixture_name).read_bytes(),
            detail_url=(
                f"https://www.sasac.gov.cn/n2588035/n2588325/n2588350/c4000000{index}/content.html"
            ),
        )
        for index, fixture_name in enumerate(
            ("detail-campus.html", "detail-professional.html", "detail-graduate.html"),
            start=1,
        )
    )

    jiangsu_dir = FIXTURE_ROOT / "jiangsu"
    jiangsu_documents = tuple(
        parse_jiangsu_detail(
            (jiangsu_dir / fixture_name).read_bytes(),
            detail_url=(f"https://jshrss.jiangsu.gov.cn/art/2026/{index}/1/art_1_{index}.html"),
        )
        for index, fixture_name in enumerate(
            (
                "detail-civil-service.html",
                "detail-institution.html",
                "detail-three-support.html",
            ),
            start=1,
        )
    )

    firstjob_dir = FIXTURE_ROOT / "firstjob"
    firstjob_documents = tuple(
        materialize_firstjob_fair(
            parse_firstjob_list(
                (firstjob_dir / fixture_name).read_bytes(),
                public_base_url="https://www.firstjob.shec.edu.cn/",
            )[0],
            public_base_url="https://www.firstjob.shec.edu.cn/",
            official_owner="上海市学生事务中心",
        )
        for fixture_name in (
            "fair-information.json",
            "fair-vocational.json",
            "fair-yangtze-delta.json",
        )
    )
    return {
        "sasac": sasac_documents,
        "jiangsu": jiangsu_documents,
        "firstjob": firstjob_documents,
    }


def _attachment_body(extension: str) -> tuple[str, bytes]:
    if extension == ".pdf":
        return "application/pdf", b"%PDF-1.7\nJAI-011 source acceptance"
    if extension == ".xlsx":
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as workbook:
            workbook.writestr("[Content_Types].xml", "<Types />")
            workbook.writestr("xl/workbook.xml", "<workbook />")
        return (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            output.getvalue(),
        )
    raise AssertionError(f"Unexpected acceptance attachment extension: {extension}")


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
