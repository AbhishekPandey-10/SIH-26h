"""
Smart Recall / Zero-Repeat Interview Tests
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Verifies:
1. Returning-patient interview says "Your records show you take Metformin — still current?"
2. Known medications with confidence > 0.8 are confirmed rather than re-asked from scratch
3. Rephrase verification for confidence 0.5 - 0.8
4. Patient confirmation/correction tracked in confirmed_facts
5. Cross-session context injection across patient records
"""

import uuid

import pytest

from app.db.database import async_session_factory
from app.db.models import ExtractedEntityModel, Patient, Session
from app.routes.interview import get_patient_extracted_context
from app.services.interview_engine import InterviewEngine


def test_smart_recall_confirms_known_medication_confidence_gt_80():
    engine = InterviewEngine()
    session_id = f"test_recall_{uuid.uuid4().hex[:8]}"

    # Extracted context with high confidence Metformin (confidence = 0.98)
    extracted_context = [
        {
            "entity_id": "ent_metformin_01",
            "entity_type": "medication",
            "value": "Tab Metformin 500mg BD",
            "generic_name": "Metformin 500mg",
            "confidence": 0.98,
        }
    ]

    # Start interview with injected extracted context
    q1 = engine.start_interview(session_id, language="en", extracted_context=extracted_context)
    assert q1.section == "chief_complaint"

    # Step to socrates
    q2 = engine.step(session_id, "Fever for 3 days")
    assert q2.section in ("socrates", "pmh")

    # Step through socrates to PMH
    q3 = engine.step(session_id, "High fever with chills")
    assert q3.section == "pmh"

    # Step from PMH to medications -> should trigger Smart Recall confirmation!
    q4 = engine.step(session_id, "No other prior illnesses")
    assert q4.section == "medications"

    # CRITICAL ASSERTION: Smart Recall confirmation rather than generic "Do you take any medications?"
    assert "Your records show you take Metformin" in q4.text or "Metformin" in q4.text
    assert "still current" in q4.text.lower() or "जारी" in q4.text
    assert q4.metadata is not None
    assert q4.metadata.get("is_smart_recall") is True
    assert q4.metadata.get("recall_mode") == "confirm_known_fact"

    # Patient confirms: "Yes, still taking it"
    q5 = engine.step(session_id, "Yes, still taking it daily")
    assert q5.section == "allergies"

    # Verify fact confirmation tracked in session state
    state = engine.get_or_create_session(session_id)
    confirmed_facts = state.get("confirmed_facts", [])
    assert len(confirmed_facts) >= 1
    assert confirmed_facts[0]["status"] == "confirmed"
    assert "Metformin" in confirmed_facts[0]["entity"]


def test_smart_recall_hindi_confirmation():
    engine = InterviewEngine()
    session_id = f"test_recall_hi_{uuid.uuid4().hex[:8]}"

    extracted_context = [
        {
            "entity_id": "ent_metformin_hi",
            "entity_type": "medication",
            "value": "Tab Metformin 500mg",
            "generic_name": "Metformin",
            "confidence": 0.95,
        }
    ]

    engine.start_interview(session_id, language="hi", extracted_context=extracted_context)
    engine.step(session_id, "छाती में दर्द")
    engine.step(session_id, "हल्का दर्द")

    # Step from PMH to medications with Smart Recall
    q_med = engine.step(session_id, "कोई पुरानी बीमारी नहीं")
    assert q_med.section == "medications"
    assert "Metformin" in q_med.text
    assert "रिकॉर्ड" in q_med.text


def test_smart_recall_rephrase_verification_confidence_50_to_80():
    engine = InterviewEngine()
    session_id = f"test_recall_mid_{uuid.uuid4().hex[:8]}"

    # Moderate confidence: 0.65
    extracted_context = [
        {
            "entity_id": "ent_amlo_01",
            "entity_type": "medication",
            "value": "Amlodipine 5mg",
            "generic_name": "Amlodipine",
            "confidence": 0.65,
        }
    ]

    engine.start_interview(session_id, language="en", extracted_context=extracted_context)
    engine.step(session_id, "Headache")
    engine.step(session_id, "For 2 days")

    # Step from PMH to medications question with moderate confidence -> rephrase verification
    q_med = engine.step(session_id, "No past diseases")
    assert q_med.section == "medications"
    assert q_med.metadata is not None
    assert q_med.metadata.get("is_smart_recall") is True
    assert q_med.metadata.get("recall_mode") == "rephrase_verification"
    assert "verify" in q_med.text.lower() or "confirm" in q_med.text.lower() or "mention" in q_med.text.lower()



@pytest.mark.asyncio
async def test_cross_session_context_injection():
    # Verify patient with multiple sessions inherits documents from past sessions
    patient_id = f"pat_{uuid.uuid4().hex[:8]}"
    sess_1 = f"sess_old_{uuid.uuid4().hex[:8]}"
    sess_2 = f"sess_new_{uuid.uuid4().hex[:8]}"

    async with async_session_factory() as db:
        # 1. Create patient record
        pat = Patient(
            id=patient_id,
            abha_id=f"user_{patient_id}@abdm",
            name="Suresh Verma",
            gender="M",
            dob="1975-04-12",
        )
        # 2. Old session for this patient with extracted entities
        s1 = Session(id=sess_1, patient_id=patient_id, status="completed", language="hi")
        # 3. New session for the same patient
        s2 = Session(id=sess_2, patient_id=patient_id, status="active", language="hi")
        # 4. Extracted entity on old session
        ent = ExtractedEntityModel(
            id=f"ent_cross_{uuid.uuid4().hex[:8]}",
            document_id="doc_old_opd",
            session_id=sess_1,
            entity_type="medication",
            value="Tab Metformin 500mg",
            generic_name="Metformin",
            confidence=0.96,
        )
        db.add_all([pat, s1, s2, ent])
        await db.commit()

    # Query context for the NEW session
    context = await get_patient_extracted_context(sess_2)
    assert len(context) >= 1
    found_metformin = any(c.get("generic_name") == "Metformin" for c in context)
    assert found_metformin is True
