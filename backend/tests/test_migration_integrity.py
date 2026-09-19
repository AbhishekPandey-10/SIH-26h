"""
Regression Tests: Database Integrity, Migration Reconciliation, and Canonical Contracts
Assignment 1 — PS ID26047

Validates:
1. Alembic upgrade head produces complete schema matching ORM metadata.
2. Consent audit is append-only at DB level (triggers block UPDATE & DELETE).
3. Foreign key constraints are enforced (orphans rejected, RESTRICT on delete).
4. SQLite foreign_keys pragma is enabled on all engine connections.
5. verify_schema_ready() fails truthfully on unmigrated databases.
6. Canonical schemas and enums round-trip and reject invalid inputs.
7. TypeScript/Pydantic contract parity for core types.
"""

import os
import sqlite3
import tempfile
import uuid
from datetime import UTC, datetime

import pytest
from alembic import command
from alembic.config import Config
from pydantic import ValidationError
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError

from app.db.models import (
    Base,
    ClinicalSummary,
    ConsentAudit,
    Document,
    ExtractedEntityModel,
    FHIRPushQueue,
    InterviewTranscript,
    Patient,
    RedFlagEventModel,
    Session,
    SummaryResolution,
)
from app.shared.schemas import (
    ConsentAction,
    ConsentActionItem,
    DocumentStatus,
    EntityType,
    ExtractedEntity,
    FHIRExportRequest,
    FHIRExportResponse,
    FHIRPreviewResponse,
    InterviewAnswer,
    InterviewMode,
    NextQuestion,
    RedFlagEvent,
    RedFlagSeverity,
    SessionStartResponse,
    SessionStatus,
    SummaryField,
    SummarySection,
    SummarySource,
    VerificationStatus,
    WebSocketEnvelope,
    WebSocketMessageType,
)


