"""merge dev1 and dev2 migrations

Revision ID: af48eaaf9194
Revises: 002_consent_audit_v2, aac449da0deb
Create Date: 2026-09-18 21:34:31.548116

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'af48eaaf9194'
down_revision: Union[str, None] = ('002_consent_audit_v2', 'aac449da0deb')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('extracted_entities', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now())
        )


def downgrade() -> None:
    with op.batch_alter_table('extracted_entities', schema=None) as batch_op:
        batch_op.drop_column('created_at')

