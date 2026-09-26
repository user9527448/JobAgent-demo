"""Add append-only operator audit events for development resends.

Revision ID: 0011_delivery_operator_audit
Revises: 0010_notification_delivery
Create Date: 2026-09-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_delivery_operator_audit"
down_revision: str | None = "0010_notification_delivery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create an immutable milestone ledger for explicitly authorized resends."""
    op.create_table(
        "notification_delivery_operator_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("action_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("delivery_id", sa.BigInteger(), nullable=False),
        sa.Column("part_number", sa.Integer(), nullable=False),
        sa.Column("attempt_id", sa.BigInteger(), nullable=True),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column(
            "duplicate_risk_confirmed",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("outcome", sa.String(length=32), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "part_number > 0",
            name=op.f("ck_notification_delivery_operator_events_part_number_positive"),
        ),
        sa.CheckConstraint(
            "event_type IN ('authorized', 'started', 'completed')",
            name=op.f("ck_notification_delivery_operator_events_event_type_valid"),
        ),
        sa.CheckConstraint(
            "outcome IS NULL OR outcome IN ('succeeded', 'failed', 'unknown', 'interrupted')",
            name=op.f("ck_notification_delivery_operator_events_outcome_valid"),
        ),
        sa.CheckConstraint(
            "(event_type = 'authorized' AND attempt_id IS NULL "
            "AND reason IS NOT NULL AND length(reason) BETWEEN 10 AND 500 "
            "AND duplicate_risk_confirmed AND outcome IS NULL "
            "AND error_code IS NULL AND error_message IS NULL) OR "
            "(event_type = 'started' AND attempt_id IS NOT NULL "
            "AND reason IS NULL AND NOT duplicate_risk_confirmed AND outcome IS NULL "
            "AND error_code IS NULL AND error_message IS NULL) OR "
            "(event_type = 'completed' AND attempt_id IS NOT NULL "
            "AND reason IS NULL AND NOT duplicate_risk_confirmed AND outcome IS NOT NULL)",
            name=op.f("ck_notification_delivery_operator_events_event_payload_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["notification_delivery_attempts.id"],
            name="fk_delivery_operator_event_attempt",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["delivery_id"],
            ["notification_deliveries.id"],
            name="fk_delivery_operator_event_delivery",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_notification_delivery_operator_events"),
        ),
        sa.UniqueConstraint(
            "action_id",
            "event_type",
            name=op.f("uq_notification_delivery_operator_events_action_type"),
        ),
    )
    op.create_index(
        "ix_notification_delivery_operator_events_delivery_created",
        "notification_delivery_operator_events",
        ["delivery_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_notification_delivery_operator_events_action_created",
        "notification_delivery_operator_events",
        ["action_id", "created_at"],
        unique=False,
    )
    op.execute(
        """
        CREATE FUNCTION prevent_notification_operator_event_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'notification delivery operator events are append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_notification_operator_events_append_only
        BEFORE UPDATE OR DELETE ON notification_delivery_operator_events
        FOR EACH ROW EXECUTE FUNCTION prevent_notification_operator_event_mutation()
        """
    )


def downgrade() -> None:
    """Remove the development resend audit ledger."""
    op.execute(
        "DROP TRIGGER IF EXISTS trg_notification_operator_events_append_only "
        "ON notification_delivery_operator_events"
    )
    op.execute("DROP FUNCTION IF EXISTS prevent_notification_operator_event_mutation()")
    op.drop_index(
        "ix_notification_delivery_operator_events_action_created",
        table_name="notification_delivery_operator_events",
    )
    op.drop_index(
        "ix_notification_delivery_operator_events_delivery_created",
        table_name="notification_delivery_operator_events",
    )
    op.drop_table("notification_delivery_operator_events")
