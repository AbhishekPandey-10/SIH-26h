# Assignment 4 — Document Ingestion, OCR Evidence, Lab Values, and Dates Handoff

**Status: COMPLETED AND VERIFIED**  
**Monorepo Baseline: Revision b3d619e + Assignments 1, 2, & 3 Reconciliation**  
**Test Suites: `backend/tests/test_document_ocr_labs.py` (38/38 PASS), `backend/tests/test_document_pipeline.py` (7/7 PASS), `backend/tests/test_documents.py` (3/3 PASS), Full Core Suite (91/91 PASS)**

---

## Implemented Outcomes & Root Causes Removed

1. **Zero Runtime Fabrication Across Entire Pipeline**:
   - **Failed/Empty OCR**: Removed `_fallback_extract_entities` entirely. When Gemini OCR fails or returns empty entities, zero clinical facts are invented. Document status is set to `"extracted"` with 0 entities, or `"error"` if an exception occurred.
   - **Empty Entities Endpoint**: `GET /api/documents/entities/{session_id}` returns empty list `[]` with count 0 when no documents exist; removed hardcoded sample prescription injection.
   - **Missing Documents & Crops**: `GET /api/documents/{doc_id}/crop` and `GET /api/documents/{doc_id}/image` return explicit HTTP 404 Not Found when a source file or document does not exist. `crop_service.crop_document()` raises `FileNotFoundError` rather than synthesizing a blank canvas image.
   - **ABDM Patient Fetch**: `POST /api/abdm/fetch-records` verifies an active encounter, enforces `check_effective_consent("store_abdm")`, and restricts retrieval strictly to the authenticated `SANDBOX_PATIENTS` registry (`rajesh.kumar@abdm`). Arbitrary or unrecognized ABHA IDs return truthful HTTP 404 Not Found rather than injecting hardcoded fake records.
   - **Downstream Deltas & Contradictions**: Removed hardcoded historical entity injection (`ent_hist_01`, `ent_hist_02`, `ent_hist_03`) and unconditional fallback modifications in `contradiction_detector.py`. When patient input is empty or lacks evidence, zero Amlodipine/Metformin/Glimepiride deltas are invented. Removed fabricated demonstration items in `visualization_service.get_what_changed()`.

2. **Shared Structured Lab Quantity Parser (`backend/app/services/lab_parser.py`)**:
   - Implemented `StructuredLabParser` and `ParsedLabQuantity` dataclass with discrete fields: `test_key`, `test_name`, `numeric_value`, `effective_value`, `comparator`, `unit`, `multiplier`, `raw_text`, and `status`.
   - **Test-Name Digit Collision Defense**: Isolates test names and digit markers before numeric evaluation (e.g. `HbA1c: 7.1%` yields `numeric_value = 7.1`, not `1.0`; `CA-125: 18.5 U/mL` yields `18.5`).
   - **Multiplier Handling**: Parses Indian and international multiplier expressions (`Lakhs`, `Lakh`, `K`, `Thousand`, `Million`). `Platelets 1.8 Lakhs /cumm` accurately evaluates to `effective_value = 180,000.0`, not `1.8`.
   - **Comparator Preservation**: Preserves `<` and `>` comparators (`< 5.7 %`, `> 140 mg/dL`) rather than stripping them and misrepresenting values as exact readings.
   - **Unit Normalization**: Standardizes clinical lab units (`/cumm`, `g/dL`, `mg/dL`, `U/L`, `%`, `mmol/L`, `pg/mL`, `cells/uL`).

3. **Demographic & Clinical Lab Flagging (`backend/app/services/lab_flagging.py`)**:
   - Integrated `StructuredLabParser` into `LabFlagger`.
   - **Demographic Reference Ranges**: Evaluates ranges according to patient gender (`female` Hemoglobin 12.0 - 15.5 g/dL vs `male` 13.0 - 17.0 g/dL; Creatinine female 0.5 - 1.1 mg/dL vs male 0.7 - 1.3 mg/dL).
   - **Unit Mismatch Defense**: When extracted unit conflicts with expected reference unit without a safe constant conversion (e.g., Hemoglobin in `mmol/L` vs expected `g/dL`), flags `is_abnormal = None` (unverified) with an explicit explanatory note, refusing to guess.
   - **Missing Unit Defense**: Measurements lacking required units are marked `status = "unverified"`.
   - **Comparator Handling**: Correctly evaluates `<` and `>` boundaries against thresholds.