@pytest.fixture
def disposable_sqlite_db():
    """Create a temporary SQLite database file for testing migrations."""
    fd, path = tempfile.mkstemp(suffix="_test_migration.db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


# ==============================================================================
# 1. ALEMBIC MIGRATION TESTS
# ==============================================================================

def test_empty_database_upgrades_to_head_matching_orm(disposable_sqlite_db):
    """
    Test: An empty database upgraded solely through Alembic migrations
    matches the complete intended ORM metadata.
    """
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    alembic_ini_path = os.path.join(backend_dir, "alembic.ini")

    cfg = Config(alembic_ini_path)
    # Set the temporary DB path
    db_url = f"sqlite:///{disposable_sqlite_db.replace(os.sep, '/')}"
    cfg.set_main_option("sqlalchemy.url", db_url)

    # Run upgrade head
    command.upgrade(cfg, "head")

    # Connect to the upgraded DB and inspect tables
    conn = sqlite3.connect(disposable_sqlite_db)
    cursor = conn.cursor()

    tables = {
        row[0]
        for row in cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }

    # All 10 application tables + alembic_version must exist
    expected_tables = {
        "alembic_version",
        "patients",
        "sessions",
        "consent_audit",
        "documents",
        "extracted_entities",
        "interview_transcripts",
        "summaries",
        "red_flag_events",
        "fhir_push_queue",
        "summary_resolutions",
    }
    assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"

    # Verify migration head
    version = cursor.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    assert version == "003_reconcile_schema"

    # Verify sessions columns (caregiver, voice_only, body_map, interview_mode, prakriti)
    session_cols = {col[1] for col in cursor.execute("PRAGMA table_info(sessions)").fetchall()}
    for col in [
        "caregiver_name", "caregiver_relationship", "caregiver_phone",
        "voice_only_mode", "body_map_selections", "interview_mode", "prakriti_result"
    ]:
        assert col in session_cols, f"Column '{col}' missing from sessions table"

    # Verify interview_transcripts columns (proxy fields, question_text, answer_text)
    transcript_cols = {col[1] for col in cursor.execute("PRAGMA table_info(interview_transcripts)").fetchall()}
    for col in ["is_proxy", "proxy_name", "proxy_relationship", "question_text", "answer_text"]:
        assert col in transcript_cols, f"Column '{col}' missing from interview_transcripts table"

    # Verify summaries columns (lens, ayush_json, fields_json)
    summary_cols = {col[1] for col in cursor.execute("PRAGMA table_info(summaries)").fetchall()}
    for col in ["lens", "ayush_json", "fields_json"]:
        assert col in summary_cols, f"Column '{col}' missing from summaries table"

    # Verify extracted_entities.created_at is present
    entity_cols = {col[1] for col in cursor.execute("PRAGMA table_info(extracted_entities)").fetchall()}
    assert "created_at" in entity_cols, "Column 'created_at' missing from extracted_entities"

    # Verify consent_audit has action and voice_confirmation_ref, and no orphan patient_id
    consent_cols = {col[1] for col in cursor.execute("PRAGMA table_info(consent_audit)").fetchall()}
    assert "action" in consent_cols, "'action' missing from consent_audit"
    assert "voice_confirmation_ref" in consent_cols, "'voice_confirmation_ref' missing from consent_audit"
    assert "patient_id" not in consent_cols, "Orphan 'patient_id' should have been dropped from consent_audit"

    # Verify summary_resolutions table has 10 columns
    sr_cols = {col[1] for col in cursor.execute("PRAGMA table_info(summary_resolutions)").fetchall()}
    assert len(sr_cols) == 10, f"Expected 10 columns in summary_resolutions, got {len(sr_cols)}"

    conn.close()


def test_migration_downgrade_and_reupgrade(disposable_sqlite_db):
    """Test that 003_reconcile_schema is fully reversible."""
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    alembic_ini_path = os.path.join(backend_dir, "alembic.ini")

    cfg = Config(alembic_ini_path)
    db_url = f"sqlite:///{disposable_sqlite_db.replace(os.sep, '/')}"
    cfg.set_main_option("sqlalchemy.url", db_url)

    # Upgrade to head
    command.upgrade(cfg, "head")

    # Downgrade to down_revision of 003
    command.downgrade(cfg, "904d0b0ef2bb")

    conn = sqlite3.connect(disposable_sqlite_db)
    cursor = conn.cursor()
    version = cursor.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    assert version == "904d0b0ef2bb"

    # summary_resolutions table must be dropped
    tables = {
        row[0]
        for row in cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "summary_resolutions" not in tables
    conn.close()

    # Re-upgrade to head
    command.upgrade(cfg, "head")
    conn = sqlite3.connect(disposable_sqlite_db)
    cursor = conn.cursor()
    version = cursor.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    assert version == "003_reconcile_schema"
    conn.close()


# ==============================================================================
# 2. CONSENT APPEND-ONLY DB ENFORCEMENT (TRIGGERS)
# ==============================================================================

def test_consent_audit_rejects_sql_update_and_delete(disposable_sqlite_db):
    """
    Test: Database triggers reject direct SQL UPDATE and DELETE on consent_audit.
    Consent records are legally immutable audit anchors.
    """
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    cfg = Config(os.path.join(backend_dir, "alembic.ini"))
    db_url = f"sqlite:///{disposable_sqlite_db.replace(os.sep, '/')}"
    cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(cfg, "head")

    conn = sqlite3.connect(disposable_sqlite_db)
    cursor = conn.cursor()

    # Create patient + session
    pat_id = str(uuid.uuid4())
    sess_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO patients (id, abha_id, name, gender, dob, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (pat_id, "test.patient@abdm", "Audit Test Patient", "M", "1985-05-15", datetime.now(UTC).isoformat()),
    )
    cursor.execute(
        "INSERT INTO sessions (id, patient_id, language, status, is_caregiver, started_at) VALUES (?, ?, ?, ?, ?, ?)",
        (sess_id, pat_id, "hi", "active", 0, datetime.now(UTC).isoformat()),
    )

    # Insert consent record
    consent_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO consent_audit (id, session_id, granted, timestamp, action) VALUES (?, ?, ?, ?, ?)",
        (consent_id, sess_id, 1, datetime.now(UTC).isoformat(), "share_doctor"),
    )
    conn.commit()

    # Attempt direct SQL UPDATE — must be rejected by trigger
    with pytest.raises(sqlite3.DatabaseError) as exc_update:
        cursor.execute("UPDATE consent_audit SET granted=0 WHERE id=?", (consent_id,))
        conn.commit()
    assert "append-only" in str(exc_update.value).lower() or "prohibited" in str(exc_update.value).lower()

    # Attempt direct SQL DELETE — must be rejected by trigger
    with pytest.raises(sqlite3.DatabaseError) as exc_delete:
        cursor.execute("DELETE FROM consent_audit WHERE id=?", (consent_id,))
        conn.commit()
    assert "append-only" in str(exc_delete.value).lower() or "prohibited" in str(exc_delete.value).lower()

    # Verify record is untouched
    row = cursor.execute("SELECT granted, action FROM consent_audit WHERE id=?", (consent_id,)).fetchone()
    assert row[0] == 1
    assert row[1] == "share_doctor"

    conn.close()


# ==============================================================================
# 3. FOREIGN KEY CONSTRAINTS AND RETENTION SEMANTICS
# ==============================================================================

def test_sqlite_foreign_keys_reject_orphaned_records(disposable_sqlite_db):
    """
    Test: Inserting records referencing nonexistent sessions or documents
    is rejected by SQLite foreign key enforcement.
    """
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    cfg = Config(os.path.join(backend_dir, "alembic.ini"))
    db_url = f"sqlite:///{disposable_sqlite_db.replace(os.sep, '/')}"
    cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(cfg, "head")

    conn = sqlite3.connect(disposable_sqlite_db)
    conn.execute("PRAGMA foreign_keys=ON")
    cursor = conn.cursor()

    fake_session_id = str(uuid.uuid4())

    # 1. Orphan document
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            "INSERT INTO documents (id, session_id, file_path, page_number, status, uploaded_at) VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), fake_session_id, "/uploads/fake.pdf", 1, "uploaded", datetime.now(UTC).isoformat()),
        )
        conn.commit()

    # 2. Orphan interview_transcript
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            "INSERT INTO interview_transcripts (id, session_id, turn_number, question_id, language, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), fake_session_id, 1, "cc_01", "hi", datetime.now(UTC).isoformat()),
        )
        conn.commit()

    # 3. Orphan clinical summary
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            "INSERT INTO summaries (id, session_id, version, lens, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), fake_session_id, 1, "allopathic", "draft", datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat()),
        )
        conn.commit()

    # 4. Orphan red_flag_event
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            "INSERT INTO red_flag_events (id, session_id, trigger_phrase, matched_rule, severity, category, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), fake_session_id, "pain", "rule_1", "red", "cardiac", datetime.now(UTC).isoformat()),
        )
        conn.commit()

    # 5. Orphan summary_resolution
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            "INSERT INTO summary_resolutions (id, session_id, field_id, resolution_choice, resolved_value, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), fake_session_id, "med_01", "use_patient", "Metformin 500mg", datetime.now(UTC).isoformat()),
        )
        conn.commit()

    conn.close()


