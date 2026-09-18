"""
Phase 4 Comprehensive Test Suite: Dev 1 & Dev 2 Unified Features
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Validates all Phase 4 acceptance criteria across longitudinal multi-visit records:
1. Folk Idiom Normalization & Verbatim Preservation (Hindi/colloquial -> clinical + verbatim)
2. After-Visit Patient Summary Card (Plain language, medication schedule, ABHA QR SVG)
3. Plain-Language Lab Explainer (HbA1c, Hemoglobin, Creatinine plain-language explanations & status)
4. Post-Consult Unvoiced Concern Capture (Persists to transcripts, surfaces in doctor summary)
5. Chronological Multi-Visit Timeline (4 swim lanes: diagnoses, medications, labs, procedures)
6. Longitudinal Lab Trend Sparklines (Reference range zones, status tags, unit mismatch exclusion)
7. "What Changed" Delta View (Identifies started, changed, stopped medications across visits)
"""

import asyncio
import datetime
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.database import async_session_factory
from app.db.models import (
    ClinicalSummary,
    Document,
    ExtractedEntityModel,
    InterviewTranscript,
    Patient,
    Session,
)
from app.main import app
from app.services.folk_idioms import FolkIdiomNormalizer, folk_idiom_normalizer


# --------------------------------------------------------------------------
# Multi-Visit Test Data Fixture
# --------------------------------------------------------------------------
@pytest.fixture
def multi_visit_data():
    patient_id = f"pat_p4_{uuid.uuid4().hex[:6]}"
    abha_id = f"rajesh.{patient_id}@abdm"
    
    session_v1 = f"sess_v1_{uuid.uuid4().hex[:6]}"
    session_v2 = f"sess_v2_{uuid.uuid4().hex[:6]}"
    session_v3 = f"sess_v3_{uuid.uuid4().hex[:6]}"

    async def _seed():
        async with async_session_factory() as db:
            # 1. Create Patient
            patient = Patient(
                id=patient_id,
                abha_id=abha_id,
                name="Rajesh Kumar",
                gender="M",
                dob="1972-05-15",
                mobile="9876543210",
            )
            db.add(patient)

            # 2. Session 1 (10 Jan 2025 - Initial visit)
            s1 = Session(
                id=session_v1,
                patient_id=patient_id,
                status="completed",
                language="hi",
                started_at=datetime.datetime(2025, 1, 10, 10, 0, 0),
            )
            db.add(s1)

            # Generate unique document IDs per test run
            doc_v1 = f"doc_v1_{uuid.uuid4().hex[:6]}"
            doc_v2 = f"doc_v2_{uuid.uuid4().hex[:6]}"
            doc_v3 = f"doc_v3_{uuid.uuid4().hex[:6]}"

            db.add(Document(id=doc_v1, session_id=session_v1, file_path="tests/test_data/sample.jpg", file_type="prescription"))
            db.add(Document(id=doc_v2, session_id=session_v2, file_path="tests/test_data/sample.jpg", file_type="prescription"))
            db.add(Document(id=doc_v3, session_id=session_v3, file_path="tests/test_data/sample.jpg", file_type="prescription"))

            # S1 Entities: Metformin 500mg, HbA1c 8.2%, Diabetes Mellitus
            db.add(ExtractedEntityModel(
                id=f"ent_{uuid.uuid4().hex[:8]}",
                document_id=doc_v1,
                session_id=session_v1,
                entity_type="diagnosis",
                value="Type 2 Diabetes Mellitus",
                generic_name="Type 2 Diabetes Mellitus",
                date="2025-01-10",
                is_abnormal=True,
            ))
            db.add(ExtractedEntityModel(
                id=f"ent_{uuid.uuid4().hex[:8]}",
                document_id=doc_v1,
                session_id=session_v1,
                entity_type="medication",
                value="Metformin 500mg once daily after meals",
                generic_name="Metformin",
                date="2025-01-10",
                is_abnormal=False,
            ))
            db.add(ExtractedEntityModel(
                id=f"ent_{uuid.uuid4().hex[:8]}",
                document_id=doc_v1,
                session_id=session_v1,
                entity_type="lab",
                value="8.2%",
                generic_name="HbA1c",
                unit="%",
                date="2025-01-10",
                is_abnormal=True,
            ))

            # 3. Session 2 (12 Jan 2026 - Follow-up visit)
            s2 = Session(
                id=session_v2,
                patient_id=patient_id,
                status="completed",
                language="hi",
                started_at=datetime.datetime(2026, 1, 12, 11, 0, 0),
            )
            db.add(s2)

            # S2 Entities: Metformin 1000mg, Glimepiride 1mg, HbA1c 7.5%, Cataract procedure
            db.add(ExtractedEntityModel(
                id=f"ent_{uuid.uuid4().hex[:8]}",
                document_id=doc_v2,
                session_id=session_v2,
                entity_type="medication",
                value="Metformin 1000mg twice daily after meals",
                generic_name="Metformin",
                date="2026-01-12",
                is_abnormal=False,
            ))
            db.add(ExtractedEntityModel(
                id=f"ent_{uuid.uuid4().hex[:8]}",
                document_id=doc_v2,
                session_id=session_v2,
                entity_type="medication",
                value="Glimepiride 1mg once daily before breakfast",
                generic_name="Glimepiride",
                date="2026-01-12",
                is_abnormal=False,
            ))
            db.add(ExtractedEntityModel(
                id=f"ent_{uuid.uuid4().hex[:8]}",
                document_id=doc_v2,
                session_id=session_v2,
                entity_type="lab",
                value="7.5%",
                generic_name="HbA1c",
                unit="%",
                date="2026-01-12",
                is_abnormal=True,
            ))
            db.add(ExtractedEntityModel(
                id=f"ent_{uuid.uuid4().hex[:8]}",
                document_id=doc_v2,
                session_id=session_v2,
                entity_type="lab",
                value="1.1 mg/dL",
                generic_name="Serum Creatinine",
                unit="mg/dL",
                date="2026-01-12",
                is_abnormal=False,
            ))
            db.add(ExtractedEntityModel(
                id=f"ent_{uuid.uuid4().hex[:8]}",
                document_id=doc_v2,
                session_id=session_v2,
                entity_type="procedure",
                value="Left Eye Cataract Phacoemulsification",
                generic_name="Cataract Surgery",
                date="2026-01-12",
                is_abnormal=False,
            ))

            # 4. Session 3 (Current OPD Visit - March 2026)
            s3 = Session(
                id=session_v3,
                patient_id=patient_id,
                status="active",
                language="hi",
                started_at=datetime.datetime(2026, 3, 18, 9, 30, 0),
            )
            db.add(s3)

            # S3 Entities: Metformin 1000mg, Glimepiride 2mg (increased), Amlodipine 5mg (new),
            # HbA1c 7.1% (normal), Creatinine 1.2 mg/dL, Hemoglobin 9.5 g/dL (low),
            # Invalid Unit HbA1c (140 mg/dL - unit mismatch), Dental extraction procedure
            db.add(ExtractedEntityModel(
                id=f"ent_{uuid.uuid4().hex[:8]}",
                document_id=doc_v3,
                session_id=session_v3,
                entity_type="medication",
                value="Metformin 1000mg twice daily after meals",
                generic_name="Metformin",
                date="2026-03-18",
                is_abnormal=False,
            ))
            db.add(ExtractedEntityModel(
                id=f"ent_{uuid.uuid4().hex[:8]}",
                document_id=doc_v3,
                session_id=session_v3,
                entity_type="medication",
                value="Glimepiride 2mg once daily before breakfast",
                generic_name="Glimepiride",
                date="2026-03-18",
                is_abnormal=False,
            ))
            db.add(ExtractedEntityModel(
                id=f"ent_{uuid.uuid4().hex[:8]}",
                document_id=doc_v3,
                session_id=session_v3,
                entity_type="medication",
                value="Amlodipine 5mg once daily in morning",
                generic_name="Amlodipine",
                date="2026-03-18",
                is_abnormal=False,
            ))
            db.add(ExtractedEntityModel(
                id=f"ent_{uuid.uuid4().hex[:8]}",
                document_id=doc_v3,
                session_id=session_v3,
                entity_type="lab",
                value="7.1%",
                generic_name="HbA1c",
                unit="%",
                date="2026-03-18",
                is_abnormal=False,
            ))
            db.add(ExtractedEntityModel(
                id=f"ent_{uuid.uuid4().hex[:8]}",
                document_id=doc_v3,
                session_id=session_v3,
                entity_type="lab",
                value="1.2 mg/dL",
                generic_name="Serum Creatinine",
                unit="mg/dL",
                date="2026-03-18",
                is_abnormal=False,
            ))
            db.add(ExtractedEntityModel(
                id=f"ent_{uuid.uuid4().hex[:8]}",
                document_id=doc_v3,
                session_id=session_v3,
                entity_type="lab",
                value="9.5 g/dL",
                generic_name="Hemoglobin",
                unit="g/dL",
                date="2026-03-18",
                is_abnormal=True,
            ))
            # Unit Mismatch entry: HbA1c reported with unit "mg/dL" instead of "%"
            db.add(ExtractedEntityModel(
                id=f"ent_{uuid.uuid4().hex[:8]}",
                document_id=doc_v3,
                session_id=session_v3,
                entity_type="lab",
                value="140 mg/dL",
                generic_name="HbA1c",
                unit="mg/dL",
                date="2026-03-18",
                is_abnormal=True,
            ))
            db.add(ExtractedEntityModel(
                id=f"ent_{uuid.uuid4().hex[:8]}",
                document_id=doc_v3,
                session_id=session_v3,
                entity_type="procedure",
                value="Molar Extraction",
                generic_name="Molar Extraction",
                date="2026-03-18",
                is_abnormal=False,
            ))

            await db.commit()

    asyncio.run(_seed())

    return {
        "patient_id": patient_id,
        "abha_id": abha_id,
        "session_v1": session_v1,
        "session_v2": session_v2,
        "session_v3": session_v3,
    }