4. **Strict Calendar Date Normalization (`normalize_indian_date` in `document_processor.py`)**:
   - Enforces day-first parsing (`DD/MM/YYYY`, `DD-MM-YYYY`, `DD.MM.YYYY`).
   - Strict calendar validation via `datetime.date`:
     - Valid leap year: `29/02/2024` -> `2024-02-29`
     - Invalid leap day: `29/02/2023` -> `None`
     - Century rule: `29-02-2000` -> `2000-02-29`, `29-02-1900` -> `None`
     - Invalid months/days (`31/04/2024`, `15/13/2024`, `32/01/2024`) -> `None`
   - Preserves source indicator `"Unknown"` / `"Date unknown"`.
   - Formats date-only outputs strictly as `YYYY-MM-DD` without UTC timezone shifting.

5. **Upload & Path Containment Hardening (`backend/app/routes/documents.py`)**:
   - Requires an active kiosk encounter validated by `session_manager.assert_session_active()`.
   - Sanitizes `session_id` using regex `^[a-zA-Z0-9_\-]+$` and verifies containment with `upload_dir.is_relative_to(upload_root)`, strictly rejecting `../` traversal attempts with HTTP 400 Bad Request.
   - Enforces 10 MB maximum upload size (`HTTP 413 Payload Too Large`).
   - Whitelists image/document MIME types and extensions (`.jpg`, `.jpeg`, `.png`, `.webp`, `.pdf`), rejecting executable or foreign uploads with `HTTP 415 Unsupported Media Type`.

6. **Transactional Idempotency & Partial Failure Rollback**:
   - Re-running OCR extraction on an existing document atomically deletes previously saved entities for that `document_id` before inserting new entities, preventing duplication across retries.
   - Partial processing exceptions roll back pending entity writes and persist an explicit `status = "error"` on the `Document` record in a clean, isolated transaction.

7. **Canonical `ExtractedEntity` Model Validation (`backend/app/shared/schemas.py`)**:
   - Added `@field_validator("bounding_box")` ensuring bounding boxes are either `None` or exactly 4 finite floats in `[0.0, 1.0]`.
   - Canonicalizes `vital_sign` -> `vital`.
   - Preserves low-confidence evidence under its true `entity_type` (e.g. `type = "medication"`, `confidence = 0.42`), eliminating mutation into `medication:needs_confirmation`.
   - Unknown coordinates remain `None` instead of fabricating default coordinates.

8. **Crop Service Hardening & Lifecycle Hook (`backend/app/services/crop_service.py`)**:
   - Validates normalized bounding box coordinates (`0.0 <= x <= 1.0`, `0.0 <= y <= 1.0`, `w > 0`, `h > 0`, `x + w <= 1.05`, `y + h <= 1.05`), raising `ValueError` on violations.
   - Implemented `clear_cache(session_id)` and registered a teardown hook with `session_manager` so encounter termination purges cached crops from memory.

9. **Scan Progress & Status Recovery (`GET /api/documents/{doc_id}/status`)**:
   - Exposes REST recovery endpoint so reconnecting clients can query the persisted document status (`uploaded`, `processing`, `extracted`, `error`), entity count, and page number without relying solely on transient WebSocket events.

---

## Interfaces & Contracts for Downstream Agents

### 1. Canonical Extracted Entity Schema
Declared in `backend/app/shared/schemas.py` and `shared/schemas/__init__.py`:
```python
class ExtractedEntity(BaseModel):
    id: str = Field(default_factory=lambda: f"ent_{uuid.uuid4().hex[:12]}")
    document_id: Optional[str] = None
    session_id: Optional[str] = None
    type: EntityType  # 'medication', 'diagnosis', 'allergy', 'vital', 'lab_result', 'procedure', 'immunization', 'lifestyle'
    value: str
    generic_name: Optional[str] = None
    date: Optional[str] = None  # Normalized 'YYYY-MM-DD' or None / 'Unknown'
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    bounding_box: Optional[List[float]] = None  # Exactly [x, y, w, h] in [0.0, 1.0] or None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    is_abnormal: Optional[bool] = None  # True (abnormal), False (normal), None (unverified / mismatch)
    source: Optional[str] = None
    created_at: Optional[datetime] = None
```

