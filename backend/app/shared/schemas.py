"""
MediKiosk Shared Schemas (Canonical API & Domain Contract)
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Canonical contract models for:
- Dev 1 (Conversation & Intelligence): NextQuestion, InterviewAnswer, SummaryField, RedFlagEvent, ContradictionItem, PolypharmacyAlert
- Dev 2 (Documents, Data & Infrastructure): ExtractedEntity, FHIRBundlePayload, PatientDemographics, ABHASession, Consent
- System Enums & DTOs: EntityType, SummarySection, VerificationStatus, SessionStatus, DocumentStatus, RedFlagSeverity, WebSocketEnvelope, FHIRExport
"""

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


# ==============================================================================
# CANONICAL SYSTEM ENUMS
# ==============================================================================

class EntityType(str, Enum):
    DIAGNOSIS = "diagnosis"
    MEDICATION = "medication"
    LAB_VALUE = "lab_value"
    ALLERGY = "allergy"
    PROCEDURE = "procedure"
    VITAL = "vital"


class SummarySection(str, Enum):
    CHIEF_COMPLAINT = "chief_complaint"
    HPI = "hpi"
    PMH = "pmh"
    MEDICATIONS = "medications"
    ALLERGIES = "allergies"
    ROS = "ros"
    FAMILY_PERSONAL = "family_personal"
    CHANGES_SINCE_LAST_VISIT = "changes_since_last_visit"


class VerificationStatus(str, Enum):
    PATIENT_REPORTED = "patient_reported"
    DOCUMENT_EXTRACTED = "document_extracted"
    NEEDS_CONFIRMATION = "needs_confirmation"
    CONFLICTING = "conflicting"
    DOCTOR_EDITED = "doctor_edited"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    WIPED = "wiped"


class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    EXTRACTED = "extracted"
    ERROR = "error"


class RedFlagSeverity(str, Enum):
    RED = "red"
    AMBER = "amber"


class InterviewMode(str, Enum):
    ALLOPATHIC = "allopathic"
    AYURVEDIC = "ayurvedic"
    DUAL = "dual"


class ConsentAction(str, Enum):
    SHARE_DOCTOR = "share_doctor"
    STORE_ABDM = "store_abdm"
    ANONYMIZED_RESEARCH = "anonymized_research"


class WebSocketMessageType(str, Enum):
    QUESTION = "question"
    PAUSE = "pause"
    RESUME = "resume"
    ACK = "ack"
    CLARIFICATION = "clarification"
    COMPLETION = "completion"
    ERROR = "error"


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
    input_type: Literal["voice_touch", "choice", "scale", "yes_no", "voice", "tap"] = Field(
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
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Optional clinical metadata e.g. socrates_axis, category"
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
    Has immutable evidence ID and encounter scoping for clinical provenance.
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, extra="allow")

    evidence_id: str = Field(
        default_factory=lambda: f"ev_{uuid.uuid4().hex[:12]}",
        description="Immutable evidence identifier for audit provenance"
    )
    session_id: str | None = Field(None, description="Encounter session UUID scoping this evidence")
    type: Literal["transcript", "document"] = Field(..., description="Source medium")
    ref_id: str = Field(..., description="ID of transcript turn or scanned document")
    snippet: str | None = Field(None, description="Verbatim text snippet or citation")
    bbox_crop_url: str | None = Field(None, description="URL to cropped document bounding box image")
    document_id: str | None = Field(None, description="Scanned document ID if applicable")
    page_number: int | None = Field(None, description="Page number of the document")
    bounding_box: list[float] | None = Field(None, description="Normalized [x, y, w, h]")
    confidence: float | None = Field(None, description="OCR extraction confidence (0.0 to 1.0)")
    entity_value: str | None = Field(None, description="Extracted entity string value")