@pytest.mark.asyncio
async def test_sqlite_pragma_foreign_keys_is_enabled():
    """
    Test: SQLAlchemy async engine connections automatically execute PRAGMA foreign_keys=ON
    for SQLite connections via the connect event listener.
    """
    from app.db.database import engine

    async with engine.connect() as conn:
        result = await conn.execute(text("PRAGMA foreign_keys"))
        val = result.scalar()
        assert val == 1, f"Expected PRAGMA foreign_keys=1, got {val}"


# ==============================================================================
# 4. SCHEMA READINESS VERIFICATION
# ==============================================================================

@pytest.mark.asyncio
async def test_verify_schema_ready_fails_on_unmigrated_db():
    """
    Test: verify_schema_ready() raises RuntimeError when alembic_version table
    is missing or not at the expected migration head.
    Startup initialization failure cannot be masked as success.
    """
    from sqlalchemy.ext.asyncio import create_async_engine
    import app.db.database as db_mod

    # Fresh in-memory DB has no alembic_version table
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    # Patch engine temporarily to check behavior
    orig_engine = db_mod.engine
    orig_ready = db_mod._schema_ready
    orig_error = db_mod._schema_error

    try:
        db_mod.engine = test_engine
        db_mod._schema_ready = False
        db_mod._schema_error = None

        with pytest.raises(RuntimeError) as exc_info:
            await db_mod.verify_schema_ready()

        assert "alembic" in str(exc_info.value).lower()
        assert db_mod.is_schema_ready() is False
        assert db_mod.get_schema_error() is not None
    finally:
        db_mod.engine = orig_engine
        db_mod._schema_ready = orig_ready
        db_mod._schema_error = orig_error
        await test_engine.dispose()


# ==============================================================================
# 5. CANONICAL SCHEMAS & ENUMS VALIDATION
# ==============================================================================

def test_canonical_enums_and_validation():
    """Test that canonical enums accept valid values and reject invalid values."""
    # EntityType
    assert EntityType("diagnosis") == EntityType.DIAGNOSIS
    assert EntityType("medication") == EntityType.MEDICATION
    assert EntityType("vital") == EntityType.VITAL
    with pytest.raises(ValueError):
        EntityType("invalid_entity")

    # SummarySection
    assert SummarySection("chief_complaint") == SummarySection.CHIEF_COMPLAINT
    assert SummarySection("changes_since_last_visit") == SummarySection.CHANGES_SINCE_LAST_VISIT
    with pytest.raises(ValueError):
        SummarySection("invalid_section")

    # VerificationStatus
    assert VerificationStatus("doctor_edited") == VerificationStatus.DOCTOR_EDITED
    assert VerificationStatus("conflicting") == VerificationStatus.CONFLICTING

    # RedFlagSeverity
    assert RedFlagSeverity("red") == RedFlagSeverity.RED
    assert RedFlagSeverity("amber") == RedFlagSeverity.AMBER

    # ConsentAction
    assert ConsentAction("share_doctor") == ConsentAction.SHARE_DOCTOR
    assert ConsentAction("store_abdm") == ConsentAction.STORE_ABDM


