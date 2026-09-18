"""
Phase 5 Comprehensive End-to-End Verification Tests (Dev 1 + Dev 2)
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Tests:
1. Caregiver / Proxy Mode: Session tagging, proxy attribution in transcript, consent, and summary header
2. 2D Body Map Site-Skip: Body map context reaches LangGraph and skips SOCRATES "site" question
3. AYUSH Dashavidha Pariksha: Complete 10-stage classical interview and Prakriti/Dosha evaluation
4. Dual-Lens Clinical Summary: Allopathic <-> Ayurvedic toggle on the same case
5. ABDM Auto-Fetch: Sandbox health records retrieval and automated document entity extraction
"""

import asyncio
import uuid
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

from app.db.database import async_session_factory
from app.db.models import ClinicalSummary, Document, ExtractedEntityModel, InterviewTranscript, Session
from app.main import app
from app.services.ayush_service import (
    DASHHAVIDHA_STAGES,
    evaluate_prakriti_and_dosha,
    generate_ayush_clinical_lens,
)
from app.services.interview_engine import interview_engine


client = TestClient(app)


def test_caregiver_proxy_mode_and_attribution():
    """
    Caregiver / Proxy Mode:
    1. Session started with is_caregiver=True, caregiver details.
    2. WebSocket interview Q&A recorded with speaker='caregiver', is_proxy=True.
    3. Clinical summary includes explicit proxy attribution header at the top.
    """
    session_id = f"test_cg_{uuid.uuid4().hex[:8]}"

    # 1. Start session with caregiver
    start_resp = client.post(
        "/api/session/start",
        json={
            "patient_name": "Ramesh Kumar (Patient)",
            "language": "hi",
            "is_caregiver": True,
            "caregiver_name": "Sunita Devi",
            "caregiver_relationship": "Daughter",
            "caregiver_phone": "9876543210",
        }
    )
    assert start_resp.status_code == 200
    s_data = start_resp.json()
    assert s_data["is_caregiver"] is True
    assert s_data["caregiver_name"] == "Sunita Devi"
    real_session_id = s_data["session_id"]

    # 2. Complete Q&A via WebSocket
    with client.websocket_connect(f"/ws/interview?session_id={real_session_id}") as ws:
        q1 = ws.receive_json()
        assert q1["section"] == "chief_complaint"

        # Caregiver answers for father
        ws.send_json({
            "session_id": real_session_id,
            "answer": "पिताजी को सुबह से सीने में दर्द है",
            "verbatim_voice": "pitaji ko subah se seene mein dard hai",
        })
        q2 = ws.receive_json()
        assert q2 is not None

    # Verify transcript table records proxy details
    async def check_transcript():
        async with async_session_factory() as db:
            stmt = select(InterviewTranscript).where(InterviewTranscript.session_id == real_session_id)
            res = await db.execute(stmt)
            rows = res.scalars().all()
            assert len(rows) >= 1
            entry = rows[0]
            assert entry.is_proxy is True
            assert entry.proxy_name == "Sunita Devi"
            assert entry.proxy_relationship == "Daughter"
            assert entry.speaker == "caregiver"
    asyncio.run(check_transcript())

    # 3. Generate summary and verify caregiver attribution header
    sum_resp = client.post("/api/summary/generate", json={"session_id": real_session_id})
    assert sum_resp.status_code == 200
    fields = sum_resp.json()
    assert len(fields) >= 1

    # Check attribution header field
    caregiver_field = next((f for f in fields if f["field_id"] == "sf_caregiver_hdr"), None)
    assert caregiver_field is not None
    assert "Sunita Devi" in caregiver_field["content"]
    assert "Daughter" in caregiver_field["content"]
    assert "History provided by caregiver" in caregiver_field["content"]


