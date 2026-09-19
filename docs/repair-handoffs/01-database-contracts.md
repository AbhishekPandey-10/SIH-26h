# Handoff 01 — Database Integrity and Canonical Contracts

**Assignment**: 1 — Database integrity and canonical contracts  
**Revision / Head**: `003_reconcile_schema` (Alembic)  
**Date**: 2026-09-19  
**Status**: COMPLETE  

---

## 1. Implemented Outcomes & Root Causes Removed

### A. Full ORM ↔ Migration Reconciliation
- **Root Cause Removed**: The fresh Alembic migration chain was missing 7 columns on `sessions`, 5 columns on `interview_transcripts`, 3 columns on `summaries`, `created_at` NOT NULL constraint on `extracted_entities`, orphan `patient_id` in `consent_audit`, `ix_interview_transcripts_session_id` index, and the entire `summary_resolutions` table.
- **Fix**: Implemented forward reconciliation migration `003_reconcile_schema.py` (down revision: `904d0b0ef2bb`) that brings an empty database upgraded solely via `alembic upgrade head` into 100% exact parity with SQLAlchemy ORM metadata in `app.db.models` (including all columns, nullability, constraints, foreign keys, and indexes).

### B. Append-Only Consent Enforcement at DB Level
- **Root Cause Removed**: `consent_audit` was vulnerable to direct SQL `UPDATE` and `DELETE` (and bulk ORM statements) bypassing application-level event listeners.
- **Fix**: Database triggers installed in `003_reconcile_schema`:
  - **SQLite**: `trg_consent_audit_no_update` and `trg_consent_audit_no_delete` calling `RAISE(ABORT, 'consent_audit is append-only: ... prohibited')`.
  - **PostgreSQL**: `prevent_consent_audit_modification()` trigger function and triggers on `BEFORE UPDATE OR DELETE`.

### C. Foreign Key Constraints & Retention Semantics
- **Root Cause Removed**: `documents`, `extracted_entities`, `interview_transcripts`, `summaries`, `red_flag_events`, `fhir_push_queue`, and `summary_resolutions` had unconstrained `session_id` columns (and mismatched column widths: `String(64)` vs `sessions.id String(36)`), allowing orphaned records and risking silent data loss.
- **Fix**: Added foreign key constraints referencing `sessions.id` (and `documents.id`) across all models and migrations with `RESTRICT` semantics. Replaced `String(64)` with `String(36)` to match parent primary keys.

### D. SQLite PRAGMA foreign_keys=ON Enforcement
- **Root Cause Removed**: SQLite connections silently ignored foreign key constraints by default.
- **Fix**: Added connection event listener in `app.db.database` and `migrations/env.py` executing `PRAGMA foreign_keys=ON` for every connection.

### E. Replacement of init_db Destructive DDL Patching
- **Root Cause Removed**: `init_db()` called `create_all()` and ran unconditional `ALTER TABLE` commands while catching and swallowing all exceptions, masking schema drift and reporting healthy on broken schemas.
- **Fix**: Replaced with `verify_schema_ready()`, which checks that `alembic_version` exists and matches `EXPECTED_ALEMBIC_HEAD` (`003_reconcile_schema`). If unmigrated, it raises `RuntimeError`. `main.py` records failure, logs `CRITICAL`, and `/health` returns HTTP 503 with `"status": "unhealthy"` and the exact schema error. For tests, explicit `init_db_for_testing()` is provided.

### F. Canonical Contracts & TypeScript Parity
- **Root Cause Removed**: Public schema models (`ExtractedEntity`, `SummaryField`, `RedFlagEvent`, `FHIRBundlePayload`) had field mismatches with ORM models (`id` vs `entity_id`, `type` vs `entity_type`, missing lifecycle fields, string sections). `vital_sign` was rejected by enums, and low-confidence suffixes were corrupting entity types.
- **Fix**:
  - Canonical enums: `EntityType`, `SummarySection`, `VerificationStatus`, `SessionStatus`, `DocumentStatus`, `RedFlagSeverity`, `InterviewMode`, `ConsentAction`, `WebSocketMessageType`.
  - `ExtractedEntity` strictly constrains `entity_type: EntityType` (rejecting invalid types with `ValidationError`), adds `verification: VerificationStatus = DOCUMENT_EXTRACTED`, supports both `id`/`entity_type`/`document_id` and legacy `entity_id`/`type`/`source_document_id`, normalizes `vital_sign` -> `vital`, and strips `_low_confidence` suffixes.
  - `SummarySource` now includes immutable `evidence_id` and `session_id` scoping.
  - `RedFlagEvent` supports both `id` and `event_id`, plus lifecycle fields (`is_acknowledged`, `acknowledged_by`, `action_taken`, `is_dismissed`).
  - Added `WebSocketEnvelope`, `FHIRExportRequest`, `FHIRExportResponse`, `FHIRPreviewResponse`, `ConsentActionItem`, `SessionStartResponse`.
  - Full TypeScript parity in `frontend/src/types/schemas.ts`.

---

## 2. Interfaces, Migrations & Operational Steps

