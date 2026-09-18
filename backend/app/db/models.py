"""
SQLAlchemy ORM Models — All 8 Monorepo Tables (Dev 1 + Dev 2)
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Ownership division:
- Dev 2: Patient, Session, ConsentAudit, Document, ExtractedEntity
- Dev 1: InterviewTranscript, ClinicalSummary, RedFlagEventModel
"""

import uuid
from datetime import UTC, datetime
from typing import Any, Dict, List

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# ==============================================================================
# DEV 2 MODELS (Identity, Consent, Documents & Data Track)
# ==============================================================================

class Patient(Base):
    """
    Patient master record verified via ABHA / Aadhaar.
    """
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    abha_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    abha_number: Mapped[str | None] = mapped_column(String(24), nullable=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    gender: Mapped[str] = mapped_column(String(8), nullable=False)  # 'M', 'F', 'O'
    dob: Mapped[str] = mapped_column(String(16), nullable=False)  # 'YYYY-MM-DD'
    mobile: Mapped[str | None] = mapped_column(String(16), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    district: Mapped[str | None] = mapped_column(String(64), nullable=True)
    state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )


class Session(Base):
    """
    Kiosk encounter session lifecycle and audit.
    """
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("patients.id"), nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="hi", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)  # active, completed, wiped
    is_caregiver: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_sessions_patient_status", "patient_id", "status"),
    )


class ConsentAudit(Base):
    """
    Granular audit log of patient consent agreements.
    """
    __tablename__ = "consent_audit"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    patient_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    consent_type: Mapped[str] = mapped_column(String(64), nullable=False)  # abha_data_pull, voice_recording
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )


class Document(Base):
    """
    Scanned medical records captured by kiosk camera or uploaded.
    """
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str | None] = mapped_column(String(32), nullable=True)  # prescription, lab, discharge
    page_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="uploaded", nullable=False)  # uploaded, extracted
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )


class ExtractedEntityModel(Base):
    """
    Structured clinical entities parsed by Module B document OCR pipeline.
    """
    __tablename__ = "extracted_entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    session_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)  # medication, diagnosis, lab_value
    value: Mapped[str] = mapped_column(Text, nullable=False)
    generic_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    date: Mapped[str | None] = mapped_column(String(16), nullable=True)
    bounding_box: Mapped[List[float] | None] = mapped_column(JSON, nullable=True)  # [x, y, w, h] (0-1)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reference_range: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_abnormal: Mapped[bool | None] = mapped_column(Boolean, nullable=True)


# ==============================================================================
# DEV 1 MODELS (Conversation & Intelligence Track)
# ==============================================================================

class InterviewTranscript(Base):
    """
    Chronological turn-by-turn speech and text transcript between patient and kiosk.
    """
    __tablename__ = "interview_transcripts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    turn_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    question_id: Mapped[str] = mapped_column(String(64), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    speaker: Mapped[str] = mapped_column(String(16), default="patient", nullable=False)
    text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    verbatim_voice: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="hi", nullable=False)
    node_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )

    __table_args__ = (
        Index("idx_transcripts_session_turn", "session_id", "turn_number"),
    )


class ClinicalSummary(Base):
    """
    Structured clinical summary generated from interview transcript and scanned documents.
    """
    __tablename__ = "summaries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    chief_complaint: Mapped[str | None] = mapped_column(Text, nullable=True)
    hpi_json: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    pmh_json: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    medications_json: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    allergies_json: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    family_personal_json: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    ros_json: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    fields_json: Mapped[List[Dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    doctor_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False
    )


class RedFlagEventModel(Base):
    """
    Safety danger alert triggered during interview.
    """
    __tablename__ = "red_flag_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    trigger_phrase: Mapped[str] = mapped_column(String(255), nullable=False)
    matched_rule: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)  # 'red' or 'amber'
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )
    dismissed_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dismiss_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class FHIRPushQueue(Base):
    """
    Queue for failed or retryable ABDM FHIR bundle pushes.
    """
    __tablename__ = "fhir_push_queue"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    bundle_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)  # pending, failed, pushed
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False
    )