# ==========================================================================
# TEST 1: Folk Idiom Normalization & Verbatim Preservation
# ==========================================================================
def test_folk_idiom_normalizer():
    """Verifies folk idioms are accurately mapped to clinical terms while verbatim is strictly preserved."""
    # Test 1: "pet mein aag" -> Epigastric burning / Dyspepsia
    res1 = folk_idiom_normalizer.normalize_statement("डॉक्टर साहब, 2 दिन से पेट में आग जैसी लग रही है")
    assert res1["has_idiom"] is True
    assert "Epigastric burning / Dyspepsia" in res1["clinical_summary"]
    assert "पेट में आग" in res1["verbatim"]

    # Test 2: "sar ghoom raha hai" -> Vertigo / Lightheadedness
    res2 = folk_idiom_normalizer.normalize_statement("sar ghoom raha hai aur kamzori lagti hai")
    assert res2["has_idiom"] is True
    assert "Vertigo / Lightheadedness" in res2["clinical_summary"]

    # Test 3: "chhati mein jalan" -> Retrosternal burning / Heartburn
    res3 = folk_idiom_normalizer.normalize_statement("chhati mein jalan hoti hai khane ke baad")
    assert res3["has_idiom"] is True
    assert "Heartburn" in res3["clinical_summary"]

    # Test 4: "kanpkanpi" -> Fever with rigors and chills
    res4 = folk_idiom_normalizer.normalize_statement("raat ko tez bukhar ke sath kanpkanpi aati hai")
    assert res4["has_idiom"] is True
    assert "rigors" in res4["clinical_summary"]

    # Test 5: Plain clinical text with no idioms
    res5 = folk_idiom_normalizer.normalize_statement("Patient reports bilateral knee joint pain for 3 months")
    assert res5["has_idiom"] is False
    assert res5["clinical_summary"] == "Patient reports bilateral knee joint pain for 3 months"


