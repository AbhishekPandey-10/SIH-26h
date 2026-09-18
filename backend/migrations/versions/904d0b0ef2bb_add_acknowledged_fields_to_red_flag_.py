"""add acknowledged fields to red_flag_events

Revision ID: 904d0b0ef2bb
Revises: af48eaaf9194
Create Date: 2026-09-18 22:33:20.873937

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '904d0b0ef2bb'
down_revision: Union[str, None] = 'af48eaaf9194'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('red_flag_events', schema=None) as batch_op:
        batch_op.add_column(sa.Column('acknowledged_by', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('action_taken', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('is_acknowledged', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table('red_flag_events', schema=None) as batch_op:
        batch_op.drop_column('is_acknowledged')
        batch_op.drop_column('action_taken')
        batch_op.drop_column('acknowledged_by')