class SummaryField(BaseModel):
    """
    Structured field in the clinical intake summary presented to the doctor.
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, extra="allow")

    field_id: str = Field(..., description="Unique field identifier")
    section: SummarySection | str = Field(
        ...,
        description="Summary section: 'chief_complaint', 'hpi', 'pmh', 'medications', 'allergies', 'ros', 'family_personal', 'changes_since_last_visit'"
    )
    content: str = Field(..., description="Clinically normalized summary statement")
    original_content: str | None = Field(None, description="Original unedited content if modified by doctor")
    sources: list[SummarySource] = Field(
        default_factory=list,
        description="Evidence links to original paper bounding-box or transcript quote"
    )
    verification: VerificationStatus | str = Field(
        default=VerificationStatus.PATIENT_REPORTED,
        description="Trust & provenance badge for doctor review"
    )
    changed_since_last: bool = Field(
        default=False,
        description="True if Contradiction Radar flagged a change compared to previous visits"
    )
    document_value: str | None = Field(None, description="Extracted document value for conflicting fields")
    patient_value: str | None = Field(None, description="Reported patient value for conflicting fields")


class ContradictionItem(BaseModel):
    """
    Contradiction or medication/diagnosis delta detected between current interview and historical records.
    """
    model_config = ConfigDict(from_attributes=True, extra="allow")

    id: str = Field(default_factory=lambda: f"contra_{uuid.uuid4().hex[:8]}")
    field: str = Field(..., description="Clinical field or medication category")
    old_value: str = Field(..., description="Prior recorded value or prescription dose")
    old_source: str = Field(..., description="Source text or citation of historical record")
    new_value: str = Field(..., description="Current stated or prescribed value")
    new_source: str = Field(..., description="Source text or citation of current interview turn")
    change_type: Literal["dosage_change", "started", "stopped", "new_diagnosis", "discrepancy"] = Field(...)
    significance: Literal["high", "medium", "low"] = Field(default="medium")
    status: Literal["unreviewed", "confirmed", "flagged_error"] = Field(default="unreviewed")
    old_source_ref: dict[str, Any] | None = None
    new_source_ref: dict[str, Any] | None = None


class PolypharmacyAlert(BaseModel):
    """
    Alert for duplicated generic entities or dangerous drug-drug interactions.
    """
    model_config = ConfigDict(from_attributes=True, extra="allow")

    type: Literal["brand_generic_duplicate", "drug_interaction", "contraindication"] = Field(...)
    drug_a: str = Field(...)
    drug_b: str | None = None
    severity: Literal["high", "medium", "low"] = Field(default="medium")
    message: str = Field(...)


class ResolveFieldRequest(BaseModel):
    """
    Doctor's resolution choice on a conflicting summary field.
    """
    resolution_choice: Literal["use_document", "use_patient", "custom"] = Field(...)
    resolved_value: str = Field(...)
    doctor_id: str | None = Field(default="doc_opd_01")
    doctor_note: str | None = Field(default=None)


class RedFlagEvent(BaseModel):
    """
    Emergency danger event emitted when high-acuity keywords or clinical red flags are detected.
    Supports both `id` and legacy `event_id` seamlessly.
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, extra="allow")

    id: str = Field(
        default_factory=lambda: f"rfe_{uuid.uuid4().hex[:12]}",
        validation_alias=AliasChoices("id", "event_id"),
        description="Unique event identifier"
    )
    session_id: str = Field(..., description="Active kiosk session UUID")
    trigger_phrase: str = Field(..., description="Phrase or token that matched the trigger")
    matched_rule: str = Field(..., description="Rule or condition triggered")
    severity: RedFlagSeverity | Literal["red", "amber"] = Field(
        ...,
        description="'red' for immediate emergency stop; 'amber' for high-priority staff alert"
    )
    category: str = Field(..., description="Clinical category: 'cardiac', 'stroke', 'psychiatric', 'anaphylaxis', etc.")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when trigger fired"
    )
    is_dismissed: bool = Field(default=False, description="True if dismissed by staff")
    dismissed_by: str | None = Field(None, description="Staff/Triage nurse ID who acknowledged or dismissed")
    dismiss_reason: str | None = Field(None, description="Clinical reason if dismissed or override applied")
    is_acknowledged: bool = Field(default=False, description="True if acknowledged by staff")
    acknowledged_by: str | None = Field(None, description="Staff ID who acknowledged the red flag")
    action_taken: str | None = Field(None, description="Clinical action taken upon acknowledgement")

    @property
    def event_id(self) -> str:
        return self.id


# ==============================================================================
# DEV 2 SCHEMAS (Documents, Data & Infrastructure Track)
# ==============================================================================