# ==========================================================================
# TEST 2: After-Visit Patient Summary Card & ABHA QR
# ==========================================================================
def test_patient_summary_card_endpoint(multi_visit_data):
    """Verifies POST /api/patient/summary-card generates non-medical language card with embedded ABHA QR."""
    client = TestClient(app)
    sess_id = multi_visit_data["session_v3"]

    # 1. Hindi Card
    resp_hi = client.post("/api/patient/summary-card", json={"session_id": sess_id, "language": "hi"})
    assert resp_hi.status_code == 200
    data_hi = resp_hi.json()

    assert data_hi["session_id"] == sess_id
    assert data_hi["language"] == "hi"
    assert "परामर्श कार्ड" in data_hi["summary_title"] or "Health Card" in data_hi["summary_title"]
    assert len(data_hi["medications"]) >= 2
    assert len(data_hi["warning_signs"]) >= 2
    # Verify vector QR code is valid SVG
    assert "<svg" in data_hi["qr_code_svg"]
    assert "</svg>" in data_hi["qr_code_svg"]
    assert "abdm.gov.in" in data_hi["abha_url"]

    # 2. English Card
    resp_en = client.post("/api/patient/summary-card", json={"session_id": sess_id, "language": "en"})
    assert resp_en.status_code == 200
    data_en = resp_en.json()
    assert "Health Summary Card" in data_en["summary_title"] or "Health Card" in data_en["summary_title"]
    assert len(data_en["medications"]) >= 2
    assert "<svg" in data_en["qr_code_svg"]


