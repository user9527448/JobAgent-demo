"""Add the single-user structured preference profile.

Revision ID: 0006_single_user_preferences
Revises: 0005_validation_review_reparse
Create Date: 2026-08-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_single_user_preferences"
down_revision: str | None = "0005_validation_review_reparse"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create one non-filtering default profile and its recomputation signal."""
    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "regions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("education", sa.String(length=50), nullable=True),
        sa.Column(
            "majors",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "job_keywords",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "organization_types",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "exclusions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "recompute_required",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("recompute_requested_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint("id = 1", name=op.f("ck_user_preferences_single_user")),
        sa.CheckConstraint(
            "jsonb_typeof(regions) = 'array'",
            name=op.f("ck_user_preferences_regions_array"),
        ),
        sa.CheckConstraint(
            "education IS NULL OR education IN "
            "('no_requirement', 'doctorate', 'master_or_above', 'master', "
            "'bachelor_or_above', 'bachelor', 'associate_or_above', 'associate', "
            "'secondary_vocational', 'high_school')",
            name=op.f("ck_user_preferences_education_valid"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(majors) = 'array'",
            name=op.f("ck_user_preferences_majors_array"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(job_keywords) = 'array'",
            name=op.f("ck_user_preferences_job_keywords_array"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(organization_types) = 'array'",
            name=op.f("ck_user_preferences_organization_types_array"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(exclusions) = 'array'",
            name=op.f("ck_user_preferences_exclusions_array"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_preferences")),
    )
    op.execute(sa.text("INSERT INTO user_preferences (id) VALUES (1)"))


def downgrade() -> None:
    """Remove the JAI-022 profile."""
    op.drop_table("user_preferences")
