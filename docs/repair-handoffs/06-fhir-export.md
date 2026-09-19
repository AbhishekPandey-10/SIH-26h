# Assignment 6 — Consent-Bound FHIR Export and Durable Delivery Handoff

**Status: COMPLETED AND VERIFIED**  
**Monorepo Baseline: Revision b3d619e + Assignments 1 through 5 Reconciliation**  
**Test Suite: `backend/tests/test_fhir_export.py` (20/20 PASS), Full Core Suite PASS**

---

## 1. Executive Summary & Audit Defects Resolved

Assignment 6 resolves all 16 adversarial audit defects identified in the FHIR export and delivery subsystem. Prior to this repair, the system contained default hardcoded patient identities, accepted unverified client-supplied FHIR payloads, bypassed patient electronic consent checks, fabricated ABDM bearer tokens and gateway reference IDs, lacked queue deduplication, and emitted clinical conflict warnings as active medications.

The repaired subsystem strictly guarantees:
1. **Zero Default or Fabricated Identities**: Patient identity and ABHA identifiers are resolved strictly from verified database records. Missing identities or unlinked encounters reject export with HTTP 422.
2. **Strict Consent Enforcement at Dispatch Time**: `store_abdm` consent is validated when an export is initiated AND re-validated in the background prior to each retry dispatch. Revocation immediately blocks transmission.
3. **Mandatory Clinician Affirmation**: FHIR Document Bundles can ONLY be exported from summaries verified by an authorized clinician (`doctor_verified`). Draft or preliminary summaries reject export with HTTP 422.
4. **Server-Side Clinical Data Provenance**: The server builds the FHIR bundle from the persisted, doctor-reviewed clinical snapshot. Client-supplied bundles are completely rejected.
5. **Accurate Clinical Resource Mapping**: Non-medication prose (warnings, conflicts, polypharmacy alerts) is excluded from `MedicationStatement` resources. Stopped medications are emitted with `status: "stopped"`.
6. **XHTML Narrative Sanitization**: Narrative `div` content in FHIR Composition and Observation resources is escaped using `html.escape()` to prevent XML injection and downstream XSS.
7. **Durable, Idempotent Queue Management**: Export jobs use deduplication key `{session_id}:{summary_version}`. Duplicate export submissions return the existing job rather than creating queue duplicates.
8. **Pluggable Transport Architecture**: Default transport is `UnavailableTransport` returning explicit `provider_not_configured` status. Sandbox demo transport is explicitly enabled only via configuration; no fake bearer tokens or random reference strings are generated.

---

## 2. API Specifications & Request/Response Contracts

All export endpoints require staff authentication (`Role.STAFF`) with bearer tokens. Kiosk and patient session tokens are strictly rejected with HTTP 403.

### 2.1 Clinician Preview: `GET /api/fhir/preview/{session_id}`
- **Purpose**: Allows clinicians to inspect the generated FHIR R4 Document Bundle prior to sign-off and dispatch.
- **Side Effects**: None. Does NOT record consent, does NOT sign off the summary, and does NOT enqueue or dispatch any bundle.
- **Headers**: `Authorization: Bearer staff_<id>`
- **Response Shape (`FHIRPreviewResponse`)**:
  ```json
  {
    "session_id": "sess_12345",
    "patient_abha_id": "rajesh.kumar@sbx",
    "summary_version": 2,
    "summary_status": "doctor_verified",
    "bundle_type": "document",
    "resource_count": 7,
    "preview_json": {
      "resourceType": "Bundle",
      "type": "document",
      "timestamp": "2026-09-19T08:30:00Z",
      "entry": [...]
    },
    "is_signed_off": true
  }
  ```

### 2.2 Affirm and Export: `POST /api/fhir/export`
- **Purpose**: Affirms clinical sign-off and dispatches/enqueues a consent-bound FHIR bundle to the ABDM gateway.
- **Headers**: `Authorization: Bearer staff_<id>`
- **Request Shape (`FHIRExportRequest`)**:
  ```json
  {
    "session_id": "sess_12345",
    "notes": "Affirmed after teleconsult review."
  }
  ```
