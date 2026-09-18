"""
MediKiosk Shared Schemas (API Contract)
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

This file defines the strict Pydantic v2 schemas that form the API contract between:
- Dev 1 (Conversation & Intelligence): NextQuestion, InterviewAnswer, SummaryField, RedFlagEvent
- Dev 2 (Documents, Data & Infrastructure): ExtractedEntity (TODO stub), FHIRBundlePayload (TODO stub)
"""

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ==============================================================================
# DEV 1 SCHEMAS (Conversation & Intelligence Track)
# ==============================================================================

class NextQuestion(BaseModel):
    """
    Model for the question emitted by the interview engine to the Kiosk frontend.
    """
    model_config = ConfigDict(from_attributes=True)

    question_id: str = Field(..., description="Unique question identifier, e.g. 'cc_01', 'soc_site'")
    text: str = Field(..., description="Display text of the question in active language")
    audio_url: str | None = Field(None, description="Pre-synthesized TTS audio URL or data URI if available")
    input_type: Literal["voice_touch", "choice", "scale", "yes_no"] = Field(
        default="voice_touch",
        description="Expected interaction mode on Kiosk UI"
    )
    options: list[str] | None = Field(
        default=None,
        description="List of choices if input_type is 'choice' or 'yes_no'"
    )
    section: str = Field(
        ...,
        description="Section key: 'chief_complaint', 'socrates', 'pmh', 'medications', 'allergies', 'family_hx', 'personal_hx', 'ros', 'complete'"
    )
    progress_pct: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Estimated overall interview progress percentage (0.0 to 100.0)"
    )
    is_red_flag_warning: bool = Field(
        default=False,
        description="True if current answer or context triggered a safety red flag"
    )
    red_flag_details: dict[str, Any] | None = Field(
        default=None,
        description="Optional warning metadata to render a calming alert on Kiosk"
    )


class InterviewAnswer(BaseModel):
    """
    Model for patient answers received from Kiosk frontend over WebSocket or REST.
    """
    model_config = ConfigDict(from_attributes=True)

    question_id: str = Field(..., description="The ID of the question being answered")
    answer_text: str = Field(..., description="Normalized transcribed or typed text of the answer")
    answer_option: str | None = Field(None, description="Selected option if choice/touch input")
    verbatim_voice: str | None = Field(None, description="Raw unnormalized ASR transcript if voice input")
    language: str = Field(default="hi", description="ISO language code of the answer, e.g. 'hi', 'en', 'ta'")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp of when answer was captured"
    )


class SummarySource(BaseModel):
    """
    Source citation linking a summary field to either transcript or scanned document crop.
    """
    type: Literal["transcript", "document"] = Field(..., description="Source medium")
    ref_id: str = Field(..., description="ID of transcript turn or scanned document")
    snippet: str | None = Field(None, description="Verbatim text snippet or citation")
    bbox_crop_url: str | None = Field(None, description="URL to cropped document bounding box image")


class SummaryField(BaseModel):
    """
    Structured field in the clinical intake summary presented to the doctor.
    """
    model_config = ConfigDict(from_attributes=True)

    field_id: str = Field(..., description="Unique field identifier")
    section: str = Field(
        ...,
        description="Summary section: 'chief_complaint', 'hpi', 'pmh', 'medications', 'allergies', 'ros', 'family_personal'"
    )
    content: str = Field(..., description="Clinically normalized summary statement")
    sources: list[SummarySource] = Field(
        default_factory=list,
        description="Evidence links to original paper bounding-box or transcript quote"
    )
    verification: Literal[
        "patient_reported",
        "document_extracted",
        "needs_confirmation",
        "conflicting"
    ] = Field(
        default="patient_reported",
        description="Trust & provenance badge for doctor review"
    )
    changed_since_last: bool = Field(
        default=False,
        description="True if Contradiction Radar flagged a change compared to previous visits"
    )


class RedFlagEvent(BaseModel):
    """
    Emergency danger event emitted when high-acuity keywords or clinical red flags are detected.
    """
    model_config = ConfigDict(from_attributes=True)

    event_id: str = Field(..., description="Unique event identifier")
    session_id: str = Field(..., description="Active kiosk session UUID")
    trigger_phrase: str = Field(..., description="Phrase or token that matched the trigger")
    matched_rule: str = Field(..., description="Rule or condition triggered")
    severity: Literal["red", "amber"] = Field(
        ...,
        description="'red' for immediate emergency stop; 'amber' for high-priority staff alert"
    )
    category: str = Field(..., description="Clinical category: 'cardiac', 'stroke', 'psychiatric', 'anaphylaxis', etc.")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when trigger fired"
    )
    dismissed_by: str | None = Field(None, description="Staff/Triage nurse ID who acknowledged or dismissed")
    dismiss_reason: str | None = Field(None, description="Clinical reason if dismissed or override applied")


# ==============================================================================
# DEV 2 STUB SCHEMAS (Documents, Data & Infrastructure Track)
# TODO: Dev 2 will finalize the concrete schema definitions for Module B and ABDM
# ==============================================================================

class ExtractedEntity(BaseModel):
    """
    [DEV 2 STUB] Output of the multimodal OCR & entity extraction pipeline.
    Finalized by Dev 2 in Phase 2.
    """
    model_config = ConfigDict(extra="allow")

    entity_id: str = Field(..., description="Unique entity ID")
    type: str = Field(..., description="e.g., 'diagnosis', 'medication', 'lab_value', 'allergy'")
    value: str = Field(..., description="Extracted clinical entity text")
    date: str | None = Field(None, description="Document date or mention date if available")
    source_document_id: str | None = Field(None, description="Foreign key to documents table")
    bounding_box: list[float] | None = Field(
        None,
        description="Normalized coordinates [x, y, w, h] (0.0 to 1.0) on original document image"
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence score")
    unit: str | None = Field(None, description="Lab unit if applicable")
    reference_range: str | None = Field(None, description="Normal reference range if lab")
    is_abnormal: bool | None = Field(None, description="Flagged by lab range validator")


class FHIRBundlePayload(BaseModel):
    """
    [DEV 2 STUB] ABDM standardized FHIR R4 Bundle payload.
    Finalized by Dev 2 in Phase 2/3.
    """
    model_config = ConfigDict(extra="allow")

    patient_abha_id: str = Field(..., description="ABHA address / ID of the patient")
    encounter_id: str = Field(..., description="OPD encounter UUID")
    summary_fields: list[SummaryField] = Field(
        default_factory=list,
        description="Verified clinical summary fields signed off by doctor"
    )
    consent_ref: str = Field(..., description="ABDM electronic consent artefact reference ID")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of bundle generation"
    )
    raw_fhir_json: dict[str, Any] | None = Field(
        None,
        description="Full FHIR R4 Bundle JSON resource"
    )
