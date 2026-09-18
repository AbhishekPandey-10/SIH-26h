"""001_initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-18 11:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. patients (Dev 2)
    op.create_table(
        'patients',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('abha_id', sa.String(length=64), nullable=False),
        sa.Column('abha_number', sa.String(length=24), nullable=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('gender', sa.String(length=8), nullable=False),
        sa.Column('dob', sa.String(length=16), nullable=False),
        sa.Column('mobile', sa.String(length=16), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('district', sa.String(length=64), nullable=True),
        sa.Column('state', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_patients_abha_id', 'patients', ['abha_id'], unique=True)

    # 2. sessions (Dev 2)
    op.create_table(
        'sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('patient_id', sa.String(length=36), nullable=True),
        sa.Column('language', sa.String(length=8), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('is_caregiver', sa.Boolean(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_sessions_patient_status', 'sessions', ['patient_id', 'status'])

    # 3. consent_audit (Dev 2)
    op.create_table(
        'consent_audit',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('patient_id', sa.String(length=36), nullable=True),
        sa.Column('consent_type', sa.String(length=64), nullable=False),
        sa.Column('granted', sa.Boolean(), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_consent_audit_session_id', 'consent_audit', ['session_id'])

    # 4. documents (Dev 2)
    op.create_table(
        'documents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=False),
        sa.Column('file_type', sa.String(length=32), nullable=True),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_documents_session_id', 'documents', ['session_id'])

    # 5. extracted_entities (Dev 2)
    op.create_table(
        'extracted_entities',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('entity_type', sa.String(length=32), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('generic_name', sa.String(length=128), nullable=True),
        sa.Column('date', sa.String(length=16), nullable=True),
        sa.Column('bounding_box', sa.JSON(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(length=32), nullable=True),
        sa.Column('reference_range', sa.String(length=64), nullable=True),
        sa.Column('is_abnormal', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_extracted_entities_document_id', 'extracted_entities', ['document_id'])
    op.create_index('ix_extracted_entities_session_id', 'extracted_entities', ['session_id'])

    # 6. interview_transcripts (Dev 1)
    op.create_table(
        'interview_transcripts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('turn_number', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.String(length=64), nullable=False),
        sa.Column('speaker', sa.String(length=16), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('verbatim_voice', sa.Text(), nullable=True),
        sa.Column('audio_url', sa.Text(), nullable=True),
        sa.Column('language', sa.String(length=8), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_transcripts_session_turn', 'interview_transcripts', ['session_id', 'turn_number'])

    # 7. summaries (Dev 1)
    op.create_table(
        'summaries',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('chief_complaint', sa.Text(), nullable=True),
        sa.Column('hpi_json', sa.JSON(), nullable=True),
        sa.Column('pmh_json', sa.JSON(), nullable=True),
        sa.Column('medications_json', sa.JSON(), nullable=True),
        sa.Column('allergies_json', sa.JSON(), nullable=True),
        sa.Column('family_personal_json', sa.JSON(), nullable=True),
        sa.Column('ros_json', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('doctor_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_summaries_session_id', 'summaries', ['session_id'])

    # 8. red_flag_events (Dev 1)
    op.create_table(
        'red_flag_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('trigger_phrase', sa.String(length=255), nullable=False),
        sa.Column('matched_rule', sa.String(length=255), nullable=False),
        sa.Column('severity', sa.String(length=16), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('dismissed_by', sa.String(length=64), nullable=True),
        sa.Column('dismiss_reason', sa.Text(), nullable=True),
        sa.Column('is_dismissed', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_red_flag_events_session_id', 'red_flag_events', ['session_id'])


def downgrade() -> None:
    op.drop_table('red_flag_events')
    op.drop_table('summaries')
    op.drop_table('interview_transcripts')
    op.drop_table('extracted_entities')
    op.drop_table('documents')
    op.drop_table('consent_audit')
    op.drop_table('sessions')
    op.drop_table('patients')
