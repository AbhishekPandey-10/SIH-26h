"""002_consent_audit_v2

Revision ID: 002_consent_audit_v2
Revises: 001_initial_schema
Create Date: 2026-09-18 12:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_consent_audit_v2'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('consent_audit', schema=None) as batch_op:
        # Add action column with server_default for existing rows
        batch_op.add_column(sa.Column('action', sa.String(length=50), nullable=False, server_default='share_doctor'))
        # Add voice_confirmation_ref column
        batch_op.add_column(sa.Column('voice_confirmation_ref', sa.Text(), nullable=True))
        # Drop legacy consent_type column so NOT NULL is removed
        batch_op.drop_column('consent_type')
        # Create foreign key to sessions(id)
        batch_op.create_foreign_key('fk_consent_audit_session_id', 'sessions', ['session_id'], ['id'])


def downgrade() -> None:
    with op.batch_alter_table('consent_audit', schema=None) as batch_op:
        batch_op.drop_constraint('fk_consent_audit_session_id', type_='foreignkey')
        batch_op.add_column(sa.Column('consent_type', sa.String(length=64), nullable=True))
        batch_op.drop_column('voice_confirmation_ref')
        batch_op.drop_column('action')
