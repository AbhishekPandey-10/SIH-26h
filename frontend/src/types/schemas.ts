/**
 * MediKiosk Frontend TypeScript Schemas (API Contract)
 * PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
 *
 * Mirrors the canonical Pydantic v2 schemas in shared/schemas/__init__.py
 */

export type InputType = "voice_touch" | "choice" | "scale" | "yes_no" | "voice" | "tap";

export interface RedFlagDetails {
  event_id?: string;
  severity: "red" | "amber";
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
  type: "transcript" | "document";
  ref_id: string;
  snippet?: string | null;
  bbox_crop_url?: string | null;
}

export interface SummaryField {
  field_id: string;
  section: "chief_complaint" | "hpi" | "pmh" | "medications" | "allergies" | "ros" | "family_personal" | string;
  content: string;
  sources: SummarySource[];
  verification: "patient_reported" | "document_extracted" | "needs_confirmation" | "conflicting";
  changed_since_last: boolean;
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

// Dev 2 placeholder shapes
export interface ExtractedEntity {
  entity_id: string;
  type: string;
  value: string;
  date?: string | null;
  source_document_id?: string | null;
  bounding_box?: number[] | null;
  confidence?: number;
  unit?: string | null;
  reference_range?: string | null;
  is_abnormal?: boolean | null;
}

export interface FHIRBundlePayload {
  patient_abha_id: string;
  encounter_id: string;
  summary_fields: SummaryField[];
  consent_ref: string;
  generated_at?: string;
  raw_fhir_json?: Record<string, any> | null;
}

export interface SessionStartResponse {
  session_id: string;
  patient_name: string;
  language: string;
  abha_id?: string | null;
  status: string;
}

export interface ConsentActionItem {
  action: string;
  granted: boolean;
}

