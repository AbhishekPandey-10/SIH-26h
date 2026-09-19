# Assignment 3 — Interview State Machine, Emergency Safety, and Clarification Delivery Handoff

**Status: COMPLETED AND VERIFIED**  
**Monorepo Baseline: Revision b3d619e + Assignment 1 & 2 Reconciliation**  
**Test Suite: `backend/tests/test_interview_safety.py` (11/11 PASS), Full Regression Suite (54/54 PASS)**

---

## Implemented

1. **Unified Application-Level Answer Submission Pipeline (`backend/app/routes/interview.py`)**:
   - Implemented canonical `submit_interview_answer(session_id, answer, db, is_proxy, proxy_name, proxy_relationship)` used identically across:
     - WebSocket (`/ws/interview`)
     - REST step (`POST /api/interview/step`)
     - Ask-back clarification replies (`POST /api/interview/ask-back/reply`)
     - Patient unvoiced concerns (`POST /api/patient/unvoiced-concern`)
   - Enforces encounter lifecycle guard (`SessionEndedError` / HTTP 409 / WS 1008 if session is ended, wiped, or completed).
   - Idempotency guard: duplicate submissions with matching question ID and identical answer text return the existing question state without advancing the state machine or duplicating records.
   - Durable outbox pattern: persists `RedFlagEventModel` and `InterviewTranscript` to database within an atomic transaction *before* dispatching websocket pause or broadcasting staff alert.

2. **Contextual Emergency Safety & Multi-Rule Determinism (`backend/app/services/red_flag_detector.py`)**:
   - Evaluates patient answer text combined with preceding question context (`question_context`).
   - Contextual affirmative detection: positive answers ("Yes", "हाँ", "Haan", "जी हाँ", "sometimes", etc.) to safety/psychiatric screening questions trigger immediate emergency red flags without requiring the patient to repeat danger keywords.
   - Multi-rule scanning: scans all matching rules and aggregates deterministically by highest severity (`RED > AMBER`), followed by most specific matched phrase length.
   - Built-in clinical fallback rule set: ensures `triggers` is never empty even if `red_flags.json` is missing or corrupt, setting `is_degraded = True`.
   - Exposed `safety_degraded` in `/health` and `/ready` probes (`backend/app/main.py`), preventing production startup on degraded safety rules.

3. **Strict Typed LLM Confirmation with Fail-Safe Preservation (`backend/app/services/question_generator.py`)**:
   - Hardened `confirm_red_flag_emergency`:
     - Parses boolean values strictly: checks for boolean types and explicitly compares normalized strings (`"true"`, `"1"` vs `"false"`, `"0"`), preventing string `"false"` from ever being treated as truthy.
     - Fail-safe candidate preservation: any parse failure, malformed JSON, missing fields, low confidence (< 0.80), API timeout, or unconfigured LLM client unconditionally preserves the candidate emergency hold (`audit_status` indicating fail-safe mode).

4. **Multi-Alert Session Lifecycle & Staff Console Replay (`backend/app/routes/red_flag.py`)**:
   - Multi-alert dismissal tracking: `POST /api/red-flag/{event_id}/dismiss` counts remaining undismissed alerts for the session (`remaining_active_alerts`). The kiosk is only resumed if 0 active alerts remain.
   - Acknowledgment without release: `POST /api/red-flag/{event_id}/acknowledge` records staff triage and audit trails while strictly preserving the emergency hold.
   - Replay on reconnect: staff connecting to `/ws/staff-alerts` receives all active, undismissed alerts replayed from database (`is_replay = True`), ensuring alerts during network disconnects are never lost.
   - Idempotent dismissals and acknowledgments.
   - Direct staff identity binding (`dismissed_by`, `acknowledged_by` bound to authenticated `current_user.user_id`).

5. **Socket Lifecycle & Reconnect State Restoration (`backend/app/routes/interview.py`)**:
   - Instance-safe connection tracking: `ConnectionManager.disconnect(session_id, websocket)` only removes the connection if the disconnecting socket matches the active socket instance, preventing a disconnected stale socket from evicting a newly reconnected replacement.
   - State restoration on reconnect: connecting to `/ws/interview` checks active state in `interview_engine.sessions`. If state exists, re-dispatches the current question (or pause reassurance if on emergency hold) instead of restarting intake or re-prompting chief complaint.
   - Canonical `WebSocketEnvelope` dispatching with payload flattening for dual client backward compatibility.

6. **Canonical Smart Recall Service (`backend/app/services/smart_recall.py`)**:
   - Historical entity selection ordered by recency (`created_at.desc()`).
   - Strict confidence tiering:
     - `< 0.5`: Ordinary question (default question returned unchanged).
     - `0.5 <= conf <= 0.8`: Verification question ("Our hospital records mention... Could you please verify?").
     - `> 0.8`: Confirmation question ("Your records show you take... is that still current?").
   - Normalized context shape: `{entity_id, type, entity_type, value, confidence, bounding_box, created_at}`.
   - Unified `node_pmh` and `node_medications` in `interview_engine.py` to delegate directly to `smart_recall_service.adapt_question_with_recall`.
   - Strict 404 response on `GET /api/interview/transcript/{id}` for missing transcripts (zero synthetic evidence).

7. **Durable Physician Ask-Back Workflow (`backend/app/routes/interview.py`)**:
   - `POST /api/interview/ask-back`: if patient has not answered, preserves pending state (`needs_confirmation`) with zero fabricated clinical findings or synthetic transcripts.
   - `POST /api/interview/ask-back/reply`: receives patient response from kiosk, routes reply through red-flag safety scanning, and appends a genuine `InterviewTranscript` turn.

