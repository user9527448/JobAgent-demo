"""Persist validation findings and recommendation review state.

Revision ID: 0005_validation_review_reparse
Revises: 0004_versioned_field_evidence
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_validation_review_reparse"
down_revision: str | None = "0004_versioned_field_evidence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add review eligibility and durable validation reasons per extraction version."""
    op.add_column(
        "job_posts",
        sa.Column(
            "review_status",
            sa.String(length=32),
            server_default=sa.text("'review_required'"),
            nullable=False,
        ),
    )
    op.add_column(
        "job_posts",
        sa.Column(
            "recommendation_eligible",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "job_posts",
        sa.Column(
            "validation_version",
            sa.String(length=100),
            server_default=sa.text("'legacy-unvalidated'"),
            nullable=False,
        ),
    )
    op.add_column(
        "job_posts",
        sa.Column(
            "validated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        op.f("ck_job_posts_review_status_valid"),
        "job_posts",
        "review_status IN ('approved', 'review_required', 'blocked')",
    )
    op.create_check_constraint(
        op.f("ck_job_posts_validation_version_present"),
        "job_posts",
        "length(validation_version) > 0",
    )
    op.create_index(
        "ix_job_posts_current_recommendation_eligible",
        "job_posts",
        ["is_current", "recommendation_eligible"],
    )
    for column in (
        "review_status",
        "recommendation_eligible",
        "validation_version",
        "validated_at",
    ):
        op.alter_column("job_posts", column, server_default=None)

    op.create_table(
        "validation_issues",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("post_id", sa.BigInteger(), nullable=False),
        sa.Column("issue_key", sa.String(length=64), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_key", sa.String(length=255), nullable=False),
        sa.Column("field_name", sa.String(length=100), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "entity_type IN ('job_post', 'job_position')",
            name=op.f("ck_validation_issues_entity_type_valid"),
        ),
        sa.CheckConstraint(
            "issue_key ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_validation_issues_issue_key_sha256"),
        ),
        sa.CheckConstraint(
            "severity IN ('warning', 'error')",
            name=op.f("ck_validation_issues_severity_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["post_id"],
            ["job_posts.id"],
            name=op.f("fk_validation_issues_post_id_job_posts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_validation_issues")),
        sa.UniqueConstraint(
            "post_id",
            "issue_key",
            name="uq_validation_issues_post_key",
        ),
    )
    op.create_index(
        "ix_validation_issues_post_severity",
        "validation_issues",
        ["post_id", "severity"],
    )
    op.create_index(
        "ix_validation_issues_code",
        "validation_issues",
        ["code"],
    )


def downgrade() -> None:
    """Remove JAI-020 validation state and findings."""
    op.drop_index("ix_validation_issues_code", table_name="validation_issues")
    op.drop_index("ix_validation_issues_post_severity", table_name="validation_issues")
    op.drop_table("validation_issues")

    op.drop_index("ix_job_posts_current_recommendation_eligible", table_name="job_posts")
    op.drop_constraint(
        op.f("ck_job_posts_validation_version_present"),
        "job_posts",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_job_posts_review_status_valid"),
        "job_posts",
        type_="check",
    )
    for column in (
        "validated_at",
        "validation_version",
        "recommendation_eligible",
        "review_status",
    ):
        op.drop_column("job_posts", column)
