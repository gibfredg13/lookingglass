"""Initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-18

"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysts",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="analyst"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
    )

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("region", sa.String(100), nullable=False),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("theme", sa.String(100), nullable=False),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("fingerprint", sa.String(32), nullable=False, index=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("analysts.id"), nullable=True),
    )
    op.create_index("ix_events_fingerprint_owner", "events", ["fingerprint", "owner_id"])

    op.create_table(
        "event_timeline_entries",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("url", sa.String(500), nullable=True),
        sa.Column("reliability", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id"), nullable=False),
    )

    op.create_table(
        "event_tags",
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id"), primary_key=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tags.id"), primary_key=True),
    )

    op.create_table(
        "outlooks",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("horizon_hours", sa.Integer(), nullable=False),
        sa.Column("expected_developments", sa.Text(), nullable=False),
        sa.Column("key_indicators", sa.Text(), nullable=False),
        sa.Column("implications", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("analysts.id"), nullable=True),
    )

    op.create_table(
        "scenarios",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("case_type", sa.String(20), nullable=False),
        sa.Column("triggers", sa.Text(), nullable=False),
        sa.Column("impacts", sa.Text(), nullable=False),
        sa.Column("time_horizon_hours", sa.Integer(), nullable=False),
        sa.Column("probability", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("analysts.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("scenarios")
    op.drop_table("outlooks")
    op.drop_table("event_tags")
    op.drop_table("sources")
    op.drop_table("event_timeline_entries")
    op.drop_index("ix_events_fingerprint_owner", table_name="events")
    op.drop_table("events")
    op.drop_table("tags")
    op.drop_table("analysts")

