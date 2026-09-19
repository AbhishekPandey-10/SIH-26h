"""
Comprehensive Regression Test Suite for Assignment 4:
Document Ingestion, OCR Evidence, Lab Values, and Dates
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Audited behaviors verified:
1. Zero runtime fabrication: empty OCR, missing docs, missing crops, unknown ABHA IDs
2. StructuredLabParser isolates digits in test names (HbA1c 7.1% -> 7.1, not 1.0)
3. Multipliers handled accurately (Platelets 1.8 Lakhs /cumm -> 180,000, not 1.8)
4. Unit mismatch defense (Hemoglobin 8.5 mmol/L -> unverified is_abnormal = None)
5. Demographic reference ranges (male vs female)
6. Calendar date validation (DD/MM/YYYY, leap days, invalid calendar dates rejected)
7. Security: path traversal rejection, 10MB size limit, MIME whitelist
8. Transactional idempotency & atomic rollback on OCR errors
9. CropService coordinate bounds validation & truthful 404/FileNotFoundError
10. Downstream lab explanation & visualization zero-fabrication
"""

import io
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from sqlalchemy import select
from app.config import settings
from app.db.database import async_session_factory
from app.db.models import Document, ExtractedEntityModel as DBLabEntity, Session as DBSession
from app.services.crop_service import crop_service
from app.services.document_processor import document_processor, normalize_indian_date
from app.services.lab_flagging import lab_flagger
from app.services.lab_parser import lab_parser, ParseStatus
from app.shared.schemas import ExtractedEntity, EntityType
from app.services.visualization_service import visualization_service
from app.services.contradiction_detector import contradiction_detector


# ==============================================================================
# 1. Date Normalization Tests
# ==============================================================================

class TestDateNormalization:
    """Verify strict calendar date normalization under explicit day-first rules."""

    def test_day_first_valid_formats(self):
        assert normalize_indian_date("15/03/2024") == "2024-03-15"
        assert normalize_indian_date("05-06-2023") == "2023-06-05"
        assert normalize_indian_date("15.03.2024") == "2024-03-15"
        assert normalize_indian_date("2024-03-15") == "2024-03-15"

    def test_leap_year_handling(self):
        # 2024 is a leap year -> valid
        assert normalize_indian_date("29/02/2024") == "2024-02-29"
        # 2023 is not a leap year -> invalid, must return None
        assert normalize_indian_date("29/02/2023") is None
        # 2000 is a leap year (divisible by 400)
        assert normalize_indian_date("29-02-2000") == "2000-02-29"
        # 1900 is not a leap year (divisible by 100 but not 400)
        assert normalize_indian_date("29-02-1900") is None

    def test_invalid_calendar_dates_rejected(self):
        # 31st of April (April has 30 days)
        assert normalize_indian_date("31/04/2024") is None
        # 31st of June (June has 30 days)
        assert normalize_indian_date("31/06/2024") is None
        # Month 13
        assert normalize_indian_date("15/13/2024") is None
        # Day 32
        assert normalize_indian_date("32/01/2024") is None
        # Day 00
        assert normalize_indian_date("00/05/2024") is None
        # Non-numeric garbage
        assert normalize_indian_date("99/99/9999") is None
        assert normalize_indian_date("invalid-date") is None
        assert normalize_indian_date(None) is None

    def test_preserves_unknown_indicators(self):
        assert normalize_indian_date("Unknown") == "Unknown"
        assert normalize_indian_date("Date unknown") == "Date unknown"


# ==============================================================================
# 2. Structured Lab Parser Tests
# ==============================================================================

