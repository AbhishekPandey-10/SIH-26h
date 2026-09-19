/**
 * MediKiosk Frontend TypeScript Schemas (Canonical API Contract)
 * PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
 *
 * Strict parity with canonical Pydantic v2 schemas in shared/schemas/__init__.py
 */

// ==============================================================================
// CANONICAL SYSTEM ENUMS & LITERAL UNIONS
// ==============================================================================

export type EntityType =
  | "diagnosis"
  | "medication"
  | "lab_value"
  | "allergy"
  | "procedure"
  | "vital";

export type SummarySection =
  | "chief_complaint"
  | "hpi"
  | "pmh"
  | "medications"
  | "allergies"
  | "ros"
  | "family_personal"
  | "changes_since_last_visit";

export type VerificationStatus =
  | "patient_reported"
  | "document_extracted"
  | "needs_confirmation"
  | "conflicting"
  | "doctor_edited";

export type SessionStatus = "active" | "completed" | "wiped";

export type DocumentStatus = "uploaded" | "extracted" | "error";

export type RedFlagSeverity = "red" | "amber";

export type InterviewMode = "allopathic" | "ayurvedic" | "dual";

export type ConsentAction =
  | "share_doctor"
  | "store_abdm"
  | "anonymized_research";

export type InputType =
  | "voice_touch"
  | "choice"
  | "scale"
  | "yes_no"
  | "voice"
  | "tap";

export type WebSocketMessageType =
  | "question"
  | "pause"
  | "resume"
  | "ack"
  | "clarification"
  | "completion"
  | "error";

// ==============================================================================
// DEV 1 SCHEMAS (Conversation & Intelligence Track)
// ==============================================================================

export interface RedFlagDetails {
  event_id?: string;
  id?: string;
  severity: RedFlagSeverity;
  category: string;
  trigger_phrase?: string;
  matched_rule?: string;
  [key: string]: any;
}

export interface NextQuestion {
  question_id: string;
  text: string;
  audio_url?: string | null;
  input_type: InputType;
  options?: string[] | null;
  section: string;
  progress_pct: number;
  is_red_flag_warning: boolean;
  red_flag_details?: RedFlagDetails | null;
  metadata?: {
    socrates_axis?: string;
    category?: string;
    [key: string]: any;
  } | null;
}

export interface InterviewAnswer {
  question_id: string;
  answer_text: string;
  answer_option?: string | null;
  verbatim_voice?: string | null;
  language: string;
  timestamp?: string;
}

export interface SummarySource {
  evidence_id?: string;
  session_id?: string | null;
  type: "transcript" | "document";
  ref_id: string;
  snippet?: string | null;
  bbox_crop_url?: string | null;
  document_id?: string | null;
  page_number?: number | null;
  bounding_box?: number[] | null;
  confidence?: number | null;
  entity_value?: string | null;
}

export interface SummaryField {
  field_id: string;
  section: SummarySection | string;
  content: string;
  original_content?: string | null;
  sources: SummarySource[];
  verification: VerificationStatus;
  changed_since_last: boolean;
  document_value?: string | null;
  patient_value?: string | null;
}

export interface ContradictionItem {
  id: string;
  field: string;
  old_value: string;
  old_source: string;
  new_value: string;
  new_source: string;
  change_type: "dosage_change" | "started" | "stopped" | "new_diagnosis" | "discrepancy";
  significance: "high" | "medium" | "low";
  status: "unreviewed" | "confirmed" | "flagged_error";
  old_source_ref?: Record<string, any> | null;
  new_source_ref?: Record<string, any> | null;
}

export interface PolypharmacyAlert {
  type: "brand_generic_duplicate" | "drug_interaction" | "contraindication";
  drug_a: string;
  drug_b?: string | null;
  severity: "high" | "medium" | "low";
  message: string;
}

export interface ResolveFieldRequest {
  resolution_choice: "use_document" | "use_patient" | "custom";
  resolved_value: string;
  doctor_id?: string | null;
  doctor_note?: string | null;
}

export interface RedFlagEvent {
  id: string;
  event_id?: string;
  session_id: string;
  trigger_phrase: string;
  matched_rule: string;
  severity: RedFlagSeverity;
  category: string;
  timestamp: string;
  is_dismissed?: boolean;
  dismissed_by?: string | null;
  dismiss_reason?: string | null;
  is_acknowledged?: boolean;
  acknowledged_by?: string | null;
  action_taken?: string | null;
}

// ==============================================================================
// DEV 2 SCHEMAS (Documents, Data & Infrastructure Track)
// ==============================================================================

export interface ExtractedEntity {
  id: string;
  entity_id?: string;
  document_id?: string | null;
  source_document_id?: string | null;
  session_id?: string | null;
  entity_type: EntityType;
  type?: string;
  verification?: VerificationStatus;
  value: string;
  generic_name?: string | null;
  date?: string | null;
  bounding_box?: number[] | null;
  confidence: number;
  unit?: string | null;
  reference_range?: string | null;
  is_abnormal?: boolean | null;
  created_at?: string | null;
}

export interface FHIRBundlePayload {
  patient_abha_id: string;
  encounter_id: string;
  summary_fields: SummaryField[];
  consent_ref: string;
  generated_at?: string;
  raw_fhir_json?: Record<string, any> | null;
}

export interface FHIRExportRequest {
  session_id: string;
  consent_artefact_id?: string | null;
  hip_id?: string | null;
  export_type?: "opd_summary" | "prescription" | "diagnostic_report";
  notes?: string | null;
}

export interface FHIRExportResponse {
  export_id?: string | null;
  session_id: string;
  status:
    | "pending"
    | "claimed"
    | "delivered"
    | "failed_retryable"
    | "failed_terminal"
    | "blocked_consent_revoked"
    | "blocked_stale_version"
    | "provider_not_configured"
    | "queued"
    | "in_progress"
    | "failed"
    | "blocked_no_consent";
  idempotency_key?: string | null;
  abdm_transaction_id?: string | null;
  transaction_id?: string | null;
  summary_version?: number | null;
  is_new?: boolean | null;
  error_message?: string | null;
  timestamp: string;
}

export interface FHIRPreviewResponse {
  session_id: string;
  patient_abha_id: string;
  summary_version?: number;
  summary_status?: string;
  bundle_type: string;
  resource_count: number;
  preview_json: Record<string, any>;
  is_signed_off: boolean;
}

export interface WebSocketEnvelope {
  type: WebSocketMessageType;
  payload: Record<string, any>;
  session_id?: string | null;
  timestamp: string;
  error?: string | null;
}

export interface PatientDemographics {
  abha_id: string;
  abha_number?: string | null;
  name: string;
  gender: "M" | "F" | "O";
  dob: string;
  mobile?: string | null;
  address?: string | null;
  district?: string | null;
  state?: string | null;
  photo_url?: string | null;
  is_verified: boolean;
}

export interface ABHASession {
  session_id: string;
  abha_id: string;
  auth_token: string;
  patient: PatientDemographics;
  expires_at: string;
}

export interface OTPRequest {
  identifier: string;
  auth_mode: "MOBILE_OTP" | "AADHAAR_OTP" | "DEMOGRAPHICS";
}

export interface OTPVerify {
  txn_id: string;
  otp: string;
  abha_id: string;
}

export interface ConsentActionItem {
  action: ConsentAction;
  granted: boolean;
}

export interface SessionStartResponse {
  session_id: string;
  patient_name: string;
  language: string;
  abha_id?: string | null;
  status: SessionStatus | string;
}
