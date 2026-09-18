"""
Unit and Integration Tests for Module B: Document OCR Pipeline & Module C: Doctor Scribe
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""

import io
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from app.services.crop_service import crop_service
from app.services.document_processor import normalize_indian_date
from app.services.lab_flagging import lab_flagger

# ------------------------------------------------------------------------------
# 1. Lab Abnormal Value Flagging Tests
# ------------------------------------------------------------------------------

def test_lab_flagging_hemoglobin():
    """Verify normal vs abnormal hemoglobin for male and female demographics."""
    # Male: normal 13.0 - 17.0 g/dL
    abnormal_low, rng = lab_flagger.evaluate_lab_value("Hemoglobin", "11.2 g/dL", unit="g/dL", gender="male")
    assert abnormal_low is True
    assert "13.0 - 17.0" in rng

    normal_male, _ = lab_flagger.evaluate_lab_value("Hb", "14.5 g/dL", unit="g/dL", gender="male")
    assert normal_male is False

    # Female: normal 12.0 - 15.5 g/dL
    normal_female, rng_f = lab_flagger.evaluate_lab_value("Hemoglobin", "13.0 g/dL", unit="g/dL", gender="female")
    assert normal_female is False
    assert "12.0 - 15.5" in rng_f


def test_lab_flagging_lft_and_hba1c():
    """Verify LFT SGPT/ALT and HbA1c diabetic flagging."""
    # ALT: normal <= 40 U/L
    abnormal_alt, _ = lab_flagger.evaluate_lab_value("SGPT (ALT)", "65 U/L", unit="U/L")
    assert abnormal_alt is True

    normal_alt, _ = lab_flagger.evaluate_lab_value("ALT", "28 U/L", unit="U/L")
    assert normal_alt is False

    # HbA1c: normal < 5.7 %, diabetic >= 6.5 %
    high_a1c, _ = lab_flagger.evaluate_lab_value("HbA1c", "8.4 %", unit="%")
    assert high_a1c is True


def test_lab_flagging_unit_mismatch_defense():
    """
    On unit mismatch between extracted and reference units,
    engine must set is_abnormal = None (cannot verify) rather than guessing.
    """
    # Hemoglobin standard is g/dL. If extracted as mmol/L or fl, return None
    flag, _ = lab_flagger.evaluate_lab_value("Hemoglobin", "8.5 mmol/L", unit="mmol/L")
    assert flag is None, "Unit mismatch must result in is_abnormal = None"


# ------------------------------------------------------------------------------
# 2. Indian Date Normalization Tests
# ------------------------------------------------------------------------------

def test_date_normalization_indian_format():
    """Test DD/MM/YYYY vs YYYY-MM-DD parsing."""
    assert normalize_indian_date("15/03/2025") == "2025-03-15"
    assert normalize_indian_date("28-11-2024") == "2024-11-28"
    assert normalize_indian_date("2025-01-10") == "2025-01-10"
    assert normalize_indian_date("Unknown") == "Unknown"
    assert normalize_indian_date(None) is None


# ------------------------------------------------------------------------------
# 3. Pillow Crop Service Tests
# ------------------------------------------------------------------------------

def test_crop_service_with_padding(tmp_path: Path):
    """Verify Pillow crops image at normalized coordinates with 8% padding."""
    # Create test image (200 x 200 pixels, solid red)
    test_img = Image.new("RGB", (200, 200), color="red")
    img_path = tmp_path / "test_crop.jpg"
    test_img.save(img_path, format="JPEG")

    # Crop region [0.1, 0.2, 0.4, 0.3]
    jpeg_bytes = crop_service.crop_document(img_path, x=0.1, y=0.2, w=0.4, h=0.3, padding=0.08)
    assert len(jpeg_bytes) > 0

    # Verify cropped output is valid JPEG and roughly matching dimension
    with Image.open(io.BytesIO(jpeg_bytes)) as cropped:
        assert cropped.format == "JPEG"
        # Original width 200 * (0.4 + 2*0.4*0.08) ~ 92 px
        assert 70 <= cropped.width <= 120
        assert 60 <= cropped.height <= 100


# ------------------------------------------------------------------------------
# 4. End-to-End Document Upload, Process & Sort API Tests
# ------------------------------------------------------------------------------

def test_document_upload_and_process_endpoints(client: TestClient, tmp_path: Path):
    """Verify complete document upload -> process -> entities -> crop flow."""
    # Generate test image
    img = Image.new("RGB", (300, 400), color="white")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)

    session_id = "test-doc-session-001"

    # 1. Upload
    response = client.post(
        "/api/documents/upload",
        data={"session_id": session_id, "page_number": 1, "file_type": "prescription"},
        files={"file": ("prescription_p1.jpg", img_bytes.getvalue(), "image/jpeg")},
    )
    assert response.status_code == 200
    upload_data = response.json()
    doc_id = upload_data["document_id"]
    assert upload_data["status"] == "uploaded"

    # 2. Process
    proc_response = client.post(f"/api/documents/process/{doc_id}")
    assert proc_response.status_code == 200
    proc_data = proc_response.json()
    assert proc_data["status"] == "extracted"
    assert proc_data["entity_count"] > 0

    # 3. Fetch entities chronologically
    ent_response = client.get(f"/api/documents/entities/{session_id}?sort=chronological")
    assert ent_response.status_code == 200
    ent_data = ent_response.json()
    assert ent_data["count"] > 0
    assert "grouped_by_document" in ent_data
    assert doc_id in ent_data["grouped_by_document"]

    # 4. Test crop endpoint
    crop_res = client.get(f"/api/documents/{doc_id}/crop?x=0.1&y=0.2&w=0.4&h=0.1")
    assert crop_res.status_code == 200
    assert crop_res.headers["content-type"] == "image/jpeg"


# ------------------------------------------------------------------------------
# 5. Doctor Inline Edit (PUT /api/summary/{session_id}/field/{field_id})
# ------------------------------------------------------------------------------

def test_doctor_field_edit_put_endpoint(client: TestClient):
    """Verify doctor can edit field inline and track verification badge change."""
    session_id = "doc-edit-session-001"

    # Generate summary first
    gen_res = client.post("/api/summary/generate", json={"session_id": session_id})
    assert gen_res.status_code == 200
    fields = gen_res.json()
    assert len(fields) > 0
    target_field = fields[0]
    field_id = target_field["field_id"]

    # Doctor edits the field
    updated_text = "Doctor verified: Patient has severe retrosternal burning."
    put_res = client.put(
        f"/api/summary/{session_id}/field/{field_id}",
        json={"content": updated_text, "doctor_notes": "Confirmed on examination"},
    )
    assert put_res.status_code == 200
    updated_field = put_res.json()
    assert updated_field["content"] == updated_text
    assert updated_field["verification"] == "doctor_edited"
    assert updated_field["changed_since_last"] is True
