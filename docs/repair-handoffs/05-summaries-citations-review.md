# Assignment 5 — Summaries, Citations, Doctor Review, Contradictions, and Medication Intelligence Handoff

**Status: COMPLETED AND VERIFIED**  
**Monorepo Baseline: Revision b3d619e + Assignments 1, 2, 3, & 4 Reconciliation**  
**Test Suites: `backend/tests/test_summary_review_meds.py` (13/13 PASS), `backend/tests/test_summary.py` (6/6 PASS), `backend/tests/test_polypharmacy.py` (4/4 PASS), Full Core Suite (107/107 PASS)**

---

## Implemented Outcomes & Root Causes Removed

1. **Zero Synthetic Clinical Fallback Across Summaries & Contradictions**:
   - **Summary Generation**: Removed `_load_fallback_entities` from `summary_generator.py`. The summary generator no longer seeds sample prescription entities (`doc_01_prescription_printed.json`) when document entities are missing. An empty encounter produces an empty summary with zero hallucinated medications or diseases.
   - **Contradiction Detection**: Removed unconditional demo deltas and synthetic history injection from `contradiction_detector.py`. Empty statements or empty historical encounters return empty contradiction lists `[]` rather than inventing an Amlodipine/Metformin/Glimepiride change.
   - **Delta Summary**: `format_delta_summary` returns empty string when zero contradictions exist, eliminating fabricated clinical change narratives.

2. **Strict Citation Validation & Provenance Integrity**:
   - **Ground Truth Verification**: `summary_generator._validate_and_tag_sources()` now strictly cross-references citations against active session transcripts and encounter-scoped extracted document entities.
   - **No Fabricated Document Provenance**: Non-existent document citations are NOT assigned fake document IDs (`doc_prev_presc_01`), synthetic bounding boxes (`[0.12, 0.34, 0.45, 0.08]`), or inflated confidence (`0.92`). Unknown coordinates remain `None`.
   - **Citation Downgrading**: Citations referencing unknown sources or failing validation are flagged `is_verified = False`, and the associated field is downgraded to `needs_confirmation = True`.
   - **Transcript Set Scoping**: An empty transcript set cannot verify claims.

3. **Session-Scoped Transcript Citation Lookup (`backend/app/routes/interview.py`)**:
   - Hardened `GET /api/interview/transcript/{ref_id}` against cross-patient leaks.
   - Queries with reusable question IDs (such as `q_cc_01`) across encounters without `session_id` query parameter return HTTP 400 Bad Request to prevent cross-session data leakage.
   - Unscoped memory scanning and mock transcript fallbacks have been removed.

4. **Reliable Nested JSON Persistence via Deep Copy & `flag_modified`**:
   - **Doctor Field Edit (`PUT /api/summary/{session_id}/field`)**: Updates nested dictionary entries on `ClinicalSummary.fields_json` using `copy.deepcopy()` and invokes `flag_modified(summary, "fields_json")`. Verified across fresh database sessions and restarts that doctor edits are reliably persisted and returned on `GET`.
   - **Doctor Resolution (`POST /api/summary/{session_id}/resolve`)**: Resolves discrepancies, creates an immutable audit row in `SummaryResolution`, updates `fields_json` via `flag_modified`, and persists cleanly to SQLite/PostgreSQL.

5. **Separation of Field Edits vs Doctor Verification**:
   - Editing a single field via `PUT /api/summary/{session_id}/field` marks that specific field `doctor_edited` and transitions the summary's `verification_status` to `"in_review"`. It does **not** prematurely mark the entire summary `"doctor_verified"`.
   - Implemented `POST /api/summary/{session_id}/verify` requiring authenticated clinician credentials (`StaffRole.DOCTOR`). This endpoint validates the summary draft, checks for unreviewed red flags, updates `verification_status = "doctor_verified"`, and logs `verified_by_doctor_id` and `verified_at`.

6. **Read-Only GET Endpoint Policy**:
   - `GET /api/summary/{session_id}` is strictly read-only. If a summary does not exist, it returns HTTP 404 Not Found.
   - It never implicitly runs background AI generation, never replaces existing summaries on read, and preserves existing clinician reviews.