class TestStructuredLabParser:
    """Verify test-name isolation, multipliers, comparators, and parse status."""

    def test_hba1c_separates_name_digits_from_value(self):
        # HbA1c: 7.1% must parse 7.1, NOT 1
        res = lab_parser.parse_quantity("HbA1c: 7.1%", test_name_hint="HbA1c")
        assert res.numeric_value == 7.1
        assert res.unit == "%"
        assert res.comparator is None
        assert res.status == ParseStatus.OK

        res2 = lab_parser.parse_quantity("HbA1c 5.4 %")
        assert res2.numeric_value == 5.4
        assert res2.unit == "%"

    def test_other_tests_with_embedded_digits(self):
        res_ca125 = lab_parser.parse_quantity("CA-125: 18.5 U/mL", test_name_hint="CA-125")
        assert res_ca125.numeric_value == 18.5

        res_b12 = lab_parser.parse_quantity("Vitamin B12: 240 pg/mL", test_name_hint="Vitamin B12")
        assert res_b12.numeric_value == 240.0
        assert res_b12.unit == "pg/mL"

        res_cd4 = lab_parser.parse_quantity("CD4 Count: 450 cells/uL", test_name_hint="CD4")
        assert res_cd4.numeric_value == 450.0

    def test_platelet_lakhs_multiplier(self):
        # Platelets 1.8 Lakhs /cumm -> effective value 180,000 /cumm, NOT 1.8
        res = lab_parser.parse_quantity("Platelets 1.8 Lakhs /cumm")
        assert res.numeric_value == 1.8
        assert res.multiplier == 100000.0
        assert res.effective_value == 180000.0
        assert res.unit == "/cumm"
        assert res.status == ParseStatus.OK

        res_singular = lab_parser.parse_quantity("Platelet Count: 2.5 Lakh /cumm")
        assert res_singular.numeric_value == 2.5
        assert res_singular.multiplier == 100000.0
        assert res_singular.effective_value == 250000.0

    def test_thousands_multiplier(self):
        res_k = lab_parser.parse_quantity("WBC 7.5 K/uL")
        assert res_k.numeric_value == 7.5
        assert res_k.multiplier == 1000.0
        assert res_k.effective_value == 7500.0

    def test_comparators_preserved(self):
        res_lt = lab_parser.parse_quantity("< 5.7 %")
        assert res_lt.comparator == "<"
        assert res_lt.numeric_value == 5.7

        res_gte = lab_parser.parse_quantity(">= 6.5 %")
        assert res_gte.comparator == ">="
        assert res_gte.numeric_value == 6.5

        res_gt = lab_parser.parse_quantity("> 140 mg/dL")
        assert res_gt.comparator == ">"
        assert res_gt.numeric_value == 140.0

    def test_cannot_verify_non_numeric_values(self):
        res = lab_parser.parse_quantity("Negative")
        assert res.numeric_value is None
        assert res.status == ParseStatus.CANNOT_VERIFY

        res_empty = lab_parser.parse_quantity("")
        assert res_empty.status == ParseStatus.EMPTY


# ==============================================================================
# 3. Lab Flagging and Demographic Applicability Tests
# ==============================================================================

