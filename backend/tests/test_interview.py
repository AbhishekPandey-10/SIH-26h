"""
Comprehensive tests for LangGraph Adaptive Clinical Interview Engine
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Verifies:
1. Compilation of the full StateGraph
2. 3 distinct chief complaints ("chest pain", "fever for 5 days", "feeling very sad")
   taking different SOCRATES paths based on classification:
   - "chest pain" -> socrates_pain
   - "fever for 5 days" -> socrates_general
   - "feeling very sad" -> psych_screening
3. Question options and tap choices
4. Voice input and verbatim voice preservation
5. WebSocket /ws/interview responses and event emission:
   - Connects, receives initial chief complaint
   - Sends answers and receives next adaptive questions
   - Emits red_flag_triggered event for emergency symptoms:
     "chest pain with breathlessness" and "I want to end my life"
6. DB persistence of interview_transcripts and red_flag_events
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.database import async_session_factory
from app.db.models import InterviewTranscript, RedFlagEventModel
from app.main import app
from app.services.interview_engine import (
    InterviewEngine,
    build_interview_graph,
)
from app.services.question_generator import question_generator


def test_interview_graph_compilation():
    graph = build_interview_graph()
    assert graph is not None


def test_complaint_classification():
    # 1. Pain category
    cat_pain = question_generator.classify_complaint("Severe chest pain radiating to left arm")
    assert cat_pain == "pain"

    # 2. General category
    cat_gen = question_generator.classify_complaint("fever for 5 days with body chills")
    assert cat_gen == "general"

    # 3. Psych category
    cat_psych = question_generator.classify_complaint("feeling very sad and hopeless every day")
    assert cat_psych == "psych"

    # 4. Obgyn category
    cat_obgyn = question_generator.classify_complaint("missed periods for 2 months and lower abdominal cramps")
    assert cat_obgyn == "obgyn"


def test_flow_chest_pain_routes_to_socrates_pain():
    engine = InterviewEngine()
    session_id = "test_pain_01"

    # Start -> chief complaint
    q1 = engine.start_interview(session_id, language="hi")
    assert q1.section == "chief_complaint"

    # Answer chest pain -> socrates_pain
    q2 = engine.step(session_id, "chest pain since morning")
    assert q2.section == "socrates"
    assert q2.metadata is not None
    assert q2.metadata.get("category") == "socrates_pain"

    # Next step -> pmh
    q3 = engine.step(session_id, "छाती के बीच में भारीपन (Heavy pressure in center)")
    assert q3.section == "pmh"
    assert q3.options is not None

    # Step through remaining sections to complete
    q4 = engine.step(session_id, "मधुमेह (Diabetes)")
    assert q4.section == "medications"

    q5 = engine.step(session_id, "Metformin 500mg")
    assert q5.section == "allergies"

    q6 = engine.step(session_id, "कोई एलर्जी नहीं है")
    assert q6.section == "family_hx"

    q7 = engine.step(session_id, "पिताजी को बीपी था")
    assert q7.section == "personal_hx"

    q8 = engine.step(session_id, "कोई नशा नहीं")
    assert q8.section == "ros"

    q9 = engine.step(session_id, "कोई अन्य लक्षण नहीं")
    assert q9.section == "complete"
    assert q9.progress_pct == 100.0


def test_flow_fever_routes_to_socrates_general():
    engine = InterviewEngine()
    session_id = "test_fever_01"

    # Start -> chief complaint
    q1 = engine.start_interview(session_id, language="hi")
    assert q1.section == "chief_complaint"

    # Answer fever -> socrates_general
    q2 = engine.step(session_id, "fever for 5 days")
    assert q2.section == "socrates"
    assert q2.metadata is not None
    assert q2.metadata.get("category") == "socrates_general"

    # Next step -> pmh
    q3 = engine.step(session_id, "लगातार तेज बुखार है")
    assert q3.section == "pmh"


def test_flow_sadness_routes_to_psych_screening():
    engine = InterviewEngine()
    session_id = "test_psych_01"

    # Start -> chief complaint
    q1 = engine.start_interview(session_id, language="en")
    assert q1.section == "chief_complaint"

    # Answer feeling very sad -> psych_screening
    q2 = engine.step(session_id, "feeling very sad")
    assert q2.section == "socrates"
    assert q2.metadata is not None
    assert q2.metadata.get("category") == "psych_screening"

    # Next step -> pmh
    q3 = engine.step(session_id, "For about 3 weeks now")
    assert q3.section == "pmh"


def test_websocket_interview_and_red_flag_event():
    client = TestClient(app)
    session_id = "dev-test-ws-001"

    with client.websocket_connect(f"/ws/interview?session_id={session_id}") as ws:
        # 1. Initial question on connect
        msg1 = ws.receive_json()
        assert msg1["section"] == "chief_complaint"
        assert msg1["question_id"] == "q_cc_01"

        # 2. Send benign answer -> advances to socrates_pain
        ws.send_json({"answer": "chest pain", "session_id": session_id})
        msg2 = ws.receive_json()
        assert msg2["section"] == "socrates"
        assert msg2["is_red_flag_warning"] is False

        # 3. Send critical red-flag answer: "chest pain with breathlessness"
        ws.send_json({
            "answer": "Doctor, now I have chest pain with breathlessness and sweating",
            "verbatim_voice": "chhati me dard aur saans fulna",
            "session_id": session_id
        })

        # Expect red_flag_triggered WebSocket event
        event_msg = ws.receive_json()
        assert event_msg.get("event") == "red_flag_triggered"
        assert event_msg["data"]["category"] == "cardiac"
        assert "chest pain with breathlessness" in event_msg["data"]["trigger_phrase"]

        # Next comes the NextQuestion response
        next_q_msg = ws.receive_json()
        assert next_q_msg["section"] in ("emergency_hold", "pmh")
        assert next_q_msg["is_red_flag_warning"] is True
        assert next_q_msg["red_flag_details"]["category"] == "cardiac"


def test_red_flag_suicidal_ideation():
    client = TestClient(app)
    session_id = "dev-test-ws-002"

    with client.websocket_connect(f"/ws/interview?session_id={session_id}") as ws:
        # Initial question
        ws.receive_json()

        # Send psychiatric emergency statement
        ws.send_json({
            "answer": "I have severe depression and I want to end my life with suicidal thoughts",
            "session_id": session_id
        })

        event_msg = ws.receive_json()
        assert event_msg.get("event") == "red_flag_triggered"
        assert event_msg["data"]["category"] == "psychiatric"

        next_q = ws.receive_json()
        assert next_q["is_red_flag_warning"] is True


@pytest.mark.asyncio
async def test_transcripts_and_red_flags_saved_in_db():
    # Verify DB persistence of transcripts written during websocket tests
    async with async_session_factory() as session:
        # Check transcript rows
        stmt = select(InterviewTranscript).where(InterviewTranscript.session_id == "dev-test-ws-001")
        result = await session.execute(stmt)
        transcripts = result.scalars().all()
        assert len(transcripts) >= 2

        # Check verbatim voice was preserved
        voice_entry = next((t for t in transcripts if t.verbatim_voice is not None), None)
        assert voice_entry is not None
        assert "saans fulna" in voice_entry.verbatim_voice

        # Check red flag event persistence
        stmt_rf = select(RedFlagEventModel).where(RedFlagEventModel.session_id == "dev-test-ws-001")
        result_rf = await session.execute(stmt_rf)
        rf_events = result_rf.scalars().all()
        assert len(rf_events) >= 1
        assert rf_events[0].category == "cardiac"