7. **Complete HPI & Medication Preservation (Zero Truncation)**:
   - Removed arbitrary `[:3]` medication slicing and first-turn HPI truncation in fallback summary generation.
   - Preserves 4+ medications, patient denials, and conflicting evidence branches faithfully in `fields_json`.
   - Replaced non-standard section keys (`personal_hx`, `family_hx`) with canonical `SummarySection.family_personal` (`"family_personal"`), matching frontend schemas and design tokens.

8. **Polypharmacy Single-Entity & Ingredient Normalization**:
   - **Single-Entity Double Counting Elimination**: `polypharmacy_detector.py` eliminates double-counting of generic name and display value for a single entity.
   - **Word-Boundary Negation**: Replaced flawed `if 'no' in text` check with regex boundary matching (`\b(?:no|denies|not taking|stopped)\b`). Drugs like `atenolol` and `normodipine` are never erroneously removed by substring matching.
   - **Combination Molecule Splitting**: Formulations like `Metformin + Glimepiride` or `Amoxicillin / Clavulanate` are split into discrete molecular components (`metformin` and `glimepiride`) for accurate drug-drug interaction screening.
   - **Harmonized Shim**: `polypharmacy.py` delegates to `polypharmacy_detector.py`, eliminating conflicting rule engines and synthetic fallback lists.

9. **Contradiction Engine Null-Safety & Persistence**:
   - **Null-Safety**: Safe generic extraction `(e.get("generic") or "").lower()` eliminates `AttributeError` crashes when generic names are `None`.
   - **Deterministic Stable IDs**: Contradiction IDs are derived deterministically (`contra_{field}_{ctype}_{old}_{new}`) instead of random UUIDs, allowing client UI to stably track review status.
   - **Cross-Restart Review Persistence**: Clinician confirmation and dismissal actions are persisted to the database in `SummaryResolution`. The detector reloads these decisions so user review is not lost on page refresh or restart.
   - **Cross-Encounter Patient History**: Compares current encounter entities against historical encounter records for the same patient.

10. **Targeted Ask-Back Clarification**:
    - `POST /api/interview/ask-back/reply` directly updates the targeted draft field in `ClinicalSummary.fields_json` with the correlated answer, preserving doctor edits and other section fields without wholesale summary overwrite.

---

## Summary Version, Review, and Citation APIs

### 1. Summary Review Endpoints (`backend/app/routes/summary.py`)

#### A. Edit Field
- **Endpoint**: `PUT /api/summary/{session_id}/field`
- **Auth Required**: `Bearer <staff_token>` (`StaffRole.DOCTOR` or `StaffRole.NURSE`)
- **Request Body**:
  ```json
  {
    "section": "current_medications",
    "value": "Amlodipine 5mg OD, Metformin 500mg BD (Doctor confirmed)",
    "notes": "Verified dosage with patient relative"
  }
  ```
- **Response**: Updated `ClinicalSummaryResponse` with `verification_status = "in_review"`, targeted field marked `doctor_edited = true`.
- **Audit**: Writes row to `summary_resolutions` table with `action = "field_edit"`, `doctor_id`, `original_value`, `new_value`, `timestamp`.

#### B. Resolve Field / Citation
- **Endpoint**: `POST /api/summary/{session_id}/resolve`
- **Auth Required**: `Bearer <staff_token>` (`StaffRole.DOCTOR`)
- **Request Body**:
  ```json
  {
    "field_name": "allergies",
    "status": "doctor_verified",
    "notes": "Patient clarifies no known drug allergies, previous rash was viral"
  }
  ```
- **Response**: `ClinicalSummaryResponse` with targeted field updated and resolution logged.

#### C. Explicit Doctor Verification Sign-Off
- **Endpoint**: `POST /api/summary/{session_id}/verify`
- **Auth Required**: `Bearer <staff_token>` (`StaffRole.DOCTOR`)
- **Request Body**: (Optional notes)
  ```json
  {
    "notes": "Reviewed in OPD 4, all sections verified"
  }
  ```
- **Behavior**: Validates that all critical sections are present, sets `verification_status = "doctor_verified"`, sets `verified_by_doctor_id` to authenticated clinician, and stamps `verified_at`.