### Migration Chain
```
001_initial_schema
 ├── 002_consent_audit_v2 (Dev 2) ────────┐
 └── bc12419f052b -> aac449da0deb (Dev 1) ┴──> af48eaaf9194 (Merge)
                                                └──> 904d0b0ef2bb
                                                      └──> 003_reconcile_schema (HEAD)
```

### Operational Instructions
- **Fresh deployments**:
  ```bash
  cd backend
  alembic upgrade head
  ```
- **Environment variables**:
  - `DATABASE_URL`: Primary database connection string (e.g. `sqlite+aiosqlite:///./medikiosk_dev.db` or PostgreSQL URI).
  - `ALEMBIC_DATABASE_URL`: Optional sync connection override for migrations.

### Data Recovery Limitations (Destructive Migration 002)
> [!WARNING]
> Historical databases that previously executed `002_consent_audit_v2` had `consent_type` dropped with a blanket `action='share_doctor'` default. Original consent purposes for records created prior to that migration cannot be mathematically or programmatically recovered; they must be restored from pre-migration database backups or re-consented by patients.

---

## 3. Validation Results

### Commands Run & Passing Tests
1. **Migration Integrity & Canonical Contracts Suite** (13 tests):
   ```bash
   pytest tests/test_migration_integrity.py -v
   ```
   - `test_empty_database_upgrades_to_head_matching_orm` PASSED
   - `test_migration_downgrade_and_reupgrade` PASSED (bidirectional migration verified)
   - `test_consent_audit_rejects_sql_update_and_delete` PASSED (triggers verified)
   - `test_sqlite_foreign_keys_reject_orphaned_records` PASSED (FK enforcement verified)
   - `test_sqlite_pragma_foreign_keys_is_enabled` PASSED
   - `test_verify_schema_ready_fails_on_unmigrated_db` PASSED (truthful startup error)
   - `test_canonical_enums_and_validation` PASSED
   - `test_extracted_entity_normalization_and_aliases` PASSED
   - `test_summary_source_immutable_evidence_id` PASSED
   - `test_red_flag_event_lifecycle_and_id_parity` PASSED
   - `test_websocket_envelope_discriminated_types` PASSED
   - `test_fhir_export_dtos` PASSED
   - `test_consent_action_item` PASSED

2. **Shared Schemas Suite** (7 tests):
   ```bash
   pytest tests/test_schemas.py -v
   ```
   - 7/7 PASSED

3. **System Diagnostic Suite**:
   ```bash
   pytest tests/test_gemini.py -v
   ```
   - 2/2 PASSED

4. **Frontend TypeScript & Components Suite**:
   ```bash
   npm test (in frontend/)
   ```
   - 8/8 PASSED

---

## 4. Constraints for Downstream Agents

1. **Assignment 2 (Auth, Consent & Privacy Lifecycle)**:
   - Must use `ConsentAction` enum (`share_doctor`, `store_abdm`, `anonymized_research`) for consent queries.
   - Any attempt to delete or alter a record in `consent_audit` will trigger a database exception. To revoke consent, append a new row with `granted=False`.
   - Do NOT blanket-cascade delete sessions; `RESTRICT` prevents deleting sessions with associated documents or summaries. Implement explicit archival or cleanup hooks.
   - On startup, `verify_schema_ready()` is called. In staging/production, run `alembic upgrade head` prior to app start.

2. **Assignment 3 (Interview & Emergency Safety)**:
   - Red flag events must populate `id` (or `event_id`), `session_id`, `trigger_phrase`, `matched_rule`, `severity` (`red` or `amber`), and `category`.
   - Use `WebSocketEnvelope` for all WebSocket communication.

3. **Assignment 4 (Documents, OCR & Labs)**:
   - When storing entities in `extracted_entities`, use canonical `entity_type: EntityType` (`diagnosis`, `medication`, `lab_value`, `allergy`, `procedure`, `vital`).
   - Do NOT suffix low-confidence strings to `entity_type`; use the `confidence: float` (0.0 to 1.0) and `verification` fields.
   - `created_at` is NOT NULL; rely on the server default or supply `datetime.now(UTC)`.
   - `session_id` and `document_id` must reference valid persisted parent records.

4. **Assignment 5 (Clinical Summaries & Contradiction Intelligence)**:
   - Use `SummarySection` enum values for summary field sections.
   - Ensure every `SummarySource` has an `evidence_id` and `session_id` populated for audit provenance.
   - Record conflict resolution choices in `summary_resolutions` table.

5. **Assignment 6 (FHIR & Export)**:
   - Use `FHIRExportRequest`, `FHIRExportResponse`, and `FHIRPreviewResponse` for export endpoints.
   - Do not conflate the ABDM export wrapper with raw FHIR bundles.

6. **Assignments 7 & 8 (Frontend & Clinician UI)**:
   - Import types from `frontend/src/types/schemas.ts`. All types are now strictly synchronized with backend models.

---

## 5. Remaining Items & Dependencies
- PostgreSQL deployment verification (trigger creation on live PostgreSQL instance requires live PG instance in Assignment 9).
- Assignment 2 must integrate the access-control and privacy lifecycle policy on top of these database tables and foreign keys.