class ExtractedEntity(BaseModel):
    """
    Output of the multimodal OCR & entity extraction pipeline (Module B).
    Matches DB extracted_entities schema while maintaining compatibility with legacy field names.
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, extra="allow")

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        validation_alias=AliasChoices("id", "entity_id"),
        description="Unique entity UUID, e.g. 'ent_med_01'"
    )
    document_id: str | None = Field(
        None,
        validation_alias=AliasChoices("document_id", "source_document_id"),
        description="Foreign key to documents table"
    )
    session_id: str | None = Field(None, description="Foreign key to sessions table")
    entity_type: EntityType = Field(
        ...,
        validation_alias=AliasChoices("entity_type", "type"),
        description="Standardized clinical entity category: diagnosis, medication, lab_value, allergy, procedure, vital"
    )
    verification: VerificationStatus = Field(
        default=VerificationStatus.DOCUMENT_EXTRACTED,
        description="Trust & provenance badge for extracted entity"
    )
    value: str = Field(..., description="Extracted clinical entity text, e.g. 'Tab Glycomet 500mg'")
    generic_name: str | None = Field(None, description="Normalized generic drug name, e.g. 'Metformin'")
    date: str | None = Field(None, description="Document date or mention date if available (YYYY-MM-DD)")
    bounding_box: list[float] | None = Field(
        None,
        description="Normalized coordinates [x, y, w, h] (0.0 to 1.0) on original document image"
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence score (0.0 to 1.0)")
    unit: str | None = Field(None, description="Lab unit if applicable, e.g. 'mg/dL', 'g/dL'")
    reference_range: str | None = Field(None, description="Normal reference range if lab, e.g. '70-100'")
    is_abnormal: bool | None = Field(None, description="Flagged as abnormal by lab range validator")
    created_at: datetime | None = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of entity extraction"
    )

    @field_validator("bounding_box", mode="before")
    @classmethod
    def validate_bounding_box(cls, v: Any) -> list[float] | None:
        if v is None:
            return None
        if isinstance(v, (list, tuple)):
            if len(v) != 4:
                return None
            try:
                coords = [float(x) for x in v]
            except (ValueError, TypeError):
                return None
            import math
            if not all(math.isfinite(c) for c in coords):
                return None
            x, y, w, h = coords
            if not all(0.0 <= c <= 1.0 for c in (x, y, w, h)):
                return None
            if x + w > 1.001 or y + h > 1.001:
                return None
            return [round(c, 4) for c in coords]
        return None

    @field_validator("entity_type", mode="before")
    @classmethod
    def normalize_entity_type(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_clean = v.lower().strip()
            # Normalize vital_sign/vitals to canonical vital
            if v_clean in ("vital_sign", "vitals"):
                return "vital"
            # Strip low-confidence or needs_confirmation suffixes attached to entity type
            if "_low_confidence" in v_clean:
                v_clean = v_clean.replace("_low_confidence", "")
            if ":needs_confirmation" in v_clean:
                v_clean = v_clean.replace(":needs_confirmation", "")
            return v_clean
        return v

    @property
    def entity_id(self) -> str:
        return self.id

    @property
    def type(self) -> str:
        return self.entity_type.value if hasattr(self.entity_type, "value") else str(self.entity_type)

    @property
    def source_document_id(self) -> str | None:
        return self.document_id


class FHIRBundlePayload(BaseModel):
    """
    ABDM standardized FHIR R4 Bundle payload for health record export.
    """
    model_config = ConfigDict(from_attributes=True, extra="allow")

    patient_abha_id: str = Field(..., description="ABHA address / ID of the patient, e.g. 'rajesh.kumar@abdm'")
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
        description="Full FHIR R4 Bundle JSON resource complying with ABDM profiles"
    )


class FHIRExportRequest(BaseModel):
    """Request to initiate FHIR R4 Bundle export to ABDM gateway."""
    session_id: str = Field(..., description="OPD encounter session UUID")
    consent_artefact_id: str | None = Field(None, description="Signed ABDM consent artefact ID")
    hip_id: str | None = Field(None, description="Hospital Information Provider ID")
    export_type: Literal["opd_summary", "prescription", "diagnostic_report"] = Field(
        default="opd_summary",
        description="FHIR composition profile to export"
    )
    notes: str | None = Field(None, description="Optional clinician notes on export decision")


class FHIRExportResponse(BaseModel):
    """Response status for FHIR R4 export operation."""
    export_id: str = Field(
        default_factory=lambda: f"export_{uuid.uuid4().hex[:12]}",
        description="Unique export tracking job ID"
    )
    session_id: str = Field(..., description="Encounter session UUID")
    status: str = Field(
        ...,
        description=(
            "Status: pending, claimed, delivered, failed_retryable, failed_terminal, "
            "blocked_consent_revoked, blocked_stale_version, provider_not_configured, "
            "queued, in_progress, failed, blocked_no_consent"
        ),
    )
    idempotency_key: str | None = Field(None, description="Deduplication key (session:version)")
    abdm_transaction_id: str | None = Field(None, description="Actual ABDM correlation ID")
    transaction_id: str | None = Field(None, description="ABDM gateway transaction tracking ID")
    summary_version: int | None = Field(None, description="Exact summary version exported")
    is_new: bool | None = Field(None, description="True if new job created, False if existing returned")
    error_message: str | None = Field(None, description="Reason if export blocked or failed")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class FHIRPreviewResponse(BaseModel):
    """Clinician preview of FHIR bundle before sign-off and dispatch."""
    session_id: str = Field(..., description="OPD encounter session UUID")
    patient_abha_id: str = Field(..., description="Resolved patient ABHA")
    summary_version: int = Field(default=1, description="Summary version previewed")
    summary_status: str = Field(default="draft", description="Summary verification status")
    bundle_type: str = Field(default="document", description="FHIR bundle type")
    resource_count: int = Field(..., description="Total FHIR resources in bundle")
    preview_json: dict[str, Any] = Field(..., description="Preview JSON of bundle resources")
    is_signed_off: bool = Field(default=False, description="True if clinician has signed off on bundle")


class WebSocketEnvelope(BaseModel):
    """
    Typed message envelope for WebSocket communication between Kiosk and Backend.
    Distinguishes: question | pause | resume | ack | clarification | completion | error
    """
    model_config = ConfigDict(from_attributes=True, extra="allow")

    type: WebSocketMessageType | Literal[
        "question",
        "pause",
        "resume",
        "ack",
        "clarification",
        "completion",
        "error"
    ] = Field(..., description="Discriminator message event type")
    payload: dict[str, Any] = Field(default_factory=dict, description="Event-specific payload data")
    session_id: str | None = Field(None, description="Active session UUID")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp of event creation"
    )
    error: str | None = Field(None, description="Error message if type is 'error'")


class PatientDemographics(BaseModel):
    """
    Patient demographic profile verified via ABHA or Aadhaar e-KYC.
    """
    model_config = ConfigDict(from_attributes=True)

    abha_id: str = Field(..., description="14-digit ABHA number or ABHA address, e.g. 'rajesh.kumar@abdm'")
    abha_number: str | None = Field(None, description="14-digit numerical ABHA ID")
    name: str = Field(..., description="Full legal name of patient")
    gender: Literal["M", "F", "O"] = Field(..., description="Gender: M (Male), F (Female), O (Other)")
    dob: str = Field(..., description="Date of birth in YYYY-MM-DD or year of birth YYYY")
    mobile: str | None = Field(None, description="Linked 10-digit Indian mobile number")
    address: str | None = Field(None, description="Full residential address")
    district: str | None = Field(None, description="District name")
    state: str | None = Field(None, description="State name")
    photo_url: str | None = Field(None, description="Demographic photo URL or data URI")
    is_verified: bool = Field(default=True, description="True if authenticated through ABDM sandbox")


class ABHASession(BaseModel):
    """
    Active authenticated ABDM session returned upon OTP verification.
    """
    model_config = ConfigDict(from_attributes=True)

    session_id: str = Field(..., description="Internal kiosk session UUID")
    abha_id: str = Field(..., description="Verified patient ABHA address")
    auth_token: str = Field(..., description="ABDM gateway bearer access token")
    patient: PatientDemographics = Field(..., description="Patient demographic details")
    expires_at: datetime = Field(..., description="Session expiry timestamp")


class OTPRequest(BaseModel):
    identifier: str = Field(..., description="Aadhaar number, mobile, or ABHA address")
    auth_mode: Literal["MOBILE_OTP", "AADHAAR_OTP", "DEMOGRAPHICS"] = Field(
        default="MOBILE_OTP",
        description="Selected ABDM authentication method"
    )


class OTPVerify(BaseModel):
    txn_id: str = Field(..., description="Transaction ID returned by request-otp")
    otp: str = Field(..., description="6-digit authentication OTP")
    abha_id: str = Field(..., description="Patient ABHA ID")


class ConsentActionItem(BaseModel):
    """Consent status for a specific data-sharing scope."""
    action: ConsentAction | Literal["share_doctor", "store_abdm", "anonymized_research"] = Field(
        ..., description="Consent purpose / action"
    )
    granted: bool = Field(..., description="True if consent granted, False if refused/revoked")


class SessionStartResponse(BaseModel):
    """Response returned upon kiosk session initialization."""
    session_id: str = Field(..., description="Session UUID")
    patient_name: str = Field(..., description="Patient display name")
    language: str = Field(..., description="Selected language code")
    abha_id: str | None = Field(None, description="Verified ABHA ID if authenticated")
    status: SessionStatus | str = Field(default=SessionStatus.ACTIVE, description="Session status")
