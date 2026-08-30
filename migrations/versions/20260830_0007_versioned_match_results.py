"""Add versioned hard-filter and rule-score results.

Revision ID: 0007_versioned_match_results
Revises: 0006_single_user_preferences
Create Date: 2026-08-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_versioned_match_results"
down_revision: str | None = "0006_single_user_preferences"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create append-only matching results with one current row per position."""
    op.create_table(
        "match_results",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("position_id", sa.BigInteger(), nullable=False),
        sa.Column("preference_id", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("score_version", sa.String(length=100), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("preference_hash", sa.String(length=64), nullable=False),
        sa.Column("result_hash", sa.String(length=64), nullable=False),
        sa.Column("hard_filter_passed", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column(
            "components",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "matched_rules",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("preference_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("supersedes_id", sa.BigInteger(), nullable=True),
        sa.CheckConstraint(
            "hard_filter_passed OR score = 0",
            name=op.f("ck_match_results_filtered_score_zero"),
        ),
        sa.CheckConstraint(
            "input_hash ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_match_results_input_hash_sha256"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(components) = 'array'",
            name=op.f("ck_match_results_components_array"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(matched_rules) = 'array'",
            name=op.f("ck_match_results_matched_rules_array"),
        ),
        sa.CheckConstraint(
            "preference_hash ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_match_results_preference_hash_sha256"),
        ),
        sa.CheckConstraint(
            "result_hash ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_match_results_result_hash_sha256"),
        ),
        sa.CheckConstraint(
            "score >= 0 AND score <= 100",
            name=op.f("ck_match_results_score_range"),
        ),
        sa.CheckConstraint(
            "length(score_version) > 0",
            name=op.f("ck_match_results_score_version_present"),
        ),
        sa.CheckConstraint(
            "supersedes_id IS NULL OR supersedes_id <> id",
            name=op.f("ck_match_results_supersedes_other_result"),
        ),
        sa.ForeignKeyConstraint(
            ["position_id"],
            ["job_positions.id"],
            name=op.f("fk_match_results_position_id_job_positions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["preference_id"],
            ["user_preferences.id"],
            name=op.f("fk_match_results_preference_id_user_preferences"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_id"],
            ["match_results.id"],
            name=op.f("fk_match_results_supersedes_id_match_results"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_match_results")),
        sa.UniqueConstraint(
            "position_id",
            "score_version",
            "input_hash",
            "preference_hash",
            "preference_updated_at",
            name=op.f("uq_match_results_calculation"),
        ),
    )
    op.create_index(
        "ix_match_results_current_score",
        "match_results",
        ["is_current", "score"],
        unique=False,
    )
    op.create_index(
        "ix_match_results_score_version",
        "match_results",
        ["score_version"],
        unique=False,
    )
    op.create_index(
        "uq_match_results_position_current",
        "match_results",
        ["position_id"],
        unique=True,
        postgresql_where=sa.text("is_current"),
    )


def downgrade() -> None:
    """Remove versioned matching results."""
    op.drop_index(
        "uq_match_results_position_current",
        table_name="match_results",
        postgresql_where=sa.text("is_current"),
    )
    op.drop_index("ix_match_results_score_version", table_name="match_results")
    op.drop_index("ix_match_results_current_score", table_name="match_results")
    op.drop_table("match_results")
