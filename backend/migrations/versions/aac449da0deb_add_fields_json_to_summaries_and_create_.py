"""add fields_json to summaries and create fhir_push_queue

Revision ID: aac449da0deb
Revises: bc12419f052b
Create Date: 2026-09-18 15:38:40.690822

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aac449da0deb'
down_revision: Union[str, None] = 'bc12419f052b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('fhir_push_queue',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('bundle_json', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_fhir_push_queue_session_id', 'fhir_push_queue', ['session_id'], unique=False)
    op.add_column('summaries', sa.Column('fields_json', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('summaries', 'fields_json')
    op.drop_index('ix_fhir_push_queue_session_id', table_name='fhir_push_queue')
    op.drop_table('fhir_push_queue')
