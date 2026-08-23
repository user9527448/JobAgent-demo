"""Version structured entities and preserve complete extraction evidence.

Revision ID: 0004_versioned_field_evidence
Revises: 0003_attachment_storage
Create Date: 2026-08-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_versioned_field_evidence"
down_revision: str | None = "0003_attachment_storage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add append-only extraction versions and evidence values/coordinates."""
    op.drop_constraint("uq_job_posts_document_id", "job_posts", type_="unique")
    op.add_column(
        "job_posts",
        sa.Column(
            "extraction_version",
            sa.String(length=100),
            server_default=sa.text("'legacy-v1'"),
            nullable=False,
        ),
    )
    op.add_column(
        "job_posts",
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
    )
    op.add_column(
        "job_posts",
        sa.Column(
            "is_current",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column("job_posts", sa.Column("supersedes_id", sa.BigInteger(), nullable=True))
    op.add_column(
        "job_posts",
        sa.Column(
            "result_hash",
            sa.String(length=64),
            server_default=sa.text("repeat('0', 64)"),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        op.f("fk_job_posts_supersedes_id_job_posts"),
        "job_posts",
        "job_posts",
        ["supersedes_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_job_posts_document_extraction_version",
        "job_posts",
        ["document_id", "extraction_version"],
    )
    op.create_check_constraint(op.f("ck_job_posts_version_positive"), "job_posts", "version > 0")
    op.create_check_constraint(
        op.f("ck_job_posts_result_hash_sha256"),
        "job_posts",
        "result_hash ~ '^[0-9a-f]{64}$'",
    )
    op.create_check_constraint(
        op.f("ck_job_posts_supersedes_other_version"),
        "job_posts",
        "supersedes_id IS NULL OR supersedes_id <> id",
    )
    op.create_index(
        "uq_job_posts_document_current",
        "job_posts",
        ["document_id"],
        unique=True,
        postgresql_where=sa.text("is_current"),
    )
    op.create_index("ix_job_posts_supersedes_id", "job_posts", ["supersedes_id"])
    op.alter_column("job_posts", "extraction_version", server_default=None)
    op.alter_column("job_posts", "version", server_default=None)
    op.alter_column("job_posts", "result_hash", server_default=None)

    op.add_column("job_positions", sa.Column("record_key", sa.String(255), nullable=True))
    op.execute(sa.text("UPDATE job_positions SET record_key = 'legacy:' || id::text"))
    op.alter_column("job_positions", "record_key", nullable=False)
    op.alter_column(
        "job_positions",
        "name",
        existing_type=sa.String(length=300),
        nullable=True,
    )
    op.create_unique_constraint(
        "uq_job_positions_post_record_key",
        "job_positions",
        ["post_id", "record_key"],
    )

    op.drop_constraint(op.f("ck_field_evidence_locator_present"), "field_evidence", type_="check")
    op.add_column(
        "field_evidence",
        sa.Column(
            "raw_value",
            sa.Text(),
            server_default=sa.text("'legacy'"),
            nullable=False,
        ),
    )
    op.execute(sa.text("UPDATE field_evidence SET raw_value = COALESCE(quote_text, 'legacy')"))
    op.add_column(
        "field_evidence",
        sa.Column(
            "normalized_value",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'null'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "field_evidence",
        sa.Column(
            "extraction_method",
            sa.String(32),
            server_default=sa.text("'legacy'"),
            nullable=False,
        ),
    )
    op.add_column(
        "field_evidence",
        sa.Column(
            "extraction_version",
            sa.String(100),
            server_default=sa.text("'legacy-v1'"),
            nullable=False,
        ),
    )
    op.add_column(
        "field_evidence",
        sa.Column("is_selected", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.add_column(
        "field_evidence",
        sa.Column("conflict", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column("field_evidence", sa.Column("line_start", sa.Integer(), nullable=True))
    op.add_column("field_evidence", sa.Column("line_end", sa.Integer(), nullable=True))
    op.add_column("field_evidence", sa.Column("sheet_name", sa.String(200), nullable=True))
    op.alter_column(
        "field_evidence",
        "cell_reference",
        existing_type=sa.String(length=50),
        type_=sa.String(length=100),
        existing_nullable=True,
    )
    op.create_check_constraint(
        op.f("ck_field_evidence_locator_present"),
        "field_evidence",
        "quote_text IS NOT NULL OR page_number IS NOT NULL OR line_start IS NOT NULL "
        "OR cell_reference IS NOT NULL",
    )
    op.create_check_constraint(
        op.f("ck_field_evidence_line_range_valid"),
        "field_evidence",
        "(line_start IS NULL AND line_end IS NULL) OR (line_start > 0 AND line_end >= line_start)",
    )
    op.create_check_constraint(
        op.f("ck_field_evidence_extraction_method_valid"),
        "field_evidence",
        "extraction_method IN ('legacy', 'deterministic', 'llm')",
    )
    op.create_index(
        "ix_field_evidence_extraction_version",
        "field_evidence",
        ["extraction_version"],
    )
    for column in ("raw_value", "normalized_value", "extraction_method", "extraction_version"):
        op.alter_column("field_evidence", column, server_default=None)


def downgrade() -> None:
    """Remove JAI-019 metadata; requires no rows that depend on the new history fields."""
    op.drop_index("ix_field_evidence_extraction_version", table_name="field_evidence")
    op.drop_constraint(
        op.f("ck_field_evidence_extraction_method_valid"),
        "field_evidence",
        type_="check",
    )
    op.drop_constraint(op.f("ck_field_evidence_line_range_valid"), "field_evidence", type_="check")
    op.drop_constraint(op.f("ck_field_evidence_locator_present"), "field_evidence", type_="check")
    op.alter_column(
        "field_evidence",
        "cell_reference",
        existing_type=sa.String(length=100),
        type_=sa.String(length=50),
        existing_nullable=True,
    )
    for column in (
        "sheet_name",
        "line_end",
        "line_start",
        "conflict",
        "is_selected",
        "extraction_version",
        "extraction_method",
        "normalized_value",
        "raw_value",
    ):
        op.drop_column("field_evidence", column)
    op.create_check_constraint(
        op.f("ck_field_evidence_locator_present"),
        "field_evidence",
        "quote_text IS NOT NULL OR page_number IS NOT NULL OR cell_reference IS NOT NULL",
    )

    op.drop_constraint("uq_job_positions_post_record_key", "job_positions", type_="unique")
    op.alter_column(
        "job_positions",
        "name",
        existing_type=sa.String(length=300),
        nullable=False,
    )
    op.drop_column("job_positions", "record_key")

    op.drop_index("ix_job_posts_supersedes_id", table_name="job_posts")
    op.drop_index("uq_job_posts_document_current", table_name="job_posts")
    op.drop_constraint(op.f("ck_job_posts_supersedes_other_version"), "job_posts", type_="check")
    op.drop_constraint(op.f("ck_job_posts_result_hash_sha256"), "job_posts", type_="check")
    op.drop_constraint(op.f("ck_job_posts_version_positive"), "job_posts", type_="check")
    op.drop_constraint("uq_job_posts_document_extraction_version", "job_posts", type_="unique")
    op.drop_constraint(
        op.f("fk_job_posts_supersedes_id_job_posts"), "job_posts", type_="foreignkey"
    )
    for column in ("result_hash", "supersedes_id", "is_current", "version", "extraction_version"):
        op.drop_column("job_posts", column)
    op.create_unique_constraint("uq_job_posts_document_id", "job_posts", ["document_id"])
