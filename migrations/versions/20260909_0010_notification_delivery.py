"""Add idempotent notification delivery ledgers and pipeline stage.

Revision ID: 0010_notification_delivery
Revises: 0009_pipeline_scheduling
Create Date: 2026-09-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_notification_delivery"
down_revision: str | None = "0009_pipeline_scheduling"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create delivery ledgers and allow the explicit fifth pipeline stage."""
    op.drop_constraint(
        op.f("ck_pipeline_runs_current_stage_valid"),
        "pipeline_runs",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_pipeline_runs_current_stage_valid"),
        "pipeline_runs",
        "current_stage IS NULL OR current_stage IN "
        "('collection', 'extraction', 'matching', 'report', 'delivery')",
    )
    op.drop_constraint(
        op.f("ck_pipeline_stage_runs_stage_valid"),
        "pipeline_stage_runs",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_pipeline_stage_runs_stage_valid"),
        "pipeline_stage_runs",
        "stage IN ('collection', 'extraction', 'matching', 'report', 'delivery')",
    )

    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("report_snapshot_id", sa.BigInteger(), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("delivery_version", sa.String(length=32), nullable=False),
        sa.Column("message_hash", sa.String(length=64), nullable=False),
        sa.Column("part_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "channel IN ('pushplus_wechat')",
            name=op.f("ck_notification_deliveries_channel_valid"),
        ),
        sa.CheckConstraint(
            "length(delivery_version) > 0",
            name=op.f("ck_notification_deliveries_version_present"),
        ),
        sa.CheckConstraint(
            "message_hash ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_notification_deliveries_message_hash_sha256"),
        ),
        sa.CheckConstraint(
            "part_count > 0",
            name=op.f("ck_notification_deliveries_part_count_positive"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'sending', 'succeeded', 'failed', 'unknown')",
            name=op.f("ck_notification_deliveries_status_valid"),
        ),
        sa.CheckConstraint(
            "finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at",
            name=op.f("ck_notification_deliveries_finish_after_start"),
        ),
        sa.CheckConstraint(
            "(status = 'pending' AND started_at IS NULL AND finished_at IS NULL) OR "
            "(status = 'sending' AND started_at IS NOT NULL AND finished_at IS NULL) OR "
            "(status IN ('succeeded', 'failed', 'unknown') "
            "AND started_at IS NOT NULL AND finished_at IS NOT NULL)",
            name=op.f("ck_notification_deliveries_state_timestamps"),
        ),
        sa.ForeignKeyConstraint(
            ["report_snapshot_id"],
            ["daily_report_snapshots.id"],
            name="fk_delivery_report_snapshot",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notification_deliveries")),
        sa.UniqueConstraint(
            "report_snapshot_id",
            "channel",
            name=op.f("uq_notification_deliveries_report_channel"),
        ),
    )
    op.create_index(
        "ix_notification_deliveries_status_created",
        "notification_deliveries",
        ["status", "created_at"],
        unique=False,
    )

    op.create_table(
        "notification_delivery_attempts",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("delivery_id", sa.BigInteger(), nullable=False),
        sa.Column("part_number", sa.Integer(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("part_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("provider_message_id", sa.String(length=128), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "part_number > 0",
            name=op.f("ck_notification_delivery_attempts_part_number_positive"),
        ),
        sa.CheckConstraint(
            "attempt > 0",
            name=op.f("ck_notification_delivery_attempts_attempt_positive"),
        ),
        sa.CheckConstraint(
            "part_hash ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_notification_delivery_attempts_part_hash_sha256"),
        ),
        sa.CheckConstraint(
            "status IN ('submitting', 'accepted', 'succeeded', 'failed', 'unknown', 'interrupted')",
            name=op.f("ck_notification_delivery_attempts_status_valid"),
        ),
        sa.CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name=op.f("ck_notification_delivery_attempts_finish_after_start"),
        ),
        sa.CheckConstraint(
            "(status IN ('submitting', 'accepted') AND finished_at IS NULL) OR "
            "(status IN ('succeeded', 'failed', 'unknown', 'interrupted') "
            "AND finished_at IS NOT NULL)",
            name=op.f("ck_notification_delivery_attempts_state_timestamps"),
        ),
        sa.CheckConstraint(
            "status NOT IN ('accepted', 'succeeded') OR "
            "(provider_message_id IS NOT NULL AND length(provider_message_id) > 0)",
            name=op.f("ck_notification_delivery_attempts_provider_identity_present"),
        ),
        sa.ForeignKeyConstraint(
            ["delivery_id"],
            ["notification_deliveries.id"],
            name="fk_delivery_attempt_delivery",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notification_delivery_attempts")),
        sa.UniqueConstraint(
            "delivery_id",
            "part_number",
            "attempt",
            name=op.f("uq_notification_delivery_attempts_part_attempt"),
        ),
    )
    op.create_index(
        "ix_notification_delivery_attempts_delivery_part",
        "notification_delivery_attempts",
        ["delivery_id", "part_number", "attempt"],
        unique=False,
    )
    op.create_index(
        "ix_notification_delivery_attempts_status",
        "notification_delivery_attempts",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    """Remove delivery ledgers and restore the four-stage pipeline constraints."""
    op.drop_index(
        "ix_notification_delivery_attempts_status",
        table_name="notification_delivery_attempts",
    )
    op.drop_index(
        "ix_notification_delivery_attempts_delivery_part",
        table_name="notification_delivery_attempts",
    )
    op.drop_table("notification_delivery_attempts")
    op.drop_index(
        "ix_notification_deliveries_status_created",
        table_name="notification_deliveries",
    )
    op.drop_table("notification_deliveries")

    op.drop_constraint(
        op.f("ck_pipeline_stage_runs_stage_valid"),
        "pipeline_stage_runs",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_pipeline_stage_runs_stage_valid"),
        "pipeline_stage_runs",
        "stage IN ('collection', 'extraction', 'matching', 'report')",
    )
    op.drop_constraint(
        op.f("ck_pipeline_runs_current_stage_valid"),
        "pipeline_runs",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_pipeline_runs_current_stage_valid"),
        "pipeline_runs",
        "current_stage IS NULL OR current_stage IN "
        "('collection', 'extraction', 'matching', 'report')",
    )