#### D. Read-Only Retrieval
- **Endpoint**: `GET /api/summary/{session_id}`
- **Auth Required**: `Bearer <staff_token>` or active session token
- **Behavior**: Strictly read-only; returns 404 if summary has not been generated. Never auto-regenerates or mutates draft state on read.

---

## Canonical Section Enums (`SummarySection`)

Shared between backend (`shared/schemas/__init__.py`) and frontend (`frontend/src/types/schemas.ts`):

```python
class SummarySection(str, Enum):
    # Standard Allopathic Lens
    CHIEF_COMPLAINT = "chief_complaint"
    HPI = "hpi"
    CURRENT_MEDICATIONS = "current_medications"
    PAST_HISTORY = "past_history"
    ALLERGIES = "allergies"
    FAMILY_PERSONAL = "family_personal"
    VITALS_LABS = "vitals_labs"
    RED_FLAGS = "red_flags"
    PLAN_ASSESSMENT = "plan_assessment"

    # Ayurvedic Lens
    PRAKRITI_DOSHA = "prakriti_dosha"
    AGNI_DIGESTIVE_FIRE = "agni_digestive_fire"
    DHATU_TISSUE_HEALTH = "dhatu_tissue_health"
    CHIKITSA_RECOMMENDATIONS = "chikitsa_recommendations"
```

---

## Immutable Citation Format & Provenance Contract

```python
class SourceCitation(BaseModel):
    ref_id: str                      # Immutable ID: transcript ID or document entity ID
    source_type: CitationSourceType  # "transcript", "document", "manual"
    entity_id: Optional[str] = None  # Specific entity ID if source_type == "document"
    quote: Optional[str] = None      # Verbatim text snippet or transcript turn
    bounding_box: Optional[List[float]] = None  # [x, y, w, h] in [0.0, 1.0] if document crop exists
    confidence: Optional[float] = None
    is_verified: bool = True         # False if citation could not be grounded to active encounter
```

### Scoping Rules
1. **Document Citations**: Must reference an `entity_id` and `document_id` existing within the authorized session or patient record. Citation validator verifies entity presence in the database; if missing, `is_verified` is set to `False` and no crop/bbox is fabricated.
2. **Transcript Citations**: Must match an active `transcript_id` within the session. Reusable IDs like `q_cc_01` cannot be queried globally without explicit session filtering.

---

## Medication Intelligence & Polypharmacy Report Contract

### Report Schema (`PolypharmacyReport`)
- **Status**: `completed_with_alerts` | `completed_without_alerts` | `incomplete`
- **Total Medications Analyzed**: Integer count of discrete normalized ingredients.
- **Alert Severities**:
  - `contraindicated`: Absolute contraindication (e.g. Metformin in acute severe renal impairment or iodinated contrast).
  - `high`: Severe risk (e.g. Warfarin + Aspirin/Ecosprin major bleeding risk).
  - `moderate`: Moderate interaction or duplicate therapy (e.g. Paracetamol + Combiflam containing paracetamol).
  - `low` / `info`: Minor pharmacokinetic considerations or food timing advice.

---

## Contradiction Action Semantics & Audit Persistence

1. **Deterministic Contradiction ID**:
   - Computed as: `contra_{field}_{contradiction_type}_{normalized_prior_val}_{normalized_current_val}`
   - Persists identically across re-evaluations and service restarts.

2. **Doctor Actions (`POST /api/contradictions/{session_id}/action`)**:
   - `action = "confirm"`: Clinician confirms the discrepancy; contradiction status is set to `confirmed` and logged to `SummaryResolution`.
   - `action = "dismiss"`: Clinician dismisses the discrepancy as non-clinical or resolved; contradiction status is set to `dismissed` and logged to `SummaryResolution`.

3. **Audit Row Record (`SummaryResolution`)**:
   - Columns populated: `session_id`, `doctor_id`, `field_name = "contradiction:{contra_id}"`, `action = "contradiction_confirm"` or `"contradiction_dismiss"`, `new_value = action`, `notes = json.dumps({"contradiction_id": ...})`, `resolved_at = utcnow()`.

---

## Export-Ready Reviewed-Version Selection Rules

