"""add question_text answer_text node_name to interview_transcripts

Revision ID: bc12419f052b
Revises: 001_initial_schema
Create Date: 2026-09-18 12:31:06.257015

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc12419f052b'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('interview_transcripts', sa.Column('question_text', sa.Text(), nullable=False, server_default=''))
    op.add_column('interview_transcripts', sa.Column('answer_text', sa.Text(), nullable=True))
    op.add_column('interview_transcripts', sa.Column('node_name', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('interview_transcripts', 'node_name')
    op.drop_column('interview_transcripts', 'answer_text')
    op.drop_column('interview_transcripts', 'question_text')