# ==========================================================================
# TEST 3: Plain-Language Lab Explainer Pop-up
# ==========================================================================
def test_explain_lab_endpoint():
    """Verifies POST /api/patient/explain-lab provides plain-language explanations for HbA1c, CBC, and Creatinine."""
    client = TestClient(app)

    # 1. HbA1c test (Normal / borderline)
    resp_hba1c = client.post(
        "/api/patient/explain-lab",
        json={"test_name": "HbA1c", "value": "7.1%", "unit": "%", "language": "hi"}
    )
    assert resp_hba1c.status_code == 200
    data_hba1c = resp_hba1c.json()
    assert data_hba1c["status"] in ["normal", "high"]
    assert "3 महीने" in data_hba1c["explanation"] or "शुगर" in data_hba1c["explanation"]
    assert len(data_hba1c["patient_tip"]) > 0

    # 2. Low Hemoglobin test (Anemia)
    resp_hb = client.post(
        "/api/patient/explain-lab",
        json={"test_name": "Hemoglobin", "value": "9.2", "unit": "g/dL", "language": "en"}
    )
    assert resp_hb.status_code == 200
    data_hb = resp_hb.json()
    assert data_hb["status"] == "low"
    assert "iron" in data_hb["explanation"].lower() or "oxygen" in data_hb["explanation"].lower() or "blood" in data_hb["explanation"].lower()

    # 3. High Creatinine test (Kidney function)
    resp_creat = client.post(
        "/api/patient/explain-lab",
        json={"test_name": "Serum Creatinine", "value": "2.8", "unit": "mg/dL", "language": "hi"}
    )
    assert resp_creat.status_code == 200
    data_creat = resp_creat.json()
    assert data_creat["status"] == "high"
    assert "किडनी" in data_creat["explanation"] or "गुर्दे" in data_creat["explanation"]


# ==========================================================================
# TEST 4: Post-Consult Unvoiced Concern Capture & Scribe Surfacing
# ==========================================================================
def test_post_consult_unvoiced_concern_capture(multi_visit_data):
    """Verifies unvoiced concern is recorded, folk idioms normalized, and surfaced in clinical summary."""
    client = TestClient(app)
    sess_id = multi_visit_data["session_v3"]

    concern_text = "डॉक्टर साहब, पेट में आग और जलन महसूस होती है।"

    # 1. Post unvoiced concern
    resp = client.post(
        "/api/patient/unvoiced-concern",
        json={
            "session_id": sess_id,
            "language": "hi",
            "text": concern_text,
            "verbatim_voice": concern_text,
        }
    )
    assert resp.status_code == 200
    result = resp.json()
    assert result["session_id"] == sess_id
    assert "Epigastric burning" in result["normalized_clinical_text"] or "Dyspepsia" in result["normalized_clinical_text"]
    assert "पेट में" in result["concern_text"]

    # 2. Verify persisted in DB under InterviewTranscript with node_name="unvoiced_concern"
    async def _check_db():
        async with async_session_factory() as db:
            stmt = select(InterviewTranscript).where(
                InterviewTranscript.session_id == sess_id,
                InterviewTranscript.node_name == "unvoiced_concern",
            )
            entry = (await db.execute(stmt)).scalars().first()
            assert entry is not None
            assert "Epigastric burning" in entry.answer_text or "Dyspepsia" in entry.answer_text
            assert entry.verbatim_voice == concern_text

    asyncio.run(_check_db())

    # 3. Verify synthesis surfaces the unvoiced concern
    summary_resp = client.post("/api/summary/generate", json={"session_id": sess_id})
    assert summary_resp.status_code == 200
    fields = summary_resp.json()
    # Find Chief Complaint or HPI field
    hpi_or_cc = [f for f in fields if f["section"] in ["chief_complaint", "hpi"]]
    assert len(hpi_or_cc) > 0
    all_content = " ".join(f["content"] for f in hpi_or_cc)
    assert "UNVOICED PATIENT CONCERN" in all_content or "Epigastric burning" in all_content or "Dyspepsia" in all_content



