"""003_reconcile_schema — Full ORM↔migration reconciliation

Revision ID: 003_reconcile_schema
Revises: 904d0b0ef2bb
Create Date: 2026-09-19 01:30:00.000000

Adds all columns/tables missing from the migration chain so that
`alembic upgrade head` on an empty database matches ORM metadata.
Adds FK constraints, consent append-only triggers, and summary_resolutions table.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_reconcile_schema'
down_revision: Union[str, None] = '904d0b0ef2bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name  # 'sqlite' or 'postgresql'

    # =========================================================================
    # 1. sessions — add missing columns from caregiver/AYUSH features
    # =========================================================================
    with op.batch_alter_table('sessions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('caregiver_name', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('caregiver_relationship', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('caregiver_phone', sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column('voice_only_mode', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('body_map_selections', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('interview_mode', sa.String(length=32), nullable=False, server_default='allopathic'))
        batch_op.add_column(sa.Column('prakriti_result', sa.JSON(), nullable=True))

    # =========================================================================
    # 2. interview_transcripts — add proxy fields, fix language width, add question/answer if missing
    # =========================================================================
    with op.batch_alter_table('interview_transcripts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_proxy', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('proxy_name', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('proxy_relationship', sa.String(length=64), nullable=True))
        # Fix language width: String(8) → String(10) to match ORM
        batch_op.alter_column('language', type_=sa.String(length=10), existing_type=sa.String(length=8))
        # Fix session_id width: String(64) → String(36) to match sessions.id PK width
        batch_op.alter_column('session_id', type_=sa.String(length=36), existing_type=sa.String(length=64))
        # Add FK to sessions
        batch_op.create_foreign_key(
            'fk_interview_transcripts_session_id', 'sessions', ['session_id'], ['id']
        )
        # Add index on session_id to match ORM index=True
        batch_op.create_index('ix_interview_transcripts_session_id', ['session_id'], unique=False)

    # =========================================================================
    # 3. summaries — add lens, ayush_json; fix session_id width; add FK
    # =========================================================================
    with op.batch_alter_table('summaries', schema=None) as batch_op:
        batch_op.add_column(sa.Column('lens', sa.String(length=32), nullable=False, server_default='allopathic'))
        batch_op.add_column(sa.Column('ayush_json', sa.JSON(), nullable=True))
        batch_op.alter_column('session_id', type_=sa.String(length=36), existing_type=sa.String(length=64))
        batch_op.create_foreign_key(
            'fk_summaries_session_id', 'sessions', ['session_id'], ['id']
        )

    # =========================================================================
    # 4. extracted_entities — backfill created_at NOT NULL
    # =========================================================================
    # First backfill any NULL created_at with current timestamp
    op.execute(
        sa.text("UPDATE extracted_entities SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
    )
    with op.batch_alter_table('extracted_entities', schema=None) as batch_op:
        batch_op.alter_column('created_at', nullable=False,
                              existing_type=sa.DateTime(timezone=True),
                              existing_server_default=sa.func.now())
        # Add FKs
        batch_op.create_foreign_key(
            'fk_extracted_entities_session_id', 'sessions', ['session_id'], ['id']
        )
        batch_op.create_foreign_key(
            'fk_extracted_entities_document_id', 'documents', ['document_id'], ['id']
        )

    # =========================================================================
    # 5. documents — add FK to sessions
    # =========================================================================
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'fk_documents_session_id', 'sessions', ['session_id'], ['id']
        )

    # =========================================================================
    # 6. red_flag_events — fix session_id width; add FK
    # =========================================================================
    with op.batch_alter_table('red_flag_events', schema=None) as batch_op:
        batch_op.alter_column('session_id', type_=sa.String(length=36), existing_type=sa.String(length=64))
        batch_op.create_foreign_key(
            'fk_red_flag_events_session_id', 'sessions', ['session_id'], ['id']
        )

    # =========================================================================
    # 7. fhir_push_queue — fix session_id width; add FK
    # =========================================================================
    with op.batch_alter_table('fhir_push_queue', schema=None) as batch_op:
        batch_op.alter_column('session_id', type_=sa.String(length=36), existing_type=sa.String(length=64))
        batch_op.create_foreign_key(
            'fk_fhir_push_queue_session_id', 'sessions', ['session_id'], ['id']
        )

    # =========================================================================
    # 8. consent_audit — drop orphan patient_id column (not in ORM)
    # =========================================================================
    with op.batch_alter_table('consent_audit', schema=None) as batch_op:
        batch_op.drop_column('patient_id')

    # =========================================================================
    # 9. Create summary_resolutions table
    # =========================================================================
    op.create_table('summary_resolutions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('field_id', sa.String(length=64), nullable=False),
        sa.Column('doctor_id', sa.String(length=64), nullable=False, server_default='doc_opd_01'),
        sa.Column('resolution_choice', sa.String(length=32), nullable=False),
        sa.Column('document_value', sa.Text(), nullable=True),
        sa.Column('patient_value', sa.Text(), nullable=True),
        sa.Column('resolved_value', sa.Text(), nullable=False),
        sa.Column('doctor_note', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], name='fk_summary_resolutions_session_id'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_summary_resolutions_session_id', 'summary_resolutions', ['session_id'], unique=False)

    # =========================================================================
    # 10. Consent append-only triggers at the DB level
    # =========================================================================
    if dialect == 'sqlite':
        op.execute(sa.text("""
            CREATE TRIGGER IF NOT EXISTS trg_consent_audit_no_update
            BEFORE UPDATE ON consent_audit
            BEGIN
                SELECT RAISE(ABORT, 'consent_audit is append-only: UPDATE prohibited');
            END;
        """))
        op.execute(sa.text("""
            CREATE TRIGGER IF NOT EXISTS trg_consent_audit_no_delete
            BEFORE DELETE ON consent_audit
            BEGIN
                SELECT RAISE(ABORT, 'consent_audit is append-only: DELETE prohibited');
            END;
        """))
    elif dialect == 'postgresql':
        op.execute(sa.text("""
            CREATE OR REPLACE FUNCTION prevent_consent_audit_modification()
            RETURNS TRIGGER AS $$
            BEGIN
                RAISE EXCEPTION 'consent_audit is append-only: % prohibited', TG_OP;
                RETURN NULL;
            END;
            $$ LANGUAGE plpgsql;
        """))
        op.execute(sa.text("""
            DROP TRIGGER IF EXISTS trg_consent_audit_no_update ON consent_audit;
            CREATE TRIGGER trg_consent_audit_no_update
            BEFORE UPDATE ON consent_audit
            FOR EACH ROW EXECUTE FUNCTION prevent_consent_audit_modification();
        """))
        op.execute(sa.text("""
            DROP TRIGGER IF EXISTS trg_consent_audit_no_delete ON consent_audit;
            CREATE TRIGGER trg_consent_audit_no_delete
            BEFORE DELETE ON consent_audit
            FOR EACH ROW EXECUTE FUNCTION prevent_consent_audit_modification();
        """))


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Remove consent triggers
    if dialect == 'sqlite':
        op.execute(sa.text("DROP TRIGGER IF EXISTS trg_consent_audit_no_update;"))
        op.execute(sa.text("DROP TRIGGER IF EXISTS trg_consent_audit_no_delete;"))
    elif dialect == 'postgresql':
        op.execute(sa.text("DROP TRIGGER IF EXISTS trg_consent_audit_no_update ON consent_audit;"))
        op.execute(sa.text("DROP TRIGGER IF EXISTS trg_consent_audit_no_delete ON consent_audit;"))
        op.execute(sa.text("DROP FUNCTION IF EXISTS prevent_consent_audit_modification();"))

    # Drop summary_resolutions
    op.drop_index('ix_summary_resolutions_session_id', table_name='summary_resolutions')
    op.drop_table('summary_resolutions')

    # Restore consent_audit.patient_id
    with op.batch_alter_table('consent_audit', schema=None) as batch_op:
        batch_op.add_column(sa.Column('patient_id', sa.String(length=36), nullable=True))

    # Remove FKs from fhir_push_queue, red_flag_events
    with op.batch_alter_table('fhir_push_queue', schema=None) as batch_op:
        batch_op.drop_constraint('fk_fhir_push_queue_session_id', type_='foreignkey')
        batch_op.alter_column('session_id', type_=sa.String(length=64), existing_type=sa.String(length=36))

    with op.batch_alter_table('red_flag_events', schema=None) as batch_op:
        batch_op.drop_constraint('fk_red_flag_events_session_id', type_='foreignkey')
        batch_op.alter_column('session_id', type_=sa.String(length=64), existing_type=sa.String(length=36))

    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.drop_constraint('fk_documents_session_id', type_='foreignkey')

    with op.batch_alter_table('extracted_entities', schema=None) as batch_op:
        batch_op.drop_constraint('fk_extracted_entities_document_id', type_='foreignkey')
        batch_op.drop_constraint('fk_extracted_entities_session_id', type_='foreignkey')
        batch_op.alter_column('created_at', nullable=True,
                              existing_type=sa.DateTime(timezone=True))

    with op.batch_alter_table('summaries', schema=None) as batch_op:
        batch_op.drop_constraint('fk_summaries_session_id', type_='foreignkey')
        batch_op.alter_column('session_id', type_=sa.String(length=64), existing_type=sa.String(length=36))
        batch_op.drop_column('ayush_json')
        batch_op.drop_column('lens')

    with op.batch_alter_table('interview_transcripts', schema=None) as batch_op:
        batch_op.drop_index('ix_interview_transcripts_session_id')
        batch_op.drop_constraint('fk_interview_transcripts_session_id', type_='foreignkey')
        batch_op.alter_column('session_id', type_=sa.String(length=64), existing_type=sa.String(length=36))
        batch_op.alter_column('language', type_=sa.String(length=8), existing_type=sa.String(length=10))
        batch_op.drop_column('proxy_relationship')
        batch_op.drop_column('proxy_name')
        batch_op.drop_column('is_proxy')

    with op.batch_alter_table('sessions', schema=None) as batch_op:
        batch_op.drop_column('prakriti_result')
        batch_op.drop_column('interview_mode')
        batch_op.drop_column('body_map_selections')
        batch_op.drop_column('voice_only_mode')
        batch_op.drop_column('caregiver_phone')
        batch_op.drop_column('caregiver_relationship')
        batch_op.drop_column('caregiver_name')
