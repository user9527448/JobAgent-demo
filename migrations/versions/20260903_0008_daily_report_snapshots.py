"""Add deterministic daily report snapshots.

Revision ID: 0008_daily_report_snapshots
Revises: 0007_versioned_match_results
Create Date: 2026-09-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_daily_report_snapshots"
down_revision: str | None = "0007_versioned_match_results"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create immutable snapshots keyed by report date and canonical input."""
    op.create_table(
        "daily_report_snapshots",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("timezone", sa.String(length=100), nullable=False),
        sa.Column("report_version", sa.String(length=100), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("markdown", sa.Text(), nullable=False),
        sa.Column("html", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "content_hash ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_daily_report_snapshots_content_hash_sha256"),
        ),
        sa.CheckConstraint(
            "input_hash ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_daily_report_snapshots_input_hash_sha256"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(payload) = 'object'",
            name=op.f("ck_daily_report_snapshots_payload_object"),
        ),
        sa.CheckConstraint(
            "length(report_version) > 0",
            name=op.f("ck_daily_report_snapshots_report_version_present"),
        ),
        sa.CheckConstraint(
            "length(timezone) > 0",
            name=op.f("ck_daily_report_snapshots_timezone_present"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_daily_report_snapshots")),
        sa.UniqueConstraint(
            "report_date",
            "timezone",
            "report_version",
            "input_hash",
            name=op.f("uq_daily_report_snapshots_input"),
        ),
    )
    op.create_index(
        "ix_daily_report_snapshots_date_created",
        "daily_report_snapshots",
        ["report_date", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove daily report snapshots."""
    op.drop_index(
        "ix_daily_report_snapshots_date_created",
        table_name="daily_report_snapshots",
    )
    op.drop_table("daily_report_snapshots")
