"""
Unit tests for LangGraph Interview Engine and WebSocket endpoint
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""

from fastapi.testclient import TestClient

from app.main import app
from app.services.interview_engine import (
    InterviewEngine,
    build_interview_graph,
)


def test_interview_graph_compilation():
    graph = build_interview_graph()
    assert graph is not None


def test_sequential_node_progression():
    engine = InterviewEngine()
    session_id = "test_sess_flow_01"

    # 1. Start interview -> chief_complaint
    q1 = engine.start_interview(session_id, language="hi")
    assert q1.section == "chief_complaint"
    assert q1.progress_pct == 10.0

    # 2. Answer CC -> socrates_branch
    q2 = engine.step(session_id, "सीने में दर्द (chest pain)")
    assert q2.section == "socrates"
    assert q2.progress_pct == 25.0

    # 3. Answer Socrates -> pmh
    q3 = engine.step(session_id, "कल रात से, बाएँ हाथ की तरफ जा रहा है")
    assert q3.section == "pmh"
    assert q3.progress_pct == 40.0

    # 4. Answer PMH -> medications
    q4 = engine.step(session_id, "उच्च रक्तचाप (Hypertension)")
    assert q4.section == "medications"
    assert q4.progress_pct == 55.0

    # 5. Answer Meds -> allergies
    q5 = engine.step(session_id, "Amlodipine 5mg")
    assert q5.section == "allergies"
    assert q5.progress_pct == 70.0

    # 6. Answer Allergies -> family_hx
    q6 = engine.step(session_id, "नहीं, कोई ज्ञात एलर्जी नहीं है")
    assert q6.section == "family_hx"
    assert q6.progress_pct == 80.0

    # 7. Answer Family -> personal_hx
    q7 = engine.step(session_id, "पिताजी को दिल का दौरा पड़ा था")
    assert q7.section == "personal_hx"
    assert q7.progress_pct == 90.0

    # 8. Answer Personal -> ros
    q8 = engine.step(session_id, "धूम्रपान नहीं करता")
    assert q8.section == "ros"
    assert q8.progress_pct == 95.0

    # 9. Answer ROS -> complete
    q9 = engine.step(session_id, "हल्का पसीना और घबराहट")
    assert q9.section == "complete"
    assert q9.progress_pct == 100.0


def test_websocket_interview_endpoint():
    client = TestClient(app)

    with client.websocket_connect("/ws/interview?session_id=ws_test_01") as ws:
        # Initial question sent on connection
        msg1 = ws.receive_json()
        assert msg1["section"] == "chief_complaint"
        assert msg1["question_id"] == "q_cc_01"
        assert "is_red_flag_warning" in msg1

        # Send benign answer
        ws.send_json({"answer": "पेट में हल्का दर्द है", "session_id": "ws_test_01"})
        msg2 = ws.receive_json()
        assert msg2["section"] == "socrates"
        assert msg2["is_red_flag_warning"] is False

        # Send red-flag triggering answer
        ws.send_json({"answer": "Now I have chest pain with breathlessness", "session_id": "ws_test_01"})
        msg3 = ws.receive_json()
        assert msg3["section"] == "pmh"
        assert msg3["is_red_flag_warning"] is True
        assert msg3["red_flag_details"]["category"] == "cardiac"
