"""Add immutable raw-document version chains.

Revision ID: 0002_raw_document_versions
Revises: 0001_core_models
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_raw_document_versions"
down_revision: str | None = "0001_core_models"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Replace one-row-per-URL storage with immutable version chains."""
    op.drop_constraint(
        "uq_raw_documents_source_canonical_url",
        "raw_documents",
        type_="unique",
    )
    op.add_column(
        "raw_documents",
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
    )
    op.add_column(
        "raw_documents",
        sa.Column(
            "is_current",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "raw_documents",
        sa.Column("supersedes_id", sa.BigInteger(), nullable=True),
    )
    op.add_column("raw_documents", sa.Column("etag", sa.Text(), nullable=True))
    op.add_column("raw_documents", sa.Column("last_modified", sa.Text(), nullable=True))
    op.create_check_constraint(
        op.f("ck_raw_documents_version_positive"),
        "raw_documents",
        "version > 0",
    )
    op.create_check_constraint(
        op.f("ck_raw_documents_supersedes_other_version"),
        "raw_documents",
        "supersedes_id IS NULL OR supersedes_id <> id",
    )
    op.create_foreign_key(
        "fk_raw_documents_supersedes_id_raw_documents",
        "raw_documents",
        "raw_documents",
        ["supersedes_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_raw_documents_source_canonical_url_version",
        "raw_documents",
        ["source_id", "canonical_url", "version"],
    )
    op.create_index(
        "uq_raw_documents_source_current_url",
        "raw_documents",
        ["source_id", "canonical_url"],
        unique=True,
        postgresql_where=sa.text("is_current"),
    )
    op.create_index(
        "ix_raw_documents_supersedes_id",
        "raw_documents",
        ["supersedes_id"],
    )


def downgrade() -> None:
    """Restore the original single-row URL constraint when no history conflicts."""
    op.drop_index("ix_raw_documents_supersedes_id", table_name="raw_documents")
    op.drop_index("uq_raw_documents_source_current_url", table_name="raw_documents")
    op.drop_constraint(
        "uq_raw_documents_source_canonical_url_version",
        "raw_documents",
        type_="unique",
    )
    op.drop_constraint(
        "fk_raw_documents_supersedes_id_raw_documents",
        "raw_documents",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("ck_raw_documents_supersedes_other_version"),
        "raw_documents",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_raw_documents_version_positive"),
        "raw_documents",
        type_="check",
    )
    op.drop_column("raw_documents", "supersedes_id")
    op.drop_column("raw_documents", "last_modified")
    op.drop_column("raw_documents", "etag")
    op.drop_column("raw_documents", "is_current")
    op.drop_column("raw_documents", "version")
    op.create_unique_constraint(
        "uq_raw_documents_source_canonical_url",
        "raw_documents",
        ["source_id", "canonical_url"],
    )