def test_body_map_skips_socrates_site_question():
    """
    Interactive 2D Body Map Site-Skip:
    When anatomical selections exist (e.g. Left chest, Left arm),
    LangGraph socrates_pain_node skips the 'site' question (Where is the pain?)
    and proceeds directly to 'onset' (When did it start?).
    """
    engine = interview_engine
    session_id = f"test_bm_{uuid.uuid4().hex[:8]}"

    # 1. Start interview with body map selections
    q1 = engine.start_interview(
        session_id=session_id,
        language="hi",
        body_map_selections=["Left chest", "Left arm"],
        interview_mode="allopathic",
    )
    assert q1.section == "chief_complaint"

    # 2. Answer with pain complaint -> triggers SOCRATES pain branch
    q2 = engine.step(session_id, "सीने में तेज दर्द है")
    assert q2.section == "socrates"

    # Verify that 'site' question was skipped and 'onset' was asked instead
    assert q2.metadata.get("body_map_skipped_site") is True
    assert "onset" in q2.question_id.lower() or "कब" in q2.text or "when" in q2.text.lower()
    assert "दर्द कहाँ है" not in q2.text  # 'Where is the pain?' question was successfully bypassed!

    # Verify that site selection was stored in state answers
    state = engine.get_or_create_session(session_id)
    site_answer = next((a for a in state["answers"] if a.get("question_id") == "soc_pain_site"), None)
    assert site_answer is not None
    assert "Left chest" in site_answer["answer_text"]
    assert "Left arm" in site_answer["answer_text"]


def test_ayush_dashavidha_pariksha_10_stages_and_prakriti():
    """
    AYUSH Dashavidha Pariksha:
    1. Stages endpoint returns all 10 classical diagnostic stages.
    2. Interactive interview runs through all 10 stages.
    3. Prakriti evaluation calculates Vata, Pitta, Kapha percentages, Agni, and Koshtha.
    """
    # 1. Check stages endpoint
    stages_resp = client.get("/api/ayush/stages")
    assert stages_resp.status_code == 200
    data = stages_resp.json()
    assert data["count"] == 10
    assert len(data["stages"]) == 10

    stage_ids = [s["id"] for s in data["stages"]]
    expected = ["prakriti", "vikriti", "sara", "samhanana", "pramana", "satmya", "satva", "ahara_shakti", "vyayama_shakti", "vaya_koshtha"]
    for exp in expected:
        assert exp in stage_ids

    # 2. Complete 10-stage interview via InterviewEngine
    engine = interview_engine
    session_id = f"test_ayush_{uuid.uuid4().hex[:8]}"

    q_start = engine.start_interview(
        session_id=session_id,
        language="hi",
        interview_mode="ayush",
    )
    assert q_start.section == "chief_complaint"

    # Move to AYUSH branch
    q_first_stage = engine.step(session_id, "पाचन की समस्या और भारीपन")
    assert q_first_stage.section == "ayush_pariksha"
    assert q_first_stage.metadata["stage_id"] == "prakriti"

    # Step through all remaining stages
    ayush_mock_answers = [
        "Lean build, dry skin, intolerant to cold (Vata)",
        "Burning sensation, excessive thirst, acid reflux (Pitta)",
        "Moderate vitality and firmness (Madhyama Sara)",
        "Slender, prominent joints (Sushira / Vata)",
        "Proportionate and balanced",
        "Warm, oily, sweet and sour foods suit best (Vata)",
        "Impatience, irritability, highly focused (Pitta)",
        "Irregular appetite, gas/bloating after meals (Vishama Agni)",
        "Moderate endurance, can do daily tasks without difficulty",
        "Hard stools, chronic tendency for constipation (Krura Koshtha)",
    ]

    curr_q = q_first_stage
    for ans in ayush_mock_answers:
        curr_q = engine.step(session_id, ans)

    # After 10 stages, session is complete with Prakriti evaluation
    state = engine.get_or_create_session(session_id)
    assert state["is_complete"] is True
    prakriti = state.get("prakriti_result")
    assert prakriti is not None
    assert "primary_dosha" in prakriti
    assert "scores" in prakriti
    assert prakriti["scores"]["vata"] > 0
    assert prakriti["agni"] == "vishama"
    assert prakriti["koshtha"] == "krura"