- **Response Shape (`FHIRExportResponse`)**:
  ```json
  {
    "export_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "session_id": "sess_12345",
    "status": "delivered",
    "idempotency_key": "sess_12345:2",
    "abdm_transaction_id": "abdm-tx-987654321",
    "summary_version": 2,
    "is_new": true,
    "error_message": null,
    "timestamp": "2026-09-19T08:30:05Z"
  }
  ```
- **HTTP Error States**:
  - `401 Unauthorized`: Missing or invalid credentials.
  - `403 Forbidden`: Caller lacks `Role.STAFF` role, OR patient has not granted effective `store_abdm` consent.
  - `404 Not Found`: Session or clinical summary does not exist.
  - `422 Unprocessable Content`: Session has no linked patient record, patient has no ABHA, or summary has not been verified by a clinician (`status != "doctor_verified"`).

### 2.3 Process Retry Queue: `POST /api/fhir/retry-queue`
- **Purpose**: Worker or scheduled task endpoint to process pending and retryable export jobs.
- **Headers**: `Authorization: Bearer staff_<id>`
- **Behavior**:
  - Claims deliverable jobs using lease locking (`locked_at`, `locked_by`).
  - Re-evaluates `store_abdm` consent before each dispatch. If revoked, sets `status = "blocked_consent_revoked"`.
  - Re-evaluates summary version. If the summary was updated since the job was enqueued, sets `status = "blocked_stale_version"`.
  - Applies exponential backoff ($2^{\text{retry\_count}} \times 30\text{s}$) to prevent network hammering.
  - Bounded retries: after `max_retry_count` (default: 5) failures, transitions job to `failed_terminal`.
  - Updates the SAME row in place; never creates duplicate queue rows.
- **Response Shape**:
  ```json
  {
    "processed": 1,
    "results": [
      {
        "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "status": "delivered",
        "action": "delivered",
        "transaction_id": "abdm-tx-987654321",
        "retry_count": 2
      }
    ]
  }
  ```

### 2.4 Export Job Audit: `GET /api/fhir/jobs/{session_id}`
- **Purpose**: Returns the full delivery history, attempt logs, and status for all export jobs associated with an encounter.
- **Response Shape**:
  ```json
  [
    {
      "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "session_id": "sess_12345",
      "status": "delivered",
      "idempotency_key": "sess_12345:2",
      "summary_version": 2,
      "retry_count": 1,
      "max_retry_count": 5,
      "abdm_transaction_id": "abdm-tx-987654321",
      "delivered_at": "2026-09-19T08:30:05Z",
      "last_error": null,
      "created_at": "2026-09-19T08:30:00Z",
      "updated_at": "2026-09-19T08:30:05Z"
    }
  ]
  ```

---

## 3. FHIR R4 Profile Mapping & Clinical Intelligence

The bundle builder (`app/services/fhir_builder.py`) constructs standard FHIR R4 Document Bundles complying with NRCES and ABDM health data standards.

### 3.1 Resource Architecture & References
- **Bundle**: `type: "document"`, contains `Composition` as the first entry (`entry[0]`).
- **Internal Reference Standard**: All references between bundle resources use RFC 4122 UUID URIs (`urn:uuid:<uuid>`). Patient ABHA addresses are never used directly as resource IDs.
- **Patient Resource**:
  - `id`: Internal UUID.
  - `identifier[0]`: System `https://healthid.abdm.gov.in`, Value: `<patient_abha_id>`.
  - `identifier[1]`: System `urn:medikiosk:patient-id`, Value: `<patient_id>`.
- **Encounter Resource**: `status: "finished"`, `class: AMB` (ambulatory outpatient).
- **Composition Resource**:
  - `status`: Derived strictly from summary review state: `"final"` if `doctor_verified`, otherwise `"preliminary"`.
  - `type`: LOINC `11503-0` (Medical records).
  - `author`: Clinician who affirmed the summary (`verified_by`).
  - `section`: Structured sections mapped to standard LOINC codes:
    - Chief Complaint: `10154-3`
    - History of Present Illness (HPI): `10164-2`
    - Past Medical History: `11348-0`
    - Current Medications: `10160-0`
    - Allergies: `48765-2`
    - Family / Personal History: `10157-6`
    - Review of Systems: `10187-3`
    - Vitals / Labs: `8716-3`
    - Red Flags: `74018-3`
    - Plan & Assessment: `51847-2`

