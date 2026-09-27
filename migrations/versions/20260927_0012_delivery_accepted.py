"""Add a terminal provider-accepted delivery state.

Revision ID: 0012_delivery_accepted
Revises: 0011_delivery_operator_audit
Create Date: 2026-09-27
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0012_delivery_accepted"
down_revision: str | None = "0011_delivery_operator_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Represent provider acceptance without claiming final delivery confirmation."""
    op.drop_constraint(
        op.f("ck_notification_deliveries_status_valid"),
        "notification_deliveries",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_notification_deliveries_state_timestamps"),
        "notification_deliveries",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_notification_delivery_attempts_state_timestamps"),
        "notification_delivery_attempts",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_notification_delivery_operator_events_outcome_valid"),
        "notification_delivery_operator_events",
        type_="check",
    )

    op.execute(
        "UPDATE notification_delivery_attempts "
        "SET finished_at = COALESCE(finished_at, now()), "
        "error_code = COALESCE(error_code, 'notification.provider_receipt_unavailable'), "
        "error_message = COALESCE(error_message, "
        "'Provider accepted the submission, but final delivery receipt is unavailable.') "
        "WHERE status = 'accepted'"
    )
    op.execute(
        "WITH latest AS ("
        "  SELECT DISTINCT ON (delivery_id, part_number) "
        "    delivery_id, part_number, status, finished_at, error_code "
        "  FROM notification_delivery_attempts "
        "  ORDER BY delivery_id, part_number, attempt DESC"
        "), summaries AS ("
        "  SELECT delivery_id, count(*) AS part_count, "
        "    bool_and(status IN ('accepted', 'succeeded')) AS all_accepted, "
        "    bool_or(status = 'accepted') AS any_accepted, "
        "    max(finished_at) AS finished_at, "
        "    min(error_code) FILTER (WHERE status = 'accepted') AS error_code "
        "  FROM latest GROUP BY delivery_id"
        ") UPDATE notification_deliveries AS delivery "
        "SET status = 'accepted', "
        "finished_at = COALESCE(summary.finished_at, now()), "
        "error_code = COALESCE(summary.error_code, "
        "'notification.provider_receipt_unavailable'), "
        "error_message = 'Provider accepted every message part, but final delivery receipt "
        "is unavailable.', updated_at = now() "
        "FROM summaries AS summary "
        "WHERE delivery.id = summary.delivery_id "
        "AND delivery.status = 'sending' "
        "AND summary.part_count = delivery.part_count "
        "AND summary.all_accepted AND summary.any_accepted"
    )

    op.create_check_constraint(
        op.f("ck_notification_deliveries_status_valid"),
        "notification_deliveries",
        "status IN ('pending', 'sending', 'accepted', 'succeeded', 'failed', 'unknown')",
    )
    op.create_check_constraint(
        op.f("ck_notification_deliveries_state_timestamps"),
        "notification_deliveries",
        "(status = 'pending' AND started_at IS NULL AND finished_at IS NULL) OR "
        "(status = 'sending' AND started_at IS NOT NULL AND finished_at IS NULL) OR "
        "(status IN ('accepted', 'succeeded', 'failed', 'unknown') "
        "AND started_at IS NOT NULL AND finished_at IS NOT NULL)",
    )
    op.create_check_constraint(
        op.f("ck_notification_delivery_attempts_state_timestamps"),
        "notification_delivery_attempts",
        "(status = 'submitting' AND finished_at IS NULL) OR "
        "(status IN ('accepted', 'succeeded', 'failed', 'unknown', 'interrupted') "
        "AND finished_at IS NOT NULL)",
    )
    op.create_check_constraint(
        op.f("ck_notification_delivery_operator_events_outcome_valid"),
        "notification_delivery_operator_events",
        "outcome IS NULL OR outcome IN "
        "('accepted', 'succeeded', 'failed', 'unknown', 'interrupted')",
    )


def downgrade() -> None:
    """Conservatively map accepted evidence to unknown for the older schema."""
    op.execute(
        "DROP TRIGGER IF EXISTS trg_notification_operator_events_append_only "
        "ON notification_delivery_operator_events"
    )
    op.execute(
        "UPDATE notification_deliveries SET status = 'unknown', "
        "error_code = COALESCE(error_code, 'notification.accepted_downgraded'), "
        "error_message = COALESCE(error_message, "
        "'Provider acceptance was preserved conservatively during downgrade.') "
        "WHERE status = 'accepted'"
    )
    op.execute(
        "UPDATE notification_delivery_attempts SET status = 'unknown', "
        "error_code = COALESCE(error_code, 'notification.accepted_downgraded'), "
        "error_message = COALESCE(error_message, "
        "'Provider acceptance was preserved conservatively during downgrade.') "
        "WHERE status = 'accepted'"
    )
    op.execute(
        "UPDATE notification_delivery_operator_events "
        "SET outcome = 'unknown', "
        "error_code = COALESCE(error_code, 'notification.accepted_downgraded'), "
        "error_message = COALESCE(error_message, "
        "'Provider acceptance was preserved conservatively during downgrade.') "
        "WHERE outcome = 'accepted'"
    )

    op.drop_constraint(
        op.f("ck_notification_delivery_operator_events_outcome_valid"),
        "notification_delivery_operator_events",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_notification_delivery_attempts_state_timestamps"),
        "notification_delivery_attempts",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_notification_deliveries_state_timestamps"),
        "notification_deliveries",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_notification_deliveries_status_valid"),
        "notification_deliveries",
        type_="check",
    )

    op.create_check_constraint(
        op.f("ck_notification_delivery_operator_events_outcome_valid"),
        "notification_delivery_operator_events",
        "outcome IS NULL OR outcome IN ('succeeded', 'failed', 'unknown', 'interrupted')",
    )
    op.create_check_constraint(
        op.f("ck_notification_delivery_attempts_state_timestamps"),
        "notification_delivery_attempts",
        "(status IN ('submitting', 'accepted') AND finished_at IS NULL) OR "
        "(status IN ('succeeded', 'failed', 'unknown', 'interrupted') "
        "AND finished_at IS NOT NULL)",
    )
    op.create_check_constraint(
        op.f("ck_notification_deliveries_state_timestamps"),
        "notification_deliveries",
        "(status = 'pending' AND started_at IS NULL AND finished_at IS NULL) OR "
        "(status = 'sending' AND started_at IS NOT NULL AND finished_at IS NULL) OR "
        "(status IN ('succeeded', 'failed', 'unknown') "
        "AND started_at IS NOT NULL AND finished_at IS NOT NULL)",
    )
    op.create_check_constraint(
        op.f("ck_notification_deliveries_status_valid"),
        "notification_deliveries",
        "status IN ('pending', 'sending', 'succeeded', 'failed', 'unknown')",
    )
    op.execute(
        """
        CREATE TRIGGER trg_notification_operator_events_append_only
        BEFORE UPDATE OR DELETE ON notification_delivery_operator_events
        FOR EACH ROW EXECUTE FUNCTION prevent_notification_operator_event_mutation()
        """
    )