8. **Patient Unvoiced Concern Safety Flow (`backend/app/routes/patient.py`)**:
   - `POST /api/patient/unvoiced-concern`: routes patient statements through contextual safety evaluation. Danger phrases trigger emergency pause, persist `RedFlagEventModel`, and broadcast staff alerts.

9. **Non-Blocking Async Gemini Retry (`backend/app/services/gemini_retry.py`)**:
   - Wraps sync Gemini calls in `asyncio.to_thread` with bounded 15-second timeouts in `gemini_call_with_retry_async`, avoiding event loop blockage.

---

## Interfaces / Migrations

### 1. Unified Answer Submission
```python
from app.routes.interview import submit_interview_answer
from shared.schemas import InterviewAnswer, NextQuestion

next_q, red_flag_ev = await submit_interview_answer(
    session_id=session_id,
    answer=InterviewAnswer(
        question_id="q_cc_01",
        answer_text="I have severe chest pain with breathlessness",
        language="hi",
    ),
    db=db,
    is_proxy=False,
)
```

### 2. Smart Recall Question Adaptation
```python
from app.services.smart_recall import smart_recall_service
from shared.schemas import NextQuestion

adapted_q: NextQuestion = smart_recall_service.adapt_question_with_recall(
    section="medications",
    default_question=default_q,
    extracted_context=patient_extracted_context,
    language="hi",
)
```

### 3. Red Flag Safety Scan
```python
from app.services.red_flag_detector import red_flag_detector
from shared.schemas import RedFlagEvent

red_flag: RedFlagEvent | None = red_flag_detector.scan_and_confirm(
    text="हाँ, बहुत ज्यादा",
    session_id=session_id,
    question_context="क्या आपके मन में खुद को नुकसान पहुँचाने का विचार आया है?",
)
```

### 4. Staff Replay & Override Endpoints
- `GET /ws/staff-alerts?token=<staff_token>`: connects staff dashboard, replays active undismissed alerts.
- `POST /api/red-flag/{event_id}/dismiss`: dismisses alert; returns `{"remaining_active_alerts": int, "resumed": bool}`.
- `POST /api/red-flag/{event_id}/acknowledge`: records emergency triage acknowledge; keeps kiosk on hold.
- `POST /api/interview/ask-back/reply`: submits patient answer to physician clarification query.

---

## Preserved Assumptions / Deviations

1. **Dual WebSocket Compatibility**:
   Modern clients expect canonical typed envelopes (`type`, `session_id`, `payload`), while legacy frontends/tests read flat keys (`event`, `is_paused`, `section`, `text`) directly on the root JSON object. `send_ws_envelope` flattens payload attributes to the top level while maintaining full typed `WebSocketEnvelope` structure.
2. **Deterministic Fallback over Unconfigured LLM**:
   In test and offline environments without live Gemini credentials, `confirm_red_flag_emergency` preserves emergency candidate holds with `audit_status="fail_safe_rule_match"` or `"fail_safe_unconfigured"`, guaranteeing safety is never bypassed when external services are unavailable.
3. **Session Row Auto-Creation for Direct WebSocket Connections**:
   Direct connections to `/ws/interview?session_id=...` verify encounter status; if active session row does not yet exist, creates a clean active session to satisfy referential integrity for subsequent `RedFlagEventModel` and `InterviewTranscript` foreign keys.

---

## Verification / Acceptance Evidence

### Test Execution Results
All 54 tests across all assignment areas passed cleanly:
```bash
pytest -v tests/test_interview_safety.py \
          tests/test_red_flag_escalation.py \
          tests/test_interview.py \
          tests/test_red_flag.py \
          tests/test_smart_recall.py \
          tests/test_migration_integrity.py \
          tests/test_auth_consent_privacy.py
```

Results summary:
- `tests/test_interview_safety.py`: **11/11 PASS**
  - a. REST and WS produce equivalent safety transitions & DB outbox records.
  - b. Socket failure during pause leaves durable alert in DB and staff alert dispatched.
  - c. Reconnecting staff receives active unresolved alerts replay.
  - d. Strict typed confirmation fail-safe modes (malformed JSON, missing fields, string booleans, timeout, unconfigured client).
  - e. Contextual affirmative to safety questions & deterministic multi-rule severity (RED > AMBER).
  - f. Multi-alert dismissal lifecycle: encounter resumes only when 0 alerts remain; idempotent dismissals/acknowledgments.
  - g. Ended session mutations rejected with 409 / WS 1008.
  - h. Reconnected second socket survives cleanup of old socket.
  - i. Smart recall confidence tiers at exact boundaries (0.4999, 0.5, 0.8, 0.8001); 404 on missing citations.
  - j. Ask-back without reply yields pending state with no fabricated transcripts; reply scans for safety.
  - k. Unvoiced concerns trigger emergency safety flow.
- `tests/test_red_flag_escalation.py`: **5/5 PASS**
- `tests/test_smart_recall.py`: **4/4 PASS**
- `tests/test_interview.py`: **8/8 PASS**
- `tests/test_red_flag.py`: **3/3 PASS**
- `tests/test_migration_integrity.py`: **13/13 PASS**
- `tests/test_auth_consent_privacy.py`: **10/10 PASS**

**Total: 54 passed in 6.88s.**

---

## Next Handoff Notes

Assignment 4 (Document OCR, FHIR R4 Generation, and Clinical Summaries) can rely on:
1. Canonical `RedFlagEventModel` records for summary emergency banners.
2. Verified provenance citations (`InterviewTranscript` IDs and `ExtractedEntityModel` IDs) guaranteed free of synthetic fabrication.
3. Effective consent checking via `check_effective_consent(session_id, "share_doctor", db)` before clinical summary generation and FHIR bundle construction.
4. Active encounter guards via `session_manager.assert_session_active(session_id, db)` before accepting document uploads or summary revisions.