### 3.2 Clinical Noise Filtering & Status Classification
- **Alert / Conflict Filtering**: Clinical notes often contain alerts such as `"⚠ CONFLICT: Patient reported 1000mg but prescription shows 500mg"` or `"Alert: Polypharmacy risk"`. The builder detects alert prose via regex and excludes it from `MedicationStatement` resources to prevent corrupting patient EHRs with synthetic medication entries.
- **Medication Status Determination**:
  - Active medications: `MedicationStatement.status = "active"`
  - Stopped / discontinued medications (e.g. `"Atorvastatin 20mg OD (stopped due to myalgia)"`): `MedicationStatement.status = "stopped"`.
- **XHTML Narrative Sanitization**:
  - All text inserted into Composition narrative `div` blocks is sanitized via `html.escape(quote=True)`.
  - Prevents malformed XML documents that fail gateway validation and mitigates XSS risks in viewing software.

---

## 4. Transport Abstraction & Queue Mechanics

### 4.1 Injectable Transport Layer (`app/services/abdm_push.py`)
Export delivery is completely decoupled from HTTP routes via the `ABDMTransport` abstract protocol:

```
                  ┌───────────────────────────────┐
                  │    POST /api/fhir/export      │
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │      ExportQueueManager       │
                  └───────────────┬───────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
         ▼                        ▼                        ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│UnavailableTransport│  │ SandboxDemoTransport│  │  TestTransport   │
│(Default/Safe)    │    │(Dev/Sandbox)     │    │(Isolated Tests)  │
└──────────────────┘    └──────────────────┘    └──────────────────┘
```

- **`UnavailableTransport` (Default)**: Used when no ABDM provider is configured. Safely records jobs and returns `provider_not_configured` without making external network calls.
- **`SandboxDemoTransport`**: Enabled only when `ABDM_PUSH_PROVIDER=sandbox_demo` and credentials (`ABDM_CLIENT_ID`, `ABDM_CLIENT_SECRET`) are present. Parses actual gateway acknowledgements (`transactionId` or `requestId`). Never synthesizes mock tokens or reference codes.
- **`TestTransport`**: Deterministic in-memory transport for automated test suites. Captures payloads, timestamps, and recipient ABHA IDs.

### 4.2 Network Ambiguity Handling
If a network timeout occurs after a request payload has been dispatched to the gateway, the outcome is fundamentally ambiguous (the gateway may have processed the request before the client socket dropped). The subsystem flags the attempt as `is_timeout_after_send=True` and records `Timeout after send (delivery unknown)`. The job remains in `failed_retryable` status for reconciliation rather than blindly creating duplicate dispatches.

### 4.3 Database Schema: `FHIRPushQueue`
The `fhir_push_queue` table maintains full operational state:
| Column | Type | Description |
|---|---|---|
| `id` | VARCHAR(36) | Primary Key UUID |
| `session_id` | VARCHAR(36) | Foreign Key -> `sessions.id` |
| `idempotency_key` | VARCHAR(128) | UNIQUE index (`{session_id}:{summary_version}`) |
| `patient_abha_id` | VARCHAR(64) | Resolved ABHA identifier |
| `summary_version` | INTEGER | Exact summary version affirmed |
| `affirmed_by_doctor_id` | VARCHAR(64) | Clinician user ID |
| `bundle_json` | JSON | Complete FHIR R4 Bundle JSON payload |
| `status` | VARCHAR(32) | `pending`, `claimed`, `delivered`, `failed_retryable`, `failed_terminal`, `blocked_consent_revoked`, `blocked_stale_version` |
| `retry_count` | INTEGER | Current attempt count |
| `max_retry_count` | INTEGER | Maximum retry threshold (default: 5) |
| `attempt_history` | JSON | Array of attempt logs with timestamps, worker IDs, and errors |
| `locked_at` | DATETIME | Lease acquisition timestamp |
| `locked_by` | VARCHAR(64) | Worker ID holding the lease lock |
| `delivered_at` | DATETIME | Timestamp of gateway delivery confirmation |
| `abdm_transaction_id` | VARCHAR(128) | Actual gateway transaction ID |
| `consent_verified_at` | DATETIME | Timestamp of most recent consent revalidation |