class TestLabFlagging:
    """Verify lab flagging with demographic ranges, unit mismatch defense, and comparators."""

    def test_hba1c_flagging(self):
        # Diabetic threshold >= 6.5%
        is_abn, rng = lab_flagger.evaluate_lab_value("HbA1c", "7.1 %", unit="%")
        assert is_abn is True
        assert "5.7" in rng

        # Normal < 5.7%
        is_abn_norm, _ = lab_flagger.evaluate_lab_value("HbA1c", "5.4 %", unit="%")
        assert is_abn_norm is False

    def test_platelet_flagging_with_multiplier(self):
        # 1.8 Lakhs /cumm = 180,000 -> Normal (150,000 - 450,000)
        is_abn, rng = lab_flagger.evaluate_lab_value("Platelets", "1.8 Lakhs /cumm", unit="/cumm")
        assert is_abn is False
        assert "150000" in rng

        # 0.8 Lakhs /cumm = 80,000 -> Low / Abnormal
        is_abn_low, _ = lab_flagger.evaluate_lab_value("Platelets", "0.8 Lakhs /cumm", unit="/cumm")
        assert is_abn_low is True

        # 5.2 Lakhs /cumm = 520,000 -> High / Abnormal
        is_abn_high, _ = lab_flagger.evaluate_lab_value("Platelets", "5.2 Lakhs /cumm", unit="/cumm")
        assert is_abn_high is True

    def test_demographic_reference_ranges(self):
        # Hemoglobin 12.5 g/dL:
        # Female (12.0 - 15.5): Normal (False)
        is_abn_f, rng_f = lab_flagger.evaluate_lab_value("Hemoglobin", "12.5 g/dL", unit="g/dL", gender="female")
        assert is_abn_f is False
        assert "12.0 - 15.5" in rng_f

        # Male (13.0 - 17.0): Low (True)
        is_abn_m, rng_m = lab_flagger.evaluate_lab_value("Hemoglobin", "12.5 g/dL", unit="g/dL", gender="male")
        assert is_abn_m is True
        assert "13.0 - 17.0" in rng_m

    def test_unit_mismatch_returns_unverified_none(self):
        # Hemoglobin standard is g/dL. If given mmol/L, engine must NOT guess!
        is_abn, rng = lab_flagger.evaluate_lab_value("Hemoglobin", "8.5 mmol/L", unit="mmol/L")
        assert is_abn is None

    def test_comparator_flagging(self):
        # Normal comparator < 5.7 %
        is_abn, _ = lab_flagger.evaluate_lab_value("HbA1c", "< 5.7 %", unit="%")
        assert is_abn is False

        # Abnormal comparator > 7.0 %
        is_abn_gt, _ = lab_flagger.evaluate_lab_value("HbA1c", "> 7.0 %", unit="%")
        assert is_abn_gt is True


# ==============================================================================
# 4. Downstream Patient Lab Explanation Tests
# ==============================================================================

class TestDownstreamPatientLabExplanation:
    """Verify /api/patient/explain-lab correctly evaluates HbA1c and Platelets."""

    def test_explain_hba1c_7_point_1(self, client: TestClient):
        payload = {"test_name": "HbA1c", "value": "7.1%", "language": "en"}
        res = client.post("/api/patient/explain-lab", json=payload)
        assert res.status_code == 200
        data = res.json()
        # Must be status "high", not normal
        assert data["status"] == "high"
        assert "7.1" in data["explanation"]
        assert "5.7" in data["reference_range"]

    def test_explain_platelets_1_point_8_lakhs(self, client: TestClient):
        payload = {"test_name": "Platelet Count", "value": "1.8 Lakhs /cumm", "language": "en"}
        res = client.post("/api/patient/explain-lab", json=payload)
        assert res.status_code == 200
        data = res.json()
        # 1.8 Lakhs is 180,000 -> Must be normal, not low
        assert data["status"] == "normal"
        assert "healthy" in data["explanation"] or "normal" in data["explanation"]


# ==============================================================================
# 5. Crop Service Hardening Tests
# ==============================================================================

class TestCropServiceHardening:
    """Verify crop bounds checking, missing file errors, and session cache purge."""

    def test_missing_source_image_raises_file_not_found(self, tmp_path: Path):
        nonexistent = tmp_path / "nonexistent.jpg"
        with pytest.raises(FileNotFoundError):
            crop_service.crop_document(nonexistent, x=0.1, y=0.1, w=0.2, h=0.2)

    def test_out_of_bounds_coordinates_raise_value_error(self, tmp_path: Path):
        img = Image.new("RGB", (100, 100), color="blue")
        img_path = tmp_path / "test.jpg"
        img.save(img_path)

        # Negative x
        with pytest.raises(ValueError):
            crop_service.crop_document(img_path, x=-0.1, y=0.1, w=0.2, h=0.2)

        # Zero or negative width
        with pytest.raises(ValueError):
            crop_service.crop_document(img_path, x=0.1, y=0.1, w=0.0, h=0.2)

        # x + w > 1.05
        with pytest.raises(ValueError):
            crop_service.crop_document(img_path, x=0.9, y=0.1, w=0.3, h=0.2)

    def test_clear_cache_session_isolation(self):
        crop_service._cache[("path/sess1/img.jpg", 0.1, 0.2, 0.3, 0.4)] = b"data1"
        crop_service._cache[("path/sess2/img.jpg", 0.1, 0.2, 0.3, 0.4)] = b"data2"

        crop_service.clear_cache(session_id="sess1")
        assert ("path/sess1/img.jpg", 0.1, 0.2, 0.3, 0.4) not in crop_service._cache
        assert ("path/sess2/img.jpg", 0.1, 0.2, 0.3, 0.4) in crop_service._cache


