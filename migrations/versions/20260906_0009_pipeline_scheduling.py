"""Add persistent scheduling and pipeline execution ledgers.

Revision ID: 0009_pipeline_scheduling
Revises: 0008_daily_report_snapshots
Create Date: 2026-09-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_pipeline_scheduling"
down_revision: str | None = "0008_daily_report_snapshots"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the APScheduler store and durable domain execution ledgers."""
    op.create_table(
        "apscheduler_jobs",
        sa.Column("id", sa.Unicode(length=191), nullable=False),
        sa.Column("next_run_time", sa.Float(precision=25), nullable=True),
        sa.Column("job_state", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_apscheduler_jobs")),
    )
    op.create_index(
        "ix_apscheduler_jobs_next_run_time",
        "apscheduler_jobs",
        ["next_run_time"],
        unique=False,
    )

    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("job_name", sa.String(length=100), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("timezone", sa.String(length=100), nullable=False),
        sa.Column("trigger", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("current_stage", sa.String(length=32), nullable=True),
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
            "current_stage IS NULL OR current_stage IN "
            "('collection', 'extraction', 'matching', 'report')",
            name=op.f("ck_pipeline_runs_current_stage_valid"),
        ),
        sa.CheckConstraint(
            "finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at",
            name=op.f("ck_pipeline_runs_finish_after_start"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'partial', 'failed', 'cancelled')",
            name=op.f("ck_pipeline_runs_status_valid"),
        ),
        sa.CheckConstraint(
            "trigger IN ('scheduled', 'makeup')",
            name=op.f("ck_pipeline_runs_trigger_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pipeline_runs")),
        sa.UniqueConstraint(
            "job_name",
            "scheduled_for",
            name=op.f("uq_pipeline_runs_job_scheduled"),
        ),
    )
    op.create_index(
        "ix_pipeline_runs_status_scheduled",
        "pipeline_runs",
        ["status", "scheduled_for"],
        unique=False,
    )

    op.create_table(
        "pipeline_stage_runs",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("pipeline_run_id", sa.BigInteger(), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="running", nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "output",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "attempt > 0",
            name=op.f("ck_pipeline_stage_runs_attempt_positive"),
        ),
        sa.CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name=op.f("ck_pipeline_stage_runs_finish_after_start"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(output) = 'object'",
            name=op.f("ck_pipeline_stage_runs_output_object"),
        ),
        sa.CheckConstraint(
            "stage IN ('collection', 'extraction', 'matching', 'report')",
            name=op.f("ck_pipeline_stage_runs_stage_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'partial', 'failed', 'interrupted')",
            name=op.f("ck_pipeline_stage_runs_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline_runs.id"],
            name="fk_pipeline_stage_runs_pipeline_run_id_pipeline_runs",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pipeline_stage_runs")),
        sa.UniqueConstraint(
            "pipeline_run_id",
            "stage",
            "attempt",
            name=op.f("uq_pipeline_stage_runs_attempt"),
        ),
    )
    op.create_index(
        "ix_pipeline_stage_runs_run_stage",
        "pipeline_stage_runs",
        ["pipeline_run_id", "stage"],
        unique=False,
    )
    op.create_index(
        "ix_pipeline_stage_runs_status",
        "pipeline_stage_runs",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    """Remove pipeline ledgers and the APScheduler job store."""
    op.drop_index("ix_pipeline_stage_runs_status", table_name="pipeline_stage_runs")
    op.drop_index("ix_pipeline_stage_runs_run_stage", table_name="pipeline_stage_runs")
    op.drop_table("pipeline_stage_runs")
    op.drop_index("ix_pipeline_runs_status_scheduled", table_name="pipeline_runs")
    op.drop_table("pipeline_runs")
    op.drop_index("ix_apscheduler_jobs_next_run_time", table_name="apscheduler_jobs")
    op.drop_table("apscheduler_jobs")
