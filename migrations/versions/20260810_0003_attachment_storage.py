"""Add attachment download and file-storage state.

Revision ID: 0003_attachment_storage
Revises: 0002_raw_document_versions
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_attachment_storage"
down_revision: str | None = "0002_raw_document_versions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Track attachment download outcomes separately from parsing state."""
    op.add_column("attachments", sa.Column("size_bytes", sa.BigInteger(), nullable=True))
    op.add_column(
        "attachments",
        sa.Column(
            "download_status",
            sa.String(length=32),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
    )
    op.add_column("attachments", sa.Column("error_message", sa.Text(), nullable=True))
    op.add_column(
        "attachments",
        sa.Column("downloaded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        op.f("ck_attachments_download_status_valid"),
        "attachments",
        "download_status IN ('pending', 'stored', 'failed')",
    )
    op.create_check_constraint(
        op.f("ck_attachments_size_bytes_nonnegative"),
        "attachments",
        "size_bytes IS NULL OR size_bytes >= 0",
    )
    op.create_check_constraint(
        op.f("ck_attachments_stored_metadata_present"),
        "attachments",
        "download_status <> 'stored' OR "
        "(mime_type IS NOT NULL AND sha256 IS NOT NULL "
        "AND local_path IS NOT NULL AND size_bytes IS NOT NULL "
        "AND downloaded_at IS NOT NULL)",
    )
    op.create_index(
        "ix_attachments_download_status",
        "attachments",
        ["download_status"],
    )


def downgrade() -> None:
    """Remove attachment download state while retaining original parse fields."""
    op.drop_index("ix_attachments_download_status", table_name="attachments")
    op.drop_constraint(
        op.f("ck_attachments_stored_metadata_present"),
        "attachments",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_attachments_size_bytes_nonnegative"),
        "attachments",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_attachments_download_status_valid"),
        "attachments",
        type_="check",
    )
    op.drop_column("attachments", "downloaded_at")
    op.drop_column("attachments", "error_message")
    op.drop_column("attachments", "download_status")
    op.drop_column("attachments", "size_bytes")
