/**
 * MediKiosk TypeScript Shared Schemas (API Contract)
 * PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
 *
 * 1:1 mirroring of canonical Pydantic models in backend/app/shared/schemas.py
 */

// =============================================================================
// DEV 1 SCHEMAS (Conversation & Intelligence Track)
// =============================================================================

export type InputType = "voice_touch" | "choice" | "scale" | "yes_no";

export interface NextQuestion {
  question_id: string;
  text: string;
  audio_url?: string | null;
  input_type: InputType;
  options?: string[] | null;
  section: string;
  progress_pct: number;
  is_red_flag_warning?: boolean;
  red_flag_details?: {
    event_id?: string;
    severity?: "red" | "amber";
    category?: string;
    trigger_phrase?: string;
    matched_rule?: string;
  } | null;
}

export interface InterviewAnswer {
  question_id: string;
  answer_text: string;
  answer_option?: string | null;
  verbatim_voice?: string | null;
  language: string;
  timestamp: string; // ISO-8601 UTC
}

export interface SummarySource {
  type: "transcript" | "document";
  ref_id: string;
  snippet?: string | null;
  bbox_crop_url?: string | null;
}

export type VerificationStatus =
  | "patient_reported"
  | "document_extracted"
  | "needs_confirmation"
  | "conflicting";

export interface SummaryField {
  field_id: string;
  section: string;
  content: string;
  sources: SummarySource[];
  verification: VerificationStatus;
  changed_since_last?: boolean;
}

export interface RedFlagEvent {
  event_id: string;
  session_id: string;
  trigger_phrase: string;
  matched_rule: string;
  severity: "red" | "amber";
  category: string;
  timestamp: string;
  dismissed_by?: string | null;
  dismiss_reason?: string | null;
}

// =============================================================================
// DEV 2 SCHEMAS (Documents, Data & Infrastructure Track)
// =============================================================================

export type EntityType =
  | "diagnosis"
  | "medication"
  | "lab_value"
  | "allergy"
  | "procedure"
  | "vital";

export interface ExtractedEntity {
  entity_id: string;
  type: EntityType;
  value: string;
  generic_name?: string | null;
  date?: string | null;
  source_document_id?: string | null;
  bounding_box?: [number, number, number, number] | null; // [x, y, w, h] normalized (0.0 to 1.0)
  confidence: number;
  unit?: string | null;
  reference_range?: string | null;
  is_abnormal?: boolean | null;
}

export interface FHIRBundlePayload {
  patient_abha_id: string;
  encounter_id: string;
  summary_fields: SummaryField[];
  consent_ref: string;
  generated_at: string;
  raw_fhir_json?: Record<string, unknown> | null;
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
  auth_mode?: "MOBILE_OTP" | "AADHAAR_OTP" | "DEMOGRAPHICS";
}

export interface OTPVerify {
  txn_id: string;
  otp: string;
  abha_id: string;
}
