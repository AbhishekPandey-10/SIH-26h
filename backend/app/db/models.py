"""
SQLAlchemy ORM Models — Dev 1 Tables Only
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Dev 1 owns:
- interview_transcripts
- summaries
- red_flag_events

Note: Dev 2 owns patients, sessions, consent_audit, documents, extracted_entities.
Foreign keys reference session_id as string/UUID without cross-ownership constraint hardlocks.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class InterviewTranscript(Base):
    """
    Chronological turn-by-turn speech and text transcript between patient and kiosk.
    """
    __tablename__ = "interview_transcripts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    turn_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    question_id: Mapped[str] = mapped_column(String(64), nullable=False)
    speaker: Mapped[str] = mapped_column(String(16), nullable=False)  # 'kiosk' or 'patient'
    text: Mapped[str] = mapped_column(Text, nullable=False)
    verbatim_voice: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="hi", nullable=False)
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
    hpi_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    pmh_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    medications_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    allergies_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    family_personal_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    ros_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)  # draft, confirmed, pushed
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
