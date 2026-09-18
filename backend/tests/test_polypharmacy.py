"""
Polypharmacy Detector Tests
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Verifies:
1. Dolo 650 + Calpol 500 -> "Possible duplicate: both are Paracetamol"
2. Warfarin + Ecosprin -> "Interaction risk: increased bleeding"
3. Metformin + Contrast -> "Interaction risk: lactic acidosis"
4. Integration with POST /api/intelligence/polypharmacy
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.db.database import async_session_factory
from app.db.models import ExtractedEntityModel, InterviewTranscript
from app.main import app
from app.services.polypharmacy_detector import polypharmacy_detector


def test_duplicate_paracetamol_detection():
    # Direct medication analysis
    meds = ["Tab Dolo 650mg BD", "Calpol 500 TDS"]
    report = polypharmacy_detector.analyze_medication_list(meds, session_id="test_dup_01")

    assert len(report.duplicates) == 1
    dup = report.duplicates[0]
    assert dup.generic == "paracetamol"
    assert "paracetamol" in dup.message.lower()
    assert "possible duplicate" in dup.message.lower()
    assert len(dup.matched_medications) == 2


def test_warfarin_ecosprin_interaction():
    # High-risk pair: Warfarin (anticoagulant) + Ecosprin (aspirin antiplatelet)
    meds = ["Tab Warf 5mg OD", "Cap Ecosprin 75mg OD"]
    report = polypharmacy_detector.analyze_medication_list(meds, session_id="test_inter_01")

    assert len(report.interactions) >= 1
    inter = next((i for i in report.interactions if i.drug_a == "warfarin" and i.drug_b == "aspirin"), None)
    assert inter is not None
    assert "bleeding" in inter.message.lower()
    assert inter.severity == "high"


def test_metformin_contrast_interaction():
    # Metformin + Contrast dye
    meds = ["Glycomet 500mg BD", "Iodinated Contrast"]
    report = polypharmacy_detector.analyze_medication_list(meds, session_id="test_inter_02")

    assert len(report.interactions) >= 1
    inter = next((i for i in report.interactions if i.drug_a == "metformin"), None)
    assert inter is not None
    assert "lactic acidosis" in inter.message.lower()


@pytest.mark.asyncio
async def test_polypharmacy_endpoint_with_db_entities():
    client = TestClient(app)
    session_id = f"test_poly_sess_{uuid.uuid4().hex[:8]}"

    # Seed one medication in interview transcript and one in document entities
    async with async_session_factory() as db:
        t = InterviewTranscript(
            session_id=session_id,
            turn_number=1,
            question_id="q_med_01",
            question_text="आप कौन सी दवाइयाँ लेते हैं?",
            answer_text="मैं Dolo 650 लेता हूँ (I take Dolo 650)",
            node_name="medications",
            speaker="patient",
            text="Dolo 650",
        )
        e = ExtractedEntityModel(
            id=f"ent_med_{session_id}",
            document_id="doc_prev_01",
            session_id=session_id,
            entity_type="medication",
            value="Calpol 500mg TDS",
            generic_name="Paracetamol",
            confidence=0.98,
        )
        db.add_all([t, e])
        await db.commit()

    resp = client.post("/api/intelligence/polypharmacy", json={"session_id": session_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session_id
    assert len(data["duplicates"]) >= 1
    assert "paracetamol" in data["duplicates"][0]["message"].lower()
