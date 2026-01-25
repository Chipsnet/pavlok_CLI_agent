"""remove date from daily_punishments

Revision ID: b6f5db559e23
Revises: 20260112_v02
Create Date: 2026-01-25 16:31:06.215291

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6f5db559e23'
down_revision: Union[str, Sequence[str], None] = '20260112_v02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('daily_punishments', schema=None) as batch_op:
        batch_op.drop_column('date')


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('daily_punishments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('date', sa.Date(), nullable=False))
        batch_op.create_unique_constraint('uq_daily_punishments_date', ['date'])