def test_dual_lens_summary_toggle_allopathic_and_ayurvedic():
    """
    Dual-Lens Clinical Summary:
    Doctor can toggle between Allopathic and Ayurvedic views on the same clinical case.
    Ayurvedic lens contains:
    Nidana, Purvarupa, Rupa, Upashaya, Samprapti, Agni/Koshtha, Pathya-Apathya, Chikitsa Sootra.
    """
    session_id = f"test_dual_{uuid.uuid4().hex[:8]}"

    # Seed an interview transcript
    async def seed():
        async with async_session_factory() as db:
            db.add(Session(
                id=session_id,
                language="hi",
                status="active",
                prakriti_result={
                    "prakriti_type": "Vata-Pitta",
                    "primary_dosha": "Vata",
                    "secondary_dosha": "Pitta",
                    "scores": {"vata": 55, "pitta": 35, "kapha": 10},
                    "agni": "vishama",
                    "koshtha": "krura",
                }
            ))
            db.add(InterviewTranscript(
                session_id=session_id,
                turn_number=1,
                question_id="q_cc_01",
                question_text="तकलीफ क्या है?",
                answer_text="सीने में जलन और चुभन वाला दर्द",
                text="सीने में जलन और चुभन वाला दर्द",
                speaker="patient",
                node_name="chief_complaint",
            ))
            await db.commit()
    asyncio.run(seed())

    # 1. Generate Allopathic summary
    allo_resp = client.post("/api/summary/generate", json={"session_id": session_id, "lens": "allopathic"})
    assert allo_resp.status_code == 200
    allo_fields = allo_resp.json()
    assert len(allo_fields) >= 1
    # Verify allopathic fields
    sections = [f["section"] for f in allo_fields]
    assert "chief_complaint" in sections

    # 2. Switch to Ayurvedic summary lens on the SAME session
    ayush_resp = client.post("/api/summary/generate", json={"session_id": session_id, "lens": "ayurvedic"})
    assert ayush_resp.status_code == 200
    ayush_fields = ayush_resp.json()
    assert len(ayush_fields) >= 5

    field_ids = [f["field_id"] for f in ayush_fields]
    assert "sf_ayush_prakriti" in field_ids
    assert "sf_ayush_nidana" in field_ids
    assert "sf_ayush_purvarupa" in field_ids
    assert "sf_ayush_rupa" in field_ids
    assert "sf_ayush_upashaya" in field_ids
    assert "sf_ayush_samprapti" in field_ids
    assert "sf_ayush_agni_koshtha" in field_ids
    assert "sf_ayush_pathya" in field_ids
    assert "sf_ayush_chikitsa" in field_ids

    # Check content of Ayurvedic items
    samprapti_f = next(f for f in ayush_fields if f["field_id"] == "sf_ayush_samprapti")
    assert "Samprapti" in samprapti_f["content"]
    assert "Vata" in samprapti_f["content"]

    pathya_f = next(f for f in ayush_fields if f["field_id"] == "sf_ayush_pathya")
    assert "Pathya" in pathya_f["content"]
    assert "Apathya" in pathya_f["content"]

    chikitsa_f = next(f for f in ayush_fields if f["field_id"] == "sf_ayush_chikitsa")
    assert "Chikitsa Sootra" in chikitsa_f["content"]


def test_abdm_auto_fetch_and_entity_extraction():
    """
    ABDM Auto-Fetch:
    POST /api/abdm/fetch-records retrieves historical records from the ABDM Sandbox
    and triggers document extraction, populating documents and extracted_entities.
    """
    session_id = f"test_abdm_fetch_{uuid.uuid4().hex[:8]}"

    # Call ABDM fetch
    resp = client.post(
        "/api/abdm/fetch-records",
        json={
            "abha_id": "rahul.sharma@abdm",
            "session_id": session_id,
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["records_retrieved"] >= 2
    assert data["extracted_entities_count"] >= 4

    # Verify in database
    async def verify_db():
        async with async_session_factory() as db:
            stmt_doc = select(Document).where(Document.session_id == session_id)
            docs = (await db.execute(stmt_doc)).scalars().all()
            assert len(docs) >= 2

            stmt_ent = select(ExtractedEntityModel).where(ExtractedEntityModel.session_id == session_id)
            entities = (await db.execute(stmt_ent)).scalars().all()
            assert len(entities) >= 4

            # Verify medication and lab values extracted from ABDM
            has_med = any(e.entity_type == "medication" for e in entities)
            has_lab = any(e.entity_type == "lab_value" for e in entities)
            assert has_med is True
            assert has_lab is True
    asyncio.run(verify_db())