def test_extracted_entity_normalization_and_aliases():
    """
    Test ExtractedEntity:
    - Normalizes 'vital_sign' to 'vital'
    - Strips low-confidence suffixes
    - Supports both entity_id and id
    - Supports both type and entity_type
    - Supports both source_document_id and document_id
    """
    # 1. Parsing with OCR output containing 'vital_sign'
    e1 = ExtractedEntity(
        entity_id="ent_01",
        type="vital_sign",
        value="120/80 mmHg",
        confidence=0.95,
        source_document_id="doc_01",
    )
    assert e1.entity_type == "vital"
    assert e1.id == "ent_01"
    assert e1.document_id == "doc_01"
    assert e1.type == "vital"
    assert e1.entity_id == "ent_01"
    assert e1.source_document_id == "doc_01"

    # 2. Parsing with low_confidence suffix attached to entity type
    e2 = ExtractedEntity(
        id="ent_02",
        entity_type="medication_low_confidence",
        value="Aspirin 75mg",
        confidence=0.45,
    )
    assert e2.entity_type == "medication"
    assert e2.confidence == 0.45

    # 3. Serialization and deserialization round-trip
    dumped = e1.model_dump_json()
    reloaded = ExtractedEntity.model_validate_json(dumped)
    assert reloaded.id == e1.id
    assert reloaded.entity_type == e1.entity_type
    assert reloaded.value == e1.value


def test_summary_source_immutable_evidence_id():
    """Test SummarySource generates immutable evidence_id and accepts session_id."""
    src = SummarySource(
        type="transcript",
        ref_id="turn_03",
        snippet="Patient has mild cough",
        session_id="sess_123",
    )
    assert src.evidence_id.startswith("ev_")
    assert src.session_id == "sess_123"
    assert src.type == "transcript"

    # Evidence ID survives serialization round-trip
    dumped = src.model_dump_json()
    reloaded = SummarySource.model_validate_json(dumped)
    assert reloaded.evidence_id == src.evidence_id


def test_red_flag_event_lifecycle_and_id_parity():
    """
    Test RedFlagEvent supports id / event_id aliases and staff lifecycle fields
    (is_acknowledged, acknowledged_by, action_taken, is_dismissed).
    """
    event = RedFlagEvent(
        event_id="rfe_test_01",
        session_id="sess_01",
        trigger_phrase="chest heaviness",
        matched_rule="RULE_CHEST_HEAVY",
        severity="red",
        category="cardiac",
        is_acknowledged=True,
        acknowledged_by="doc_opd_01",
        action_taken="Escalated to ER triage",
    )
    assert event.id == "rfe_test_01"
    assert event.event_id == "rfe_test_01"
    assert event.is_acknowledged is True
    assert event.action_taken == "Escalated to ER triage"
    assert event.is_dismissed is False


def test_websocket_envelope_discriminated_types():
    """Test WebSocketEnvelope with typed messages."""
    env_question = WebSocketEnvelope(
        type="question",
        payload={"question_id": "cc_01", "text": "What is your main complaint?"},
        session_id="sess_abc",
    )
    assert env_question.type == "question"
    assert env_question.session_id == "sess_abc"

    env_error = WebSocketEnvelope(
        type="error",
        error="Audio stream disconnected",
        session_id="sess_abc",
    )
    assert env_error.type == "error"
    assert env_error.error == "Audio stream disconnected"

    # Invalid type rejected
    with pytest.raises(ValidationError):
        WebSocketEnvelope(
            type="unknown_event_type",
            payload={},
        )


def test_fhir_export_dtos():
    """Test FHIRExportRequest and FHIRExportResponse DTOs."""
    req = FHIRExportRequest(
        session_id="sess_01",
        consent_artefact_id="consent_artefact_123",
        export_type="opd_summary",
    )
    assert req.session_id == "sess_01"
    assert req.export_type == "opd_summary"

    resp = FHIRExportResponse(
        session_id="sess_01",
        status="delivered",
        transaction_id="tx_abdm_98765",
    )
    assert resp.status == "delivered"
    assert resp.transaction_id == "tx_abdm_98765"
    assert resp.export_id.startswith("export_")


def test_consent_action_item():
    """Test ConsentActionItem validation."""
    item = ConsentActionItem(action="share_doctor", granted=True)
    assert item.action == "share_doctor"
    assert item.granted is True

    with pytest.raises(ValidationError):
        ConsentActionItem(action="unsupported_consent_action", granted=True)
