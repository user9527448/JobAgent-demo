"""Create the core recruitment data model.

Revision ID: 0001_core_models
Revises: None
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_core_models"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("adapter", sa.String(length=100), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "crawl_interval_minutes",
            sa.Integer(),
            server_default=sa.text("1440"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "crawl_interval_minutes > 0",
            name=op.f("ck_sources_crawl_interval_positive"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sources"),
        sa.UniqueConstraint("name", name="uq_sources_name"),
    )
    op.create_index("ix_sources_enabled_category", "sources", ["enabled", "category"])

    op.create_table(
        "crawl_runs",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("source_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "stats",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name=op.f("ck_crawl_runs_finish_after_start"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'partial', 'failed', 'cancelled')",
            name=op.f("ck_crawl_runs_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            name="fk_crawl_runs_source_id_sources",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_crawl_runs"),
    )
    op.create_index("ix_crawl_runs_source_started", "crawl_runs", ["source_id", "started_at"])
    op.create_index("ix_crawl_runs_status", "crawl_runs", ["status"])

    op.create_table(
        "raw_documents",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("source_id", sa.BigInteger(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("raw_html", sa.Text(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "content_hash ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_raw_documents_content_hash_sha256"),
        ),
        sa.CheckConstraint(
            "raw_html IS NOT NULL OR raw_text IS NOT NULL",
            name=op.f("ck_raw_documents_content_present"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            name="fk_raw_documents_source_id_sources",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_raw_documents"),
        sa.UniqueConstraint(
            "source_id",
            "canonical_url",
            name="uq_raw_documents_source_canonical_url",
        ),
    )
    op.create_index("ix_raw_documents_content_hash", "raw_documents", ["content_hash"])
    op.create_index(
        "ix_raw_documents_source_published",
        "raw_documents",
        ["source_id", "published_at"],
    )

    op.create_table(
        "attachments",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("document_id", sa.BigInteger(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("file_name", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=127), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("local_path", sa.Text(), nullable=True),
        sa.Column(
            "parse_status",
            sa.String(length=32),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "parse_status IN ('pending', 'parsed', 'ocr_required', 'unsupported', 'failed')",
            name=op.f("ck_attachments_parse_status_valid"),
        ),
        sa.CheckConstraint(
            "sha256 IS NULL OR sha256 ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_attachments_sha256_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["raw_documents.id"],
            name="fk_attachments_document_id_raw_documents",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_attachments"),
        sa.UniqueConstraint("document_id", "url", name="uq_attachments_document_url"),
    )
    op.create_index(
        "ix_attachments_document_status",
        "attachments",
        ["document_id", "parse_status"],
    )
    op.create_index("ix_attachments_sha256", "attachments", ["sha256"])

    op.create_table(
        "job_posts",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("document_id", sa.BigInteger(), nullable=False),
        sa.Column("organization", sa.String(length=300), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("region", sa.String(length=100), nullable=True),
        sa.Column("apply_url", sa.Text(), nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "deadline IS NULL OR start_at IS NULL OR deadline >= start_at",
            name=op.f("ck_job_posts_deadline_after_start"),
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["raw_documents.id"],
            name="fk_job_posts_document_id_raw_documents",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_job_posts"),
        sa.UniqueConstraint("document_id", name="uq_job_posts_document_id"),
    )
    op.create_index("ix_job_posts_category_region", "job_posts", ["category", "region"])
    op.create_index("ix_job_posts_deadline", "job_posts", ["deadline"])

    op.create_table(
        "job_positions",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("post_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("department", sa.String(length=300), nullable=True),
        sa.Column("location", sa.String(length=100), nullable=True),
        sa.Column("education", sa.String(length=100), nullable=True),
        sa.Column("major", sa.Text(), nullable=True),
        sa.Column("headcount", sa.Integer(), nullable=True),
        sa.Column("requirements", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "headcount IS NULL OR headcount > 0",
            name=op.f("ck_job_positions_headcount_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["post_id"],
            ["job_posts.id"],
            name="fk_job_positions_post_id_job_posts",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_job_positions"),
    )
    op.create_index(
        "ix_job_positions_location_education",
        "job_positions",
        ["location", "education"],
    )
    op.create_index("ix_job_positions_post", "job_positions", ["post_id"])

    op.create_table(
        "field_evidence",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.BigInteger(), nullable=False),
        sa.Column("field_name", sa.String(length=100), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_document_id", sa.BigInteger(), nullable=True),
        sa.Column("source_attachment_id", sa.BigInteger(), nullable=True),
        sa.Column("quote_text", sa.Text(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("cell_reference", sa.String(length=50), nullable=True),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name=op.f("ck_field_evidence_confidence_range"),
        ),
        sa.CheckConstraint(
            "entity_type IN ('job_post', 'job_position')",
            name=op.f("ck_field_evidence_entity_type_valid"),
        ),
        sa.CheckConstraint(
            "quote_text IS NOT NULL OR page_number IS NOT NULL OR cell_reference IS NOT NULL",
            name=op.f("ck_field_evidence_locator_present"),
        ),
        sa.CheckConstraint(
            "page_number IS NULL OR page_number > 0",
            name=op.f("ck_field_evidence_page_number_positive"),
        ),
        sa.CheckConstraint(
            "(source_type = 'document' AND source_document_id IS NOT NULL "
            "AND source_attachment_id IS NULL) OR "
            "(source_type = 'attachment' AND source_attachment_id IS NOT NULL "
            "AND source_document_id IS NULL)",
            name=op.f("ck_field_evidence_source_reference_matches_type"),
        ),
        sa.CheckConstraint(
            "source_type IN ('document', 'attachment')",
            name=op.f("ck_field_evidence_source_type_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["source_attachment_id"],
            ["attachments.id"],
            name="fk_field_evidence_source_attachment_id_attachments",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["raw_documents.id"],
            name="fk_field_evidence_source_document_id_raw_documents",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_field_evidence"),
    )
    op.create_index(
        "ix_field_evidence_attachment",
        "field_evidence",
        ["source_attachment_id"],
    )
    op.create_index(
        "ix_field_evidence_document",
        "field_evidence",
        ["source_document_id"],
    )
    op.create_index(
        "ix_field_evidence_entity",
        "field_evidence",
        ["entity_type", "entity_id", "field_name"],
    )


def downgrade() -> None:
    op.drop_index("ix_field_evidence_entity", table_name="field_evidence")
    op.drop_index("ix_field_evidence_document", table_name="field_evidence")
    op.drop_index("ix_field_evidence_attachment", table_name="field_evidence")
    op.drop_table("field_evidence")

    op.drop_index("ix_job_positions_post", table_name="job_positions")
    op.drop_index("ix_job_positions_location_education", table_name="job_positions")
    op.drop_table("job_positions")

    op.drop_index("ix_job_posts_deadline", table_name="job_posts")
    op.drop_index("ix_job_posts_category_region", table_name="job_posts")
    op.drop_table("job_posts")

    op.drop_index("ix_attachments_sha256", table_name="attachments")
    op.drop_index("ix_attachments_document_status", table_name="attachments")
    op.drop_table("attachments")

    op.drop_index("ix_raw_documents_source_published", table_name="raw_documents")
    op.drop_index("ix_raw_documents_content_hash", table_name="raw_documents")
    op.drop_table("raw_documents")

    op.drop_index("ix_crawl_runs_status", table_name="crawl_runs")
    op.drop_index("ix_crawl_runs_source_started", table_name="crawl_runs")
    op.drop_table("crawl_runs")

    op.drop_index("ix_sources_enabled_category", table_name="sources")
    op.drop_table("sources")