1. **Doctor Verification Precondition**:
   - ABDM push (`POST /api/summary/{session_id}/fhir/push`) and PDF exports require `verification_status == "doctor_verified"`.
   - If a summary is `"unverified"` or `"in_review"`, export is rejected or blocked from official transmission unless explicitly flagged under documented emergency override protocol.
2. **Immutability of Signed Versions**:
   - Generating a new draft incremented version preserves the prior signed version in historical audit tables (`prior_drafts`).
   - Kiosk background generation or lens switching cannot overwrite a doctor-verified summary in place.

---

## Validation & Test Results

### Test Execution Commands
```powershell
# Run dedicated Assignment 5 regression suite (13 tests)
.venv\Scripts\pytest.exe tests/test_summary_review_meds.py -v

# Run related clinical summary and polypharmacy suites (23 tests total)
.venv\Scripts\pytest.exe tests/test_summary_review_meds.py tests/test_summary.py tests/test_polypharmacy.py -v

# Run all core regression suites (107 tests total)
.venv\Scripts\pytest.exe tests/test_summary_review_meds.py tests/test_summary.py tests/test_polypharmacy.py tests/test_migration_integrity.py tests/test_auth_consent_privacy.py tests/test_interview_safety.py tests/test_red_flag_escalation.py tests/test_document_ocr_labs.py tests/test_document_pipeline.py -v
```

### Results Summary
- `tests/test_summary_review_meds.py`: **13 passed in 0.44s**
- `tests/test_summary.py`: **6 passed**
- `tests/test_polypharmacy.py`: **4 passed**
- `tests/test_migration_integrity.py`: **13 passed**
- `tests/test_auth_consent_privacy.py`: **10 passed**
- `tests/test_interview_safety.py`: **11 passed**
- `tests/test_red_flag_escalation.py`: **5 passed**
- `tests/test_document_ocr_labs.py`: **38 passed**
- `tests/test_document_pipeline.py`: **7 passed**
- **Total: 107 passed, 0 failures, 0 errors.**

### Verified Acceptance Scenarios
1. **Empty Encounter Zero Fabrication**: Empty transcript and document sets yield zero medications, zero diagnoses, and zero fabricated provenance.
2. **Citation Validation Integrity**: Nonexistent citations are rejected without synthesizing fake crops, fake bounding boxes, or confidence 0.92.
3. **Unscoped Citation Lookup Defense**: Querying `GET /api/interview/transcript/{ref_id}` with reusable question ID across encounters returns HTTP 400.
4. **JSON Persistence Survival**: Field edits and resolutions survive fresh database sessions, cache invalidation, and server restarts.
5. **Explicit Doctor Sign-off**: Field edit sets `in_review`; only explicit `POST /verify` sets `doctor_verified`.
6. **Read-Only GET Endpoint**: `GET /api/summary/{session_id}` returns 404 when summary does not exist and never auto-generates.
7. **Four-Plus Medications Preservation**: 4+ medications and full HPI/SOCRATES responses are preserved without arbitrary truncation.
8. **Polypharmacy Single-Entity Normalization**: Generic + Brand for a single entity is analyzed as 1 therapy, not 2.
9. **Negation Regex Defense**: Drugs like `atenolol` are not removed by naive substring `"no"` matching.
10. **Combination Drug Splitting**: Formulations like `Metformin + Glimepiride` are analyzed across discrete molecular ingredients.
11. **Null-Safety**: Entities with `generic_name = None` or missing fields do not crash the contradiction engine.
12. **Contradiction Persistence**: Doctor decisions on contradictions survive page refresh and server restarts.
13. **Targeted Ask-Back Clarification**: Answering an ask-back clarification updates only the targeted draft field.

---

## Remaining Dependencies & Limitations

1. **Live Gemini Multimodal Synthesis**:
   - Offline verification uses deterministic local fallback extraction and mocked Gemini responses. Live clinical generation requires a valid `GEMINI_API_KEY`.
2. **Full Frontend Component Mounting**:
   - Backend APIs and schemas are validated and aligned with `frontend/src/types/schemas.ts`. Live browser rendering of the summary view and lens toggle should be verified during frontend assembly.
3. **ABDM National Gateway Push**:
   - FHIR bundles are constructed adhering to ABDM specifications; live transmission depends on national ABDM sandbox gateway uptime.
