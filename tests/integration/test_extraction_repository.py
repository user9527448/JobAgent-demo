"""PostgreSQL acceptance for versioned merged extraction and field evidence."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.orm import Session

from jobagent.core.exceptions import PermanentJobAgentError
from jobagent.db.database import Database
from jobagent.db.models import (
    Attachment,
    FieldEvidence,
    JobPosition,
    JobPost,
    RawDocument,
    Source,
    ValidationIssue,
)
from jobagent.extraction import (
    ExtractedField,
    ExtractionEvidence,
    ExtractionMergeInput,
    ExtractionMerger,
    ExtractionRecord,
    ExtractionResult,
    ExtractionWriteStatus,
    FieldName,
    MergedExtraction,
    ReviewStatus,
    SqlAlchemyExtractionRepository,
)
from jobagent.parsers import (
    CellRangeLocation,
    LineRangeLocation,
    ParseSource,
    ParseSourceType,
)

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).parents[2]


def test_reextraction_is_idempotent_and_preserves_entities_conflicts_and_evidence() -> None:
    database_url = _test_database_url()
    engine = create_engine(database_url)
    alembic_config = _alembic_config(database_url)
    _reset_test_schema(engine)

    try:
        command.upgrade(alembic_config, "head")
        with Session(engine) as session:
            document = RawDocument(
                source=Source(
                    name="JAI-019 integration source",
                    base_url="https://example.invalid",
                    category="test",
                    adapter="fake",
                ),
                canonical_url="https://example.invalid/notices/19",
                title="Versioned extraction announcement",
                raw_text="Evidenced body",
                content_hash="a" * 64,
            )
            attachment = Attachment(
                document=document,
                url="https://example.invalid/files/jobs.xlsx",
                file_name="jobs.xlsx",
            )
            session.add_all([document, attachment])
            session.commit()
            document_id = document.id
            attachment_id = attachment.id

        first_merged = _merged_result(
            document_id=document_id,
            attachment_id=attachment_id,
            extraction_version="merge-test-v1",
            organization="第一单位",
        )
        second_merged = _merged_result(
            document_id=document_id,
            attachment_id=attachment_id,
            extraction_version="merge-test-v2",
            organization="第二单位",
        )
        nondeterministic_v2 = _merged_result(
            document_id=document_id,
            attachment_id=attachment_id,
            extraction_version="merge-test-v2",
            organization="不一致单位",
        )

        async def scenario() -> tuple[int, int, tuple[int, ...], tuple[int, ...]]:
            database = Database(database_url.render_as_string(hide_password=False))
            repository = SqlAlchemyExtractionRepository(database.session_factory)
            try:
                first = await repository.save(first_merged)
                repeated = await repository.save(first_merged)
                second = await repository.save(second_merged)
                with pytest.raises(PermanentJobAgentError) as captured:
                    await repository.save(nondeterministic_v2)
                assert captured.value.code == "extraction.version_not_deterministic"

                assert first.status is ExtractionWriteStatus.CREATED
                assert first.version == 1
                assert first.previous_post_id is None
                assert first.review_status is ReviewStatus.REVIEW_REQUIRED
                assert first.recommendation_eligible is True
                assert first.validation_error_count == 0
                assert first.validation_warning_count == 2
                assert repeated.status is ExtractionWriteStatus.UNCHANGED
                assert repeated.post_id == first.post_id
                assert repeated.position_ids == first.position_ids
                assert repeated.review_status is first.review_status
                assert repeated.validation_warning_count == 2
                assert second.status is ExtractionWriteStatus.CREATED
                assert second.version == 2
                assert second.previous_post_id == first.post_id
                return first.post_id, second.post_id, first.position_ids, second.position_ids
            finally:
                await database.close()

        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            first_post_id, second_post_id, first_positions, second_positions = runner.run(
                scenario()
            )

        with Session(engine) as session:
            posts = session.scalars(select(JobPost).order_by(JobPost.version)).all()
            positions = session.scalars(
                select(JobPosition).order_by(JobPosition.post_id, JobPosition.record_key)
            ).all()
            evidence = session.scalars(
                select(FieldEvidence).order_by(FieldEvidence.entity_type, FieldEvidence.id)
            ).all()
            validation_issues = session.scalars(
                select(ValidationIssue).order_by(ValidationIssue.post_id, ValidationIssue.code)
            ).all()

        assert [post.id for post in posts] == [first_post_id, second_post_id]
        assert [post.extraction_version for post in posts] == ["merge-test-v1", "merge-test-v2"]
        assert [post.organization for post in posts] == ["第一单位", "第二单位"]
        assert [post.is_current for post in posts] == [False, True]
        assert posts[1].supersedes_id == posts[0].id
        assert all(len(post.result_hash) == 64 for post in posts)
        assert all(post.review_status == "review_required" for post in posts)
        assert all(post.recommendation_eligible for post in posts)
        assert all(post.validation_version == "validation-v1" for post in posts)
        assert all(post.validated_at is not None for post in posts)

        assert len(first_positions) == len(second_positions) == 1
        assert {position.id for position in positions} == set(first_positions + second_positions)
        assert all(position.name is None for position in positions)
        assert all(position.headcount == 6 for position in positions)
        assert all(position.education == "bachelor_or_above" for position in positions)

        assert evidence
        assert {item.entity_id for item in evidence if item.entity_type == "job_post"} == {
            first_post_id,
            second_post_id,
        }
        body_region = [
            item
            for item in evidence
            if item.entity_type == "job_post"
            and item.field_name == "region"
            and item.source_type == "document"
        ]
        attachment_region = [
            item
            for item in evidence
            if item.entity_type == "job_post"
            and item.field_name == "region"
            and item.source_type == "attachment"
        ]
        assert all(item.is_selected and not item.conflict for item in body_region)
        assert all(not item.is_selected and item.conflict for item in attachment_region)
        assert all(item.line_start == 2 and item.line_end == 4 for item in body_region)
        assert all(item.source_document_id == document_id for item in body_region)
        assert all(
            item.sheet_name == "岗位表" and item.cell_reference == "A2:C2"
            for item in attachment_region
        )
        assert all(item.source_attachment_id == attachment_id for item in attachment_region)
        assert all(item.raw_value and item.normalized_value for item in evidence)
        assert all(item.extraction_version == "deterministic-test-v1" for item in evidence)
        assert len(validation_issues) == 4
        assert {item.code for item in validation_issues} == {
            "validation.field_conflict",
            "validation.required_field_missing",
        }
        assert all(item.severity == "warning" for item in validation_issues)
        assert {item.post_id for item in validation_issues} == {first_post_id, second_post_id}
        assert session_count(engine, JobPost) == 2
    finally:
        _reset_test_schema(engine)
        engine.dispose()


def _merged_result(
    *,
    document_id: int,
    attachment_id: int,
    extraction_version: str,
    organization: str,
) -> MergedExtraction:
    document_source = ParseSource(
        source_type=ParseSourceType.DOCUMENT,
        source_id=document_id,
        source_name="announcement.html",
        media_type="text/html",
    )
    attachment_source = ParseSource(
        source_type=ParseSourceType.ATTACHMENT,
        source_id=attachment_id,
        source_name="jobs.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    body_location = LineRangeLocation(document_source, start_line=2, end_line=4)
    row_location = CellRangeLocation(attachment_source, "岗位表", "A2", "C2")
    body = ExtractionResult(
        source=document_source,
        records=(
            ExtractionRecord(
                location=body_location,
                fields=(
                    _field(FieldName.ORGANIZATION, organization, organization, body_location),
                    _field(FieldName.REGION, "北京", ("beijing",), body_location),
                    _field(
                        FieldName.START_AT,
                        "2026-08-01",
                        datetime(2026, 7, 31, 16, tzinfo=UTC),
                        body_location,
                    ),
                    _field(
                        FieldName.DEADLINE,
                        "2026-08-31",
                        datetime(2026, 8, 31, 15, 59, 59, tzinfo=UTC),
                        body_location,
                    ),
                    _field(
                        FieldName.APPLY_URL,
                        "https://apply.example.invalid/19",
                        "https://apply.example.invalid/19",
                        body_location,
                    ),
                ),
            ),
        ),
        extractor_version="deterministic-test-v1",
    )
    attachment = ExtractionResult(
        source=attachment_source,
        records=(
            ExtractionRecord(
                location=row_location,
                fields=(
                    _field(FieldName.REGION, "上海", ("shanghai",), row_location),
                    _field(FieldName.HEADCOUNT, "6人", 6, row_location),
                    _field(
                        FieldName.EDUCATION,
                        "本科及以上",
                        "bachelor_or_above",
                        row_location,
                    ),
                ),
            ),
        ),
        extractor_version="deterministic-test-v1",
    )
    return ExtractionMerger().merge(
        ExtractionMergeInput(
            document_id=document_id,
            extraction_version=extraction_version,
            deterministic_results=(body, attachment),
        )
    )


def _field(
    name: FieldName,
    raw_value: str,
    normalized_value: datetime | int | str | tuple[str, ...],
    location: LineRangeLocation | CellRangeLocation,
) -> ExtractedField:
    return ExtractedField(
        name=name,
        raw_value=raw_value,
        normalized_value=normalized_value,
        evidence=ExtractionEvidence(location=location, quote=raw_value),
        rule_id=f"test.{name.value}",
    )


def session_count(engine: Engine, model: type[JobPost]) -> int:
    with Session(engine) as session:
        return session.scalar(select(func.count()).select_from(model)) or 0


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
