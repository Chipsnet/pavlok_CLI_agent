"""Split schedule uniqueness by event type

Allow multiple REMIND schedules per day while keeping PLAN day-level uniqueness.

Revision ID: 20260215_v0.3_schedule_index_split
Revises: 20260214_v0.3_init
Create Date: 2026-02-15 20:05:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260215_v0.3_schedule_index_split"
down_revision: Union[str, Sequence[str], None] = "20260214_v0.3_init"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Old index blocked multiple REMIND entries on the same day.
    op.drop_index("uix_user_date_event", table_name="schedules")

    # Keep PLAN as one-per-user-per-day.
    op.create_index(
        "uix_user_plan_date",
        "schedules",
        ["user_id", sa.text("date(run_at)")],
        unique=True,
        sqlite_where=sa.text("event_type = 'PLAN'"),
    )

    # Add lookup index for worker/query performance.
    op.create_index(
        "ix_schedule_user_event_run_at",
        "schedules",
        ["user_id", "event_type", "run_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_schedule_user_event_run_at", table_name="schedules")
    op.drop_index("uix_user_plan_date", table_name="schedules")

    op.create_index(
        "uix_user_date_event",
        "schedules",
        ["user_id", sa.text("date(run_at)"), "event_type"],
        unique=True,
    )