# ==============================================================================
# 6. Document Upload & Ingestion API Security Tests
# ==============================================================================

class TestDocumentIngestionAPISecurity:
    """Verify session validation, path traversal defense, file limits, and 404s."""

    def test_upload_requires_active_session(self, client: TestClient):
        # Fake session ID
        response = client.post(
            "/api/documents/upload",
            data={"session_id": "nonexistent-session", "page_number": 1, "file_type": "prescription"},
            files={"file": ("test.jpg", b"fake image content", "image/jpeg")},
        )
        assert response.status_code in (400, 404)

    def test_upload_rejects_path_traversal(self, client: TestClient):
        response = client.post(
            "/api/documents/upload",
            data={"session_id": "../traversal/escape", "page_number": 1, "file_type": "prescription"},
            files={"file": ("test.jpg", b"fake image content", "image/jpeg")},
        )
        assert response.status_code == 400
        assert "Invalid session identifier" in response.json()["detail"]

    def test_upload_rejects_unsupported_file_type(self, client: TestClient):
        start_res = client.post(
            "/api/session/start",
            json={"language": "en", "is_caregiver": False},
            headers={"Authorization": f"Bearer {settings.KIOSK_API_KEY}"},
        )
        session_id = start_res.json()["session_id"]

        response = client.post(
            "/api/documents/upload",
            data={"session_id": session_id, "page_number": 1, "file_type": "prescription"},
            files={"file": ("malicious.exe", b"MZ...", "application/x-msdownload")},
        )
        assert response.status_code == 415

    def test_upload_rejects_file_exceeding_10mb(self, client: TestClient):
        start_res = client.post(
            "/api/session/start",
            json={"language": "en", "is_caregiver": False},
            headers={"Authorization": f"Bearer {settings.KIOSK_API_KEY}"},
        )
        session_id = start_res.json()["session_id"]

        oversized_bytes = b"0" * (11 * 1024 * 1024)  # 11 MB
        response = client.post(
            "/api/documents/upload",
            data={"session_id": session_id, "page_number": 1, "file_type": "prescription"},
            files={"file": ("huge.jpg", oversized_bytes, "image/jpeg")},
        )
        assert response.status_code == 413

    def test_missing_document_crop_returns_404_not_sample(self, client: TestClient):
        response = client.get("/api/documents/doc_nonexistent_999/crop?x=0.1&y=0.1&w=0.2&h=0.2")
        assert response.status_code == 404

    def test_missing_document_image_returns_404_not_sample(self, client: TestClient):
        response = client.get("/api/documents/doc_nonexistent_999/image")
        assert response.status_code == 404

    def test_empty_entities_endpoint_returns_zero_facts(self, client: TestClient):
        # Empty session returns 0 entities, NOT sample prescriptions
        start_res = client.post(
            "/api/session/start",
            json={"language": "en", "is_caregiver": False},
            headers={"Authorization": f"Bearer {settings.KIOSK_API_KEY}"},
        )
        session_id = start_res.json()["session_id"]

        res = client.get(f"/api/documents/entities/{session_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["count"] == 0
        assert data["entities"] == []
        assert data["grouped_by_document"] == {}

    def test_document_status_recovery_endpoint(self, client: TestClient):
        start_res = client.post(
            "/api/session/start",
            json={"language": "en", "is_caregiver": False},
            headers={"Authorization": f"Bearer {settings.KIOSK_API_KEY}"},
        )
        session_id = start_res.json()["session_id"]

        # Create valid image
        img = Image.new("RGB", (100, 100), color="green")
        img_buf = io.BytesIO()
        img.save(img_buf, format="JPEG")

        up_res = client.post(
            "/api/documents/upload",
            data={"session_id": session_id, "page_number": 1, "file_type": "prescription"},
            files={"file": ("doc1.jpg", img_buf.getvalue(), "image/jpeg")},
        )
        doc_id = up_res.json()["document_id"]

        status_res = client.get(f"/api/documents/{doc_id}/status")
        assert status_res.status_code == 200
        st_data = status_res.json()
        assert st_data["document_id"] == doc_id
        assert st_data["status"] == "uploaded"
        assert st_data["entity_count"] == 0


# ==============================================================================
# 7. OCR Pipeline Transactional Idempotency & Zero Fabrication Tests
# ==============================================================================

class TestOCRPipelineZeroFabricationAndTransactions:
    """Verify OCR handling of failures, empty outputs, entity types, and idempotency."""

    @pytest.mark.asyncio
    async def test_empty_ocr_returns_zero_entities(self, tmp_path: Path):
        uid = uuid.uuid4().hex[:8]
        sess_id = f"sess_empty_{uid}"
        doc_id = f"doc_empty_{uid}"

        async with async_session_factory() as db:
            sess = DBSession(id=sess_id, status="active")
            db.add(sess)
            doc = Document(
                id=doc_id,
                session_id=sess_id,
                file_path=str(tmp_path / f"{uid}.jpg"),
                file_type="prescription",
                status="uploaded",
            )
            db.add(doc)
            await db.commit()

        # Create dummy file
        (tmp_path / f"{uid}.jpg").write_bytes(b"dummy")

        # Mock Gemini returning empty entity list
        with patch.object(document_processor, "_call_gemini_vision", AsyncMock(return_value=[])):
            async with async_session_factory() as db:
                res = await document_processor.process_document(doc_id, db)
                assert len(res) == 0

        # Verify in DB: exactly 0 entities and status is extracted
        async with async_session_factory() as db:
            doc_db = (await db.execute(select(Document).where(Document.id == doc_id))).scalar_one_or_none()
            assert doc_db.status == "extracted"
            stmt = select(DBLabEntity).where(DBLabEntity.document_id == doc_id)
            result = await db.execute(stmt)
            ents = result.scalars().all()
            assert len(ents) == 0

    @pytest.mark.asyncio
    async def test_failed_ocr_persists_error_status_and_zero_entities(self, tmp_path: Path):
        uid = uuid.uuid4().hex[:8]
        sess_id = f"sess_err_{uid}"
        doc_id = f"doc_err_{uid}"

        async with async_session_factory() as db:
            sess = DBSession(id=sess_id, status="active")
            db.add(sess)
            doc = Document(
                id=doc_id,
                session_id=sess_id,
                file_path=str(tmp_path / f"{uid}.jpg"),
                file_type="prescription",
                status="uploaded",
            )
            db.add(doc)
            await db.commit()

        (tmp_path / f"{uid}.jpg").write_bytes(b"dummy")

        # Mock Gemini throwing exception
        with patch.object(document_processor, "_call_gemini_vision", AsyncMock(side_effect=RuntimeError("Vision API Down"))):
            with pytest.raises(RuntimeError):
                async with async_session_factory() as db:
                    await document_processor.process_document(doc_id, db)

        # Verify in DB: status is error, 0 entities
        async with async_session_factory() as db:
            doc_res = await db.execute(select(Document).where(Document.id == doc_id))
            doc_db = doc_res.scalar_one_or_none()
            assert doc_db is not None
            assert doc_db.status == "error"

            ent_res = await db.execute(select(DBLabEntity).where(DBLabEntity.document_id == doc_id))
            ents = ent_res.scalars().all()
            assert len(ents) == 0

    @pytest.mark.asyncio
    async def test_reprocessing_replaces_prior_entities_idempotently(self, tmp_path: Path):
        uid = uuid.uuid4().hex[:8]
        sess_id = f"sess_idemp_{uid}"
        doc_id = f"doc_idemp_{uid}"

        async with async_session_factory() as db:
            sess = DBSession(id=sess_id, status="active")
            db.add(sess)
            doc = Document(
                id=doc_id,
                session_id=sess_id,
                file_path=str(tmp_path / f"{uid}.jpg"),
                file_type="prescription",
                status="uploaded",
            )
            db.add(doc)
            await db.commit()

        (tmp_path / f"{uid}.jpg").write_bytes(b"dummy")

        # First run: 2 entities
        entities_run1 = [
            {"type": "medication", "value": "Metformin 500mg", "confidence": 0.9},
            {"type": "diagnosis", "value": "Type 2 Diabetes", "confidence": 0.95},
        ]
        with patch.object(document_processor, "_call_gemini_vision", AsyncMock(return_value=entities_run1)):
            async with async_session_factory() as db:
                res1 = await document_processor.process_document(doc_id, db)
                assert len(res1) == 2

        async with async_session_factory() as db:
            res_db1 = await db.execute(select(DBLabEntity).where(DBLabEntity.document_id == doc_id))
            ents_run1 = res_db1.scalars().all()
            assert len(ents_run1) == 2

        # Second run: 3 different entities (simulating reprocessing)
        entities_run2 = [
            {"type": "medication", "value": "Amlodipine 5mg", "confidence": 0.92},
            {"type": "medication", "value": "Aspirin 75mg", "confidence": 0.88},
            {"type": "vital", "value": "BP 130/80", "confidence": 0.91},
        ]
        with patch.object(document_processor, "_call_gemini_vision", AsyncMock(return_value=entities_run2)):
            async with async_session_factory() as db:
                res2 = await document_processor.process_document(doc_id, db)
                assert len(res2) == 3

        # Total in DB must be exactly 3, NOT 2 + 3 = 5!
        async with async_session_factory() as db:
            res_db2 = await db.execute(select(DBLabEntity).where(DBLabEntity.document_id == doc_id))
            ents_run2 = res_db2.scalars().all()
            assert len(ents_run2) == 3
            values = {e.value for e in ents_run2}
            assert "Amlodipine 5mg" in values
            assert "Metformin 500mg" not in values

    @pytest.mark.asyncio
    async def test_entity_validation_and_type_preservation(self, tmp_path: Path):
        uid = uuid.uuid4().hex[:8]
        sess_id = f"sess_types_{uid}"
        doc_id = f"doc_types_{uid}"

        async with async_session_factory() as db:
            sess = DBSession(id=sess_id, status="active")
            db.add(sess)
            doc = Document(
                id=doc_id,
                session_id=sess_id,
                file_path=str(tmp_path / f"{uid}.jpg"),
                file_type="prescription",
                status="uploaded",
            )
            db.add(doc)
            await db.commit()

        (tmp_path / f"{uid}.jpg").write_bytes(b"dummy")

        mock_raw = [
            # vital_sign should normalize to vital
            {"type": "vital_sign", "value": "Pulse 72 bpm", "confidence": 0.95},
            # low confidence medication must NOT mutate to medication:needs_confirmation
            {"type": "medication", "value": "Unclear Tablet 10mg", "confidence": 0.42},
            # invalid bounding box coordinates must normalize to None, not default bbox
            {"type": "allergy", "value": "Penicillin", "confidence": 0.9, "bounding_box": [1.5, 2.0, 0.1, 0.1]},
            # valid bounding box must be preserved
            {"type": "diagnosis", "value": "Hypertension", "confidence": 0.89, "bounding_box": [0.1, 0.2, 0.3, 0.4]},
        ]

        with patch.object(document_processor, "_call_gemini_vision", AsyncMock(return_value=mock_raw)):
            async with async_session_factory() as db:
                res = await document_processor.process_document(doc_id, db)
                assert len(res) == 4

        async with async_session_factory() as db:
            res_db = await db.execute(select(DBLabEntity).where(DBLabEntity.document_id == doc_id))
            ents = res_db.scalars().all()
            by_val = {e.value: e for e in ents}

            # 1. vital_sign -> vital
            assert by_val["Pulse 72 bpm"].entity_type == "vital"

            # 2. low confidence remains medication
            assert by_val["Unclear Tablet 10mg"].entity_type == "medication"
            assert by_val["Unclear Tablet 10mg"].confidence == 0.42

            # 3. out of bounds bbox -> None
            assert by_val["Penicillin"].bounding_box is None

            # 4. valid bbox preserved
            assert by_val["Hypertension"].bounding_box == [0.1, 0.2, 0.3, 0.4]


# ==============================================================================
# 8. ABDM Fetch Security Tests
# ==============================================================================

class TestABDMFetchSecurity:
    """Verify ABDM fetch requires active session, explicit consent, and known sandbox ID."""

    def test_abdm_fetch_without_active_session_fails(self, client: TestClient):
        res = client.post("/api/abdm/fetch-records", json={"abha_id": "rajesh.kumar@abdm", "session_id": "fake_sess"})
        assert res.status_code in (400, 404)

    def test_abdm_fetch_without_consent_returns_403(self, client: TestClient):
        start_res = client.post(
            "/api/session/start",
            json={"language": "en", "is_caregiver": False},
            headers={"Authorization": f"Bearer {settings.KIOSK_API_KEY}"},
        )
        session_id = start_res.json()["session_id"]

        # No store_abdm consent granted
        res = client.post("/api/abdm/fetch-records", json={"abha_id": "rajesh.kumar@abdm", "session_id": session_id})
        assert res.status_code == 403
        assert "consent" in res.json()["detail"].lower()

    def test_abdm_fetch_unknown_abha_returns_404_not_samples(self, client: TestClient):
        start_res = client.post(
            "/api/session/start",
            json={"language": "en", "is_caregiver": False},
            headers={"Authorization": f"Bearer {settings.KIOSK_API_KEY}"},
        )
        session_id = start_res.json()["session_id"]

        # Grant store_abdm consent
        consent_res = client.post(
            "/api/session/consent",
            json={
                "session_id": session_id,
                "consents": [{"action": "store_abdm", "granted": True}],
            },
            headers={"Authorization": f"Bearer {settings.KIOSK_API_KEY}"},
        )
        assert consent_res.status_code == 200

        # Attempt to fetch unrecognized ABHA ID
        res = client.post("/api/abdm/fetch-records", json={"abha_id": "99-9999-9999-9999", "session_id": session_id})
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

    def test_abdm_fetch_valid_sandbox_patient(self, client: TestClient):
        start_res = client.post(
            "/api/session/start",
            json={"language": "en", "is_caregiver": False},
            headers={"Authorization": f"Bearer {settings.KIOSK_API_KEY}"},
        )
        session_id = start_res.json()["session_id"]

        # Grant store_abdm consent
        client.post(
            "/api/session/consent",
            json={
                "session_id": session_id,
                "consents": [{"action": "store_abdm", "granted": True}],
            },
            headers={"Authorization": f"Bearer {settings.KIOSK_API_KEY}"},
        )

        # Sandbox ABHA ID
        res = client.post("/api/abdm/fetch-records", json={"abha_id": "rajesh.kumar@abdm", "session_id": session_id})
        assert res.status_code == 200
        data = res.json()
        assert data["abha_id"] == "rajesh.kumar@abdm"
        assert len(data["records"]) > 0


# ==============================================================================
# 9. Visualization & Contradiction Zero-Fabrication Tests
# ==============================================================================

class TestZeroFabricationInDownstreamServices:
    """Verify visualization and contradiction services never fabricate fake events."""

    @pytest.mark.asyncio
    async def test_what_changed_empty_on_no_patient_history(self):
        # Empty session must yield zero deltas, never inject fake Amlodipine
        async with async_session_factory() as db:
            res = await visualization_service.get_what_changed("empty_session_id_999", db)
            assert len(res["items"]) == 0

    def test_format_delta_summary_empty_when_no_contradictions(self):
        summary = contradiction_detector.format_delta_summary([])
        assert "Amlodipine" not in summary
