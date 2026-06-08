"""Add phase 3 features

Revision ID: 0002_phase3_features
Revises: 0001_initial
Create Date: 2026-05-18

"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002_phase3_features"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add new columns to events
    op.add_column("events", sa.Column("sector", sa.String(100), nullable=True))
    op.add_column("events", sa.Column("risk_type", sa.String(100), nullable=True))
    op.add_column("events", sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("events", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))

    op.create_index("ix_events_sector", "events", ["sector"])
    op.create_index("ix_events_risk_type", "events", ["risk_type"])

    # Add new columns to outlooks
    op.add_column("outlooks", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("outlooks", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("outlooks", sa.Column("reviewer_notes", sa.Text(), nullable=True))

    op.create_index("ix_outlooks_status", "outlooks", ["status"])

    # Add new columns to scenarios
    op.add_column("scenarios", sa.Column("is_template", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("scenarios", sa.Column("template_id", sa.Integer(), sa.ForeignKey("scenarios.id"), nullable=True))

    # Create ask_anything_queries table
    op.create_table(
        "ask_anything_queries",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("sources_cited", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("analysts.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("ask_anything_queries")

    op.drop_column("scenarios", "template_id")
    op.drop_column("scenarios", "is_template")

    op.drop_index("ix_outlooks_status", table_name="outlooks")
    op.drop_column("outlooks", "reviewer_notes")
    op.drop_column("outlooks", "published_at")
    op.drop_column("outlooks", "reviewed_at")

    op.drop_index("ix_events_risk_type", table_name="events")
    op.drop_index("ix_events_sector", table_name="events")
    op.drop_column("events", "published_at")
    op.drop_column("events", "is_published")
    op.drop_column("events", "risk_type")
    op.drop_column("events", "sector")

