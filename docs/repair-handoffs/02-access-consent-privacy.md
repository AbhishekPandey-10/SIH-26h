# Assignment 2 — Authentication, Consent, Identity, and Privacy Lifecycle Handoff

**Status: COMPLETED AND VERIFIED**  
**Monorepo Baseline: Revision b3d619e + Assignment 1 Reconciliation**  
**Test Suite: `backend/tests/test_auth_consent_privacy.py` (10/10 PASS), All core suites (34/34 PASS)**

---

## Implemented

1. **Centralized Access Control & Identity Verification (`backend/app/dependencies.py`)**:
   - Implemented `AuthenticatedUser` model, `UserRole` enum (`staff`, `kiosk`, `admin`).
   - Unified token resolver supporting `Authorization: Bearer <token>`, `X-Staff-Token`, `X-Kiosk-Token`, `X-Session-Token`, and query parameters.
   - Enforced role gates: `require_authenticated_user` (401 on missing/invalid credentials), `require_staff` (403 on non-staff callers), `require_kiosk` (403 on non-kiosk/staff callers).
   - Enforced encounter scoping via `require_session_access` and `require_encounter_access`: session-bound kiosk tokens are strictly confined to their encounter UUID; cross-encounter access is rejected with HTTP 403 Forbidden.
   - Authenticated WebSocket handshake helper (`authenticate_websocket`) rejecting unauthorized sockets with close code 1008 (Policy Violation).

2. **Audit Identity Binding (Anti-Spoofing)**:
   - Fixed `POST /api/red-flag/{event_id}/dismiss` and `POST /api/red-flag/{event_id}/acknowledge`: staff identity (`dismissed_by`, `acknowledged_by`) is bound directly to the authenticated caller (`current_user.user_id`), ignoring spoofed parameters in request bodies.
   - Fixed `POST /api/summary/{session_id}/resolve/{field_id}`: physician identity (`doctor_id`) in `SummaryResolution` audit log is strictly bound to `current_user.user_id`.
   - Removed duplicate, unauthenticated red-flag routes from `backend/app/routes/interview.py`.

3. **ABDM Sandbox OTP & Profile Hardening (`backend/app/services/abdm.py`)**:
   - Removed runtime synthesis and fake demographic profile fabrication for arbitrary `@abdm` addresses. Non-existent identities now return clear errors (`ValueError("Patient identity ... not found in ABDM Sandbox")`).
   - Bound OTP generation to unique transaction IDs with 10-minute expiration.
   - Enforced a strict 3-attempt limit; on the 3rd failed attempt the transaction is locked out.
   - Prevented OTP replay attacks: consumed transactions are immediately invalidated (`consumed = True`).

4. **Append-Only Consent & Effective Derivation (`backend/app/routes/consent.py`)**:
   - Created dedicated `POST /api/consent` endpoint appending immutable records to `ConsentAudit`.
   - Implemented `GET /api/consent/{session_id}` returning deterministic effective consent states derived chronologically (latest append-only decision wins).
   - Implemented `POST /api/consent/revoke` to explicitly record patient revocations with `granted=False`.
   - Exported `check_effective_consent(session_id, action, db)` and `require_effective_consent(action)` gating clinical access (e.g. `share_doctor`, `store_abdm`).

5. **Encounter-End Lifecycle & Consent-Aware Privacy Wipe (`backend/app/services/session_manager.py`)**:
   - Implemented `session_manager.end_session(session_id, db)`:
     - **Idempotency**: Repeated calls return HTTP 200 with ended state without re-executing purge or raising errors.
     - **Consent-Aware Deletion**: If patient has not granted effective consent for `share_doctor`, deletes unconsented `InterviewTranscript`, `ExtractedEntityModel`, `ClinicalSummary`, `Document` (including unlink of storage files), and `FHIRPushQueue` records.
     - **Audit Anchor Preservation**: `Session` row (status `"wiped"`) and all `ConsentAudit` records are preserved as immutable proof of encounter and consent decision history.
     - **Transport Termination**: Closes active WebSockets registered for the session with normal closure code 1000.
     - **Process Cleanup**: Purges in-memory session caches and executes registered service lifecycle hooks (`register_cleanup_hook`).
   - Added `session_manager.assert_session_active(session_id, db)`: mutations on ended encounters raise `SessionEndedError` (HTTP 409 Conflict).

6. **Production Readiness Probe (`backend/app/main.py`)**:
   - Added `GET /ready` and `GET /api/ready` endpoints verifying:
     1. Database schema readiness against Alembic version.
     2. Insecure default prevention in production (`ENVIRONMENT=production` rejects `STAFF_API_KEY=dev_staff_secret`, `KIOSK_API_KEY=dev_kiosk_secret`, and `ALLOW_DEMO_OTP=True` with HTTP 503 Service Unavailable).

---

## Interfaces / Migrations

### 1. Configuration (`backend/app/config.py`)
```python
STAFF_API_KEY: str = "dev_staff_secret"
KIOSK_API_KEY: str = "dev_kiosk_secret"
JWT_SECRET: str = "dev_jwt_secret_change_in_production"
ALLOW_DEMO_OTP: bool = True  # Must be False in production
```

### 2. Dependency Injections (`backend/app/dependencies.py`)
```python
from app.dependencies import (
    AuthenticatedUser,
    UserRole,
    authenticate_websocket,
    check_effective_consent,
    require_authenticated_user,
    require_encounter_access,
    require_kiosk,
    require_session_access,
    require_staff,
)

# Route examples:
# Clinician action:
@router.post("/api/clinical/review")
async def review_endpoint(current_user: AuthenticatedUser = Depends(require_staff)):
    actor_id = current_user.user_id

# Scoped encounter access:
@router.get("/api/session/{session_id}/records")
async def get_records(
    session_id: str,
    current_user: AuthenticatedUser = Depends(require_encounter_access),
    db: AsyncSession = Depends(get_db),
):
    await check_effective_consent(session_id, "share_doctor", db)
```