---

## 5. Privacy Protection & Encounter Lifecycle

1. **Session Termination & Privacy Wipe**:
   - In accordance with the project data retention policy, when an encounter session ends without effective consent (`share_doctor=False` or revoked), the session manager executes a complete privacy wipe.
   - All pending and undelivered entries in `fhir_push_queue` for that session are purged immediately along with documents, extracted entities, and transcripts.
2. **Consent Revocation While Queued**:
   - If a patient grants consent during their kiosk visit but later revokes `store_abdm` before queued retries are dispatched, the retry queue detects the revocation on its pre-dispatch check.
   - The job is immediately transitioned to `blocked_consent_revoked`, and the bundle is permanently prevented from leaving the hospital boundary.

---

## 6. Verification & Test Evidence

The entire subsystem is verified by 20 exhaustive acceptance tests in `backend/tests/test_fhir_export.py`:

```powershell
& "w:\SIH\Proj\backend\.venv\Scripts\pytest.exe" tests/test_fhir_export.py -v
```

| Test Case | Scenario Verified | Outcome |
|---|---|---|
| `test_export_rejected_without_consent` | No `store_abdm` consent recorded | HTTP 403 Forbidden |
| `test_export_rejected_when_consent_refused` | Explicit consent refusal (`granted=False`) | HTTP 403 Forbidden |
| `test_export_rejected_when_consent_revoked_after_grant` | Consent granted then revoked | HTTP 403 Forbidden |
| `test_export_rejected_without_clinician_affirmation` | Exporting draft/unverified summary | HTTP 422 Unprocessable Content |
| `test_export_rejected_for_wrong_role_kiosk` | Kiosk or session tokens calling export/preview | HTTP 403 Forbidden |
| `test_export_rejected_for_unlinked_session_no_patient` | Encounter with no linked patient record | HTTP 422 Unprocessable Content |
| `test_export_rejected_for_patient_without_abha` | Patient has empty/missing ABHA | HTTP 422 Unprocessable Content |
| `test_export_stale_summary_version_retry_blocked` | Summary edited after export queued | Marked `blocked_stale_version` |
| `test_client_supplied_bundle_ignored` | Client injects malicious FHIR payload | Server builds from DB; payload ignored |
| `test_preview_uses_exact_persisted_version` | Clinician previews reviewed fields | Preview matches DB; no queue rows added |
| `test_preview_and_export_consistency` | Preview vs exported bundle parity | Identical resource counts & versions |
| `test_conflicts_and_alerts_not_emitted_as_active_medications` | Alert prose vs active/stopped meds | Alerts excluded; stopped status preserved |
| `test_xhtml_narrative_properly_escaped` | Nasty XML/HTML characters in notes | All tags escaped; valid XHTML generated |
| `test_repeated_failures_increase_attempts_on_one_job` | Consecutive network failures | 1 queue row; retry count incremented |
| `test_concurrent_claims_cannot_duplicate_delivery` | Concurrent worker claiming leased job | Second worker skipped |
| `test_repeated_client_submissions_use_idempotency` | Multiple clinician clicks on Export | Same job returned; 1 gateway dispatch |
| `test_network_timeout_after_send_marks_unknown_delivery` | Network drop after request dispatched | Marked ambiguous retryable; not lost |
| `test_revocation_before_retry_blocks_queued_export` | Consent revoked while waiting in retry queue | Dispatch blocked; marked revoked |
| `test_privacy_cleanup_purges_queued_exports` | Session ends unconsented | Undelivered queue rows purged |
| `test_default_transport_unavailable_and_injected_transport_works` | Default unconfigured transport | Returns `provider_not_configured` |

**Result: 20 passed in 1.15s.**