### 2. Structured Lab Parser API (`lab_parser`)
Import: `from app.services.lab_parser import lab_parser, ParsedLabQuantity, ParseStatus`
```python
parsed = lab_parser.parse_quantity(
    text="Platelets 1.8 Lakhs /cumm",
    test_name_hint="Platelet Count",
    explicit_unit=None
)

# Attributes:
parsed.test_key         # "platelets"
parsed.test_name        # "Platelets"
parsed.numeric_value    # 1.8 (extracted number)
parsed.multiplier       # 100000.0 (multiplier factor)
parsed.effective_value  # 180000.0 (evaluated numeric quantity)
parsed.comparator       # None, "<", "<=", ">", ">=", "="
parsed.unit             # "/cumm"
parsed.status           # ParseStatus.OK ("verified"), "unverified", "cannot_verify"
```

### 3. Lab Flagger Demographic Evaluation
Import: `from app.services.lab_flagging import lab_flagger`
```python
is_abnormal, ref_range = lab_flagger.evaluate_lab_value(
    test_name="Hemoglobin",
    value_str="12.5 g/dL",
    unit="g/dL",
    gender="male"  # "male" or "female"
)
# Returns: (True, "13.0 - 17.0 g/dL")
```

### 4. Document Status Recovery Endpoint
`GET /api/documents/{doc_id}/status`  
Response:
```json
{
  "document_id": "doc_12345678",
  "session_id": "sess_87654321",
  "status": "extracted",
  "entity_count": 4,
  "page_number": 1,
  "file_type": "prescription"
}
```

### 5. Extraction Revision & Idempotency Policy
- Reprocessing `POST /api/documents/process/{doc_id}` replaces all prior `ExtractedEntityModel` rows linked to `document_id`.
- If vision extraction raises an exception, prior entities are rolled back, and the document is updated to `status = "error"`.
- Entity count returned to clients matches the exact active rows in the database.

---

## Validation & Test Results

### Test Execution Commands
```powershell
# Run Assignment 4 dedicated regression suite (38 tests)
.venv\Scripts\pytest.exe tests\test_document_ocr_labs.py --show-capture=no

# Run all core regression suites (91 tests)
.venv\Scripts\pytest.exe tests\test_document_ocr_labs.py tests\test_document_pipeline.py tests\test_documents.py tests\test_auth_consent_privacy.py tests\test_migration_integrity.py tests\test_interview_safety.py tests\test_red_flag_escalation.py tests\test_session.py --show-capture=no
```

### Results Summary
- `tests/test_document_ocr_labs.py`: **38 passed in 2.37s**
- `tests/test_document_pipeline.py`: **7 passed**
- `tests/test_documents.py`: **3 passed**
- `tests/test_auth_consent_privacy.py`: **10 passed**
- `tests/test_migration_integrity.py`: **13 passed**
- `tests/test_interview_safety.py`: **11 passed**
- `tests/test_red_flag_escalation.py`: **5 passed**
- `tests/test_session.py`: **4 passed**
- **Total: 91 passed, 0 failures, 0 errors.**

### Negative & Security Cases Exercised
1. **Path Traversal Defense**: Session ID `../traversal/escape` rejected with HTTP 400.
2. **Oversized Upload Defense**: Files > 10MB rejected with HTTP 413.
3. **MIME Whitelist**: `.exe` or disallowed content-type rejected with HTTP 415.
4. **Missing Source Image**: Requests for missing document or crop return truthful HTTP 404, never synthesized fallback canvases.
5. **ABDM Unauthorized Fetch**: Missing `store_abdm` consent returns HTTP 403; unknown ABHA ID returns HTTP 404.
6. **Unit Mismatch Defense**: Hemoglobin given in `mmol/L` flags `is_abnormal = None` (cannot verify).
7. **Calendar Dates**: Non-existent leap day `29/02/2023` and invalid months `15/13/2024` return `None`.
8. **Reprocessing Idempotency**: Running OCR twice on the same document replaces old entities rather than doubling them in the database.

---

## Remaining Dependencies & Limitations

1. **Live Gemini Multimodal OCR Verification**:
   - Offline tests execute using deterministic mocked vision payloads and error injectors.
   - Live external OCR requires a funded Google Cloud API key (`GEMINI_API_KEY`) configured in deployment. When not present, the system fails truthfully with `RuntimeError` rather than fabricating clinical facts.
2. **Live ABDM Sandbox Connectivity**:
   - ABDM integration currently verifies against `SANDBOX_PATIENTS` in sandbox mode. Connecting to the national ABDM gateway requires live client credentials (`ABDM_CLIENT_ID`, `ABDM_CLIENT_SECRET`) and signed consent tokens from the central gateway.
3. **Browser / DevTools Verification**:
   - Backend APIs and endpoints are verified via `pytest` and `TestClient`. Full end-to-end mounted browser testing on kiosk hardware remains pending on final UI bundle staging.