### 3. Session Manager Lifecycle Hooks (`backend/app/services/session_manager.py`)
```python
from app.services.session_manager import session_manager

# Register a service cleanup hook (called on encounter end)
async def cleanup_my_service(session_id: str) -> None:
    # Clear process memory, buffers, or temporary files
    my_cache.pop(session_id, None)

session_manager.register_cleanup_hook(cleanup_my_service)
```

### 4. Permission Matrix

| Endpoint | Method | Role Required | Encounter Scoped? | Consent Check |
|---|---|---|---|---|
| `/api/session/start` | POST | Kiosk, Staff | No | None |
| `/api/session/{id}/configure` | POST | Kiosk (matching ID), Staff | Yes | Active Session Guard (409) |
| `/api/session/{id}/status` | GET | Kiosk (matching ID), Staff | Yes | None |
| `/api/session/{id}/fhir` | GET | Kiosk (matching ID), Staff | Yes | `share_doctor` (403) |
| `/api/session/end` | POST | Kiosk (matching ID), Staff | Yes | Idempotent end & purge |
| `/api/consent` | POST | Kiosk (matching ID), Staff | Yes | Active Session Guard (409) |
| `/api/consent/{id}` | GET | Kiosk (matching ID), Staff | Yes | None |
| `/api/consent/revoke` | POST | Kiosk (matching ID), Staff | Yes | Active Session Guard (409) |
| `/api/red-flag/{id}/dismiss` | POST | Staff Only | No | Identity Bound to Caller |
| `/api/red-flag/{id}/acknowledge`| POST | Staff Only | No | Identity Bound to Caller |
| `/ws/staff-alerts` | WS | Staff Only | No | Token Authenticated |
| `/api/summary/{id}` | GET | Kiosk (matching ID), Staff | Yes | `share_doctor` (403) |
| `/api/summary/{id}/field/{fid}` | PUT | Staff Only | No | Identity Bound to Caller |
| `/api/summary/{id}/resolve/{fid}`| POST | Staff Only | No | Identity Bound to Caller |
| `/ready` | GET | Public | No | Schema & Config Readiness |

---

## Validation

All tests executed with Python 3.12.11 in virtual environment (`W:\SIH\Proj\backend\.venv\Scripts\pytest.exe`).

### 1. Dedicated Assignment 2 Test Suite (`test_auth_consent_privacy.py`)
Command:
```powershell
& "w:\SIH\Proj\backend\.venv\Scripts\pytest.exe" tests/test_auth_consent_privacy.py -v
```
Output:
```text
tests/test_auth_consent_privacy.py::test_unauthenticated_access_rejected_across_protected_endpoints PASSED [ 10%]
tests/test_auth_consent_privacy.py::test_kiosk_role_cannot_perform_clinician_actions PASSED [ 20%]
tests/test_auth_consent_privacy.py::test_cross_session_isolation_denies_unauthorized_encounters PASSED [ 30%]
tests/test_auth_consent_privacy.py::test_staff_audit_identity_binding_cannot_be_spoofed PASSED [ 40%]
tests/test_auth_consent_privacy.py::test_otp_security_lifecycle_attempts_expiry_replay PASSED [ 50%]
tests/test_auth_consent_privacy.py::test_consent_append_only_effective_derivation_and_revocation PASSED [ 60%]
tests/test_auth_consent_privacy.py::test_idempotent_encounter_end_purges_unconsented_data PASSED [ 70%]
tests/test_auth_consent_privacy.py::test_consented_encounter_preserves_clinical_records_on_end PASSED [ 80%]
tests/test_auth_consent_privacy.py::test_mutations_on_ended_session_rejected_with_409 PASSED [ 90%]
tests/test_auth_consent_privacy.py::test_readiness_probe_detects_insecure_production_defaults PASSED [100%]
======================== 10 passed in 0.75s ========================
```

### 2. Comprehensive Core Suite Verification
Command:
```powershell
& "w:\SIH\Proj\backend\.venv\Scripts\pytest.exe" tests/test_migration_integrity.py tests/test_schemas.py tests/test_session.py tests/test_auth_consent_privacy.py -v
```
Output:
```text
======================= 34 passed, 7 warnings in 2.65s ========================
```

---

## Remaining Dependencies for Downstream Assignments

1. **Assignment 3 (Interview State Machine, Safety & Sockets)**:
   - Must authenticate WebSocket connections to `/ws/interview` with `authenticate_websocket(websocket, session_id=session_id)`.
   - Must register active interview WebSockets with `session_manager.register_websocket(session_id, ws)`.
   - Must check `session_manager.assert_session_active(session_id, db)` before accepting patient answer mutations.
   - Register cleanup hook via `session_manager.register_cleanup_hook` to discard pending turn buffers when session ends.

2. **Assignment 4 (Document Ingestion & OCR)**:
   - Must enforce `require_encounter_access` on document upload and crop streaming endpoints.
   - Must register crop cache cleanup with `session_manager.register_cleanup_hook`.

3. **Assignment 5 (Clinical Summary & Export)**:
   - Re-check effective consent for `store_abdm` or `share_doctor` immediately before triggering ABDM FHIR export dispatch.

4. **Frontend Integration**:
   - Touchscreen kiosk PWA must store `session_token` returned by `/api/session/start` and supply `Authorization: Bearer session_<uuid>` on subsequent encounter API calls and WebSocket connections.
   - Triage nurse / staff dashboards must authenticate with `Authorization: Bearer <STAFF_API_KEY>` or staff token.