# ==========================================================================
# TEST 5: Chronological Timeline Across Multiple Visits
# ==========================================================================
def test_chronological_timeline_endpoint(multi_visit_data):
    """Verifies GET /api/visualization/timeline/{patient_id} aggregates across all sessions into 4 swim lanes."""
    client = TestClient(app)
    patient_id = multi_visit_data["patient_id"]

    resp = client.get(f"/api/visualization/timeline/{patient_id}")
    assert resp.status_code == 200
    timeline = resp.json()

    assert timeline["patient_id"] == patient_id
    lanes = timeline["swim_lanes"]

    # 4 distinct swim lanes must be present
    assert "diagnoses" in lanes
    assert "medications" in lanes
    assert "labs" in lanes
    assert "procedures" in lanes

    # Diagnoses lane verification
    diag_titles = [d["title"] for d in lanes["diagnoses"]]
    assert any("Type 2 Diabetes" in t for t in diag_titles)

    # Medications lane verification (spans across sessions)
    med_titles = [m["title"] for m in lanes["medications"]]
    assert any("Metformin" in t for t in med_titles)
    assert any("Glimepiride" in t for t in med_titles)
    assert any("Amlodipine" in t for t in med_titles)

    # Procedures lane verification
    proc_titles = [p["title"] for p in lanes["procedures"]]
    assert any("Cataract" in t for t in proc_titles)
    assert any("Extraction" in t for t in proc_titles)

    # Date bounding sanity check
    assert timeline["start_date"] is not None
    assert timeline["end_date"] is not None
    assert timeline["total_nodes"] >= 6


# ==========================================================================
# TEST 6: Longitudinal Lab Trend Sparklines & Unit Mismatch Exclusion
# ==========================================================================
def test_lab_trends_sparkline_endpoint(multi_visit_data):
    """Verifies GET /api/visualization/lab-trends/{patient_id} calculates normal ranges and excludes unit mismatches."""
    client = TestClient(app)
    patient_id = multi_visit_data["patient_id"]

    # 1. Fetch HbA1c trend
    resp = client.get(f"/api/visualization/lab-trends/{patient_id}?test=hba1c")
    assert resp.status_code == 200
    trends = resp.json()

    assert len(trends["tracked_labs"]) >= 1
    hba1c_lab = next(lab for lab in trends["tracked_labs"] if "hba1c" in lab["test_key"])

    assert hba1c_lab["standard_unit"] == "%"
    assert hba1c_lab["reference_range"]["low"] is not None
    assert hba1c_lab["reference_range"]["high"] is not None

    points = hba1c_lab["points"]
    assert len(points) >= 3

    # Verify unit mismatch exclusion guard
    # The erroneous entry with unit="mg/dL" instead of "%" must be tagged is_excluded=True
    excluded = [p for p in points if p.get("is_excluded") is True]
    assert len(excluded) >= 1
    assert "mismatch" in excluded[0]["exclusion_reason"].lower()
    assert "mg/dL" in excluded[0]["exclusion_reason"]

    # Verify valid percentage points are NOT excluded
    valid = [p for p in points if not p.get("is_excluded")]
    assert len(valid) >= 2
    # Verify status assignment (normal / high)
    for p in valid:
        assert p["status"] in ["normal", "high", "low"]


# ==========================================================================
# TEST 7: "What Changed" Delta View
# ==========================================================================
def test_what_changed_delta_endpoint(multi_visit_data):
    """Verifies GET /api/visualization/what-changed/{session_id} computes differences from previous visit."""
    client = TestClient(app)
    sess_id = multi_visit_data["session_v3"]

    resp = client.get(f"/api/visualization/what-changed/{sess_id}")
    assert resp.status_code == 200
    delta = resp.json()

    assert delta["session_id"] == sess_id
    assert delta["last_visit_date"] is not None
    assert "items" in delta
    assert len(delta["items"]) > 0

    items = delta["items"]
    # 1. Amlodipine was started in session 3 -> prefix "+"
    started = [item for item in items if item.get("prefix") == "+"]
    assert any("Amlodipine" in item["field"] for item in started)

    # 2. Glimepiride dose changed from 1mg to 2mg -> prefix "^"
    changed = [item for item in items if item.get("prefix") == "^"]
    assert any("Glimepiride" in item["field"] for item in changed)
