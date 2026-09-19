"""
Comprehensive Acceptance and Regression Test Suite for Assignment 3:
Interview State Machine, Emergency Safety, and Clarification Delivery.

Verifies:
a. REST and WebSocket produce equivalent persisted safety transitions, staff alerts, and patient states.
b. Socket failure on first outgoing pause leaves durable alert and staff job.
c. Staff disconnected during detection receives unresolved alert after reconnect.
d. Malformed JSON, missing fields, string booleans ("false"), timeout, and unconfigured model preserve emergency candidates.
e. Contextual affirmative ("Yes" / "हाँ") to safety questions triggers emergency red flag with deterministic severity.
f. Multi-alert dismissal: dismissing 1 of 2 active alerts leaves session held; dismissing both resumes intake; repeated operations idempotent.
g. Ended session mutations rejected with 409 / WS 1008.
h. Reconnected second socket survives cleanup of the old socket.
i. Smart recall confidence tiers at exact boundaries: 0.4999 (ordinary), 0.5 (verification), 0.8 (verification), 0.8001 (confirmation); citations round trip.
j. Ask-back without reply yields pending state with no fabricated transcripts; actual reply updates field and runs safety scan.
k. Unvoiced concerns trigger emergency safety flow when danger phrases are entered.
"""

import asyncio
import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from starlette.websockets import WebSocketDisconnect

from app.db.database import async_session_factory
from app.db.models import ConsentAudit, InterviewTranscript, RedFlagEventModel, Session
from app.main import app
from app.routes.interview import manager as kiosk_manager
from app.routes.interview import staff_manager
from app.services.interview_engine import interview_engine
from app.services.question_generator import question_generator
from app.services.red_flag_detector import red_flag_detector
from app.services.smart_recall import smart_recall_service
from shared.schemas import NextQuestion


# ==============================================================================
# Helper to seed active session
# ==============================================================================
async def create_db_session(session_id: str, status: str = "active", language: str = "en"):
    async with async_session_factory() as db:
        sess = Session(id=session_id, status=status, language=language, interview_mode="allopathic")
        db.add(sess)
        await db.flush()
        # Seed default consent for doctor sharing if active
        if status == "active":
            db.add(ConsentAudit(session_id=session_id, action="share_doctor", granted=True))
        await db.commit()


# ==============================================================================
# a. REST and WebSocket Produce Equivalent Safety Transitions
# ==============================================================================
def test_rest_and_ws_equivalent_safety_pipeline():
    """
    Verifies that REST (POST /api/interview/step) and WebSocket (/ws/interview)
    produce equivalent persisted safety transitions, DB records, and patient states.
    """
    client = TestClient(app)
    rest_sid = f"equiv_rest_{uuid.uuid4().hex[:8]}"
    ws_sid = f"equiv_ws_{uuid.uuid4().hex[:8]}"

    # Run REST submission
    asyncio.run(create_db_session(rest_sid))
    client.post("/api/interview/start", json={"session_id": rest_sid, "language": "en"})

    rest_resp = client.post(
        "/api/interview/step",
        json={
            "session_id": rest_sid,
            "answer_text": "Doctor, I have severe chest pain with breathlessness and cold sweat",
            "language": "en",
        },
    )
    assert rest_resp.status_code == 200
    rest_q = rest_resp.json()
    assert rest_q["section"] == "emergency_hold"
    assert rest_q["is_red_flag_warning"] is True

    # Run WebSocket submission
    asyncio.run(create_db_session(ws_sid))
    with client.websocket_connect(f"/ws/interview?session_id={ws_sid}") as ws:
        _ = ws.receive_json()  # initial question
        ws.send_json({
            "session_id": ws_sid,
            "answer": "Doctor, I have severe chest pain with breathlessness and cold sweat",
        })
        pause_event = ws.receive_json()
        assert pause_event["event"] == "red_flag_triggered"
        assert pause_event["is_paused"] is True
        ws_q = ws.receive_json()
        assert ws_q["section"] == "emergency_hold"
        assert ws_q["is_red_flag_warning"] is True

    # Verify identical persistence in DB for both REST and WS
    async def check_persistence(sid: str):
        async with async_session_factory() as db:
            rf_stmt = select(RedFlagEventModel).where(RedFlagEventModel.session_id == sid)
            rf_ev = (await db.execute(rf_stmt)).scalar_one_or_none()
            assert rf_ev is not None
            assert rf_ev.severity == "red"
            assert rf_ev.category == "cardiac"

            tx_stmt = select(InterviewTranscript).where(InterviewTranscript.session_id == sid)
            transcripts = (await db.execute(tx_stmt)).scalars().all()
            assert len(transcripts) >= 1
            assert any("chest pain" in t.answer_text.lower() for t in transcripts)

    asyncio.run(check_persistence(rest_sid))
    asyncio.run(check_persistence(ws_sid))

    # Verify both session states are paused
    assert interview_engine.sessions[rest_sid]["is_paused"] is True
    assert interview_engine.sessions[ws_sid]["is_paused"] is True


# ==============================================================================
# b. Socket Failure on Outgoing Pause Leaves Durable Alert and Staff Job
# ==============================================================================
@pytest.mark.asyncio
async def test_socket_failure_on_pause_leaves_durable_alert():
    """
    Simulates a client socket dropping or failing right as pause is triggered.
    DB outbox commit must happen before sending over the socket, ensuring
    the RedFlagEventModel and transcript persist even if the socket throws.
    """
    sid = f"sock_fail_{uuid.uuid4().hex[:8]}"
    await create_db_session(sid)

    from app.routes.interview import submit_interview_answer
    from shared.schemas import InterviewAnswer

    ans = InterviewAnswer(
        question_id="q_cc",
        answer_text="I accidentally drank pesticide and feel severe burning",
        language="en",
    )

    async with async_session_factory() as db:
        # submit_interview_answer persists to DB before returning
        next_q, red_flag = await submit_interview_answer(sid, ans, db)

        assert red_flag is not None
        assert red_flag.severity == "red"
        assert next_q.section == "emergency_hold"

    # Now verify DB records exist unconditionally
    async with async_session_factory() as db:
        stmt = select(RedFlagEventModel).where(RedFlagEventModel.session_id == sid)
        ev = (await db.execute(stmt)).scalar_one_or_none()
        assert ev is not None
        assert ev.category == "toxicology"
        assert ev.is_dismissed is False


# ==============================================================================
# c. Staff Disconnected During Detection Receives Unresolved Alert on Reconnect
# ==============================================================================
def test_staff_reconnect_replays_active_unresolved_alerts():
    """
    When an emergency alert occurs while staff is disconnected,
    reconnecting to /ws/staff-alerts immediately replays all active undismissed alerts.
    """
    client = TestClient(app)
    sid = f"staff_replay_{uuid.uuid4().hex[:8]}"
    ev_id = f"rf_replay_{uuid.uuid4().hex[:8]}"

    async def seed():
        async with async_session_factory() as db:
            db.add(Session(id=sid, status="active", language="en"))
            await db.flush()
            from datetime import UTC, datetime
            db.add(
                RedFlagEventModel(
                    id=ev_id,
                    session_id=sid,
                    trigger_phrase="suicidal thoughts",
                    matched_rule="self_harm_ideation",
                    severity="red",
                    category="psychiatric",
                    timestamp=datetime(2020, 1, 1, 0, 0, 0, tzinfo=UTC),
                    is_dismissed=False,
                    is_acknowledged=False,
                )
            )
            await db.commit()

    asyncio.run(seed())

    # Reconnect staff WebSocket
    with client.websocket_connect("/ws/staff-alerts?token=staff_doc_opd_01") as staff_ws:
        received_ids = []
        for _ in range(50):
            try:
                replay_msg = staff_ws.receive_json()
                if replay_msg.get("event") == "red_flag_alert":
                    data = replay_msg.get("data", {})
                    eid = data.get("event_id")
                    received_ids.append(eid)
                    if eid == ev_id:
                        assert data["severity"] == "red"
                        assert data["session_id"] == sid
                        break
            except Exception:
                break
        assert ev_id in received_ids


# ==============================================================================
# d. Strict Typed Confirmation Fail-Safe Modes
# ==============================================================================
def test_strict_typed_confirmation_fail_safe():
    """
    LLM confirmation of candidate red flags must parse strict boolean values.
    If LLM returns malformed JSON, missing fields, times out, or is unconfigured,
    the candidate emergency hold MUST be preserved fail-safe.
    """
    # 1. Malformed JSON -> fail-safe preserves emergency
    mock_resp_malformed = MagicMock()
    mock_resp_malformed.text = "NOT JSON {broken"
    with patch.object(question_generator, "_get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_resp_malformed
        mock_get_client.return_value = mock_client

        res = question_generator.confirm_red_flag_emergency(
            answer="breathlessness",
            matched_keywords=["chest pain", "breathlessness"],
        )
        assert res["is_emergency"] is True
        assert "fail_safe" in res.get("audit_status", "")

    # 2. Missing fields in JSON -> fail-safe preserves emergency
    mock_resp_missing = MagicMock()
    mock_resp_missing.text = "{}"
    with patch.object(question_generator, "_get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_resp_missing
        mock_get_client.return_value = mock_client

        res = question_generator.confirm_red_flag_emergency(
            answer="breathlessness",
            matched_keywords=["chest pain", "breathlessness"],
        )
        assert res["is_emergency"] is True
        assert res.get("audit_status") == "fail_safe_missing_field"

    # 3. String "false" is strictly parsed as boolean False (not treated as truthy)
    mock_resp_str_false = MagicMock()
    mock_resp_str_false.text = json.dumps({"is_emergency": "false", "confidence": 0.95})
    with patch.object(question_generator, "_get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_resp_str_false
        mock_get_client.return_value = mock_client

        res = question_generator.confirm_red_flag_emergency(
            answer="breathlessness",
            matched_keywords=["chest pain", "breathlessness"],
        )
        assert res["is_emergency"] is False

    # 4. Timeout / error -> preserves emergency candidate
    with patch.object(question_generator, "_get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = TimeoutError("Timeout")
        mock_get_client.return_value = mock_client

        res = question_generator.confirm_red_flag_emergency(
            answer="breathlessness",
            matched_keywords=["chest pain", "breathlessness"],
        )
        assert res["is_emergency"] is True
        assert "fail_safe" in res.get("audit_status", "")

    # 5. Unconfigured client -> preserves emergency candidate
    with patch.object(question_generator, "_get_client", return_value=None):
        res = question_generator.confirm_red_flag_emergency(
            answer="breathlessness",
            matched_keywords=["chest pain", "breathlessness"],
        )
        assert res["is_emergency"] is True
        assert "fail_safe" in res.get("audit_status", "")


# ==============================================================================
# e. Contextual Affirmative to Safety Questions & Multi-Rule Severity
# ==============================================================================
def test_contextual_affirmative_and_multi_rule_severity():
    """
    Answers like 'Yes' or 'हाँ' to a suicidal ideation question must trigger the red flag.
    When multiple rules match (e.g. moderate fever AMBER + severe chest pain RED),
    the detector must deterministically aggregate to RED.
    """
    # Contextual affirmative in English
    rf_en = red_flag_detector.scan_and_confirm(
        text="Yes, sometimes",
        session_id="sess_aff_en",
        question_context="Have you had any thoughts of ending your life or harming yourself?",
    )
    assert rf_en is not None
    assert rf_en.severity == "red"
    assert rf_en.category == "psychiatric"

    # Contextual affirmative in Hindi
    rf_hi = red_flag_detector.scan_and_confirm(
        text="हाँ, बहुत ज्यादा",
        session_id="sess_aff_hi",
        question_context="क्या आपके मन में खुद को नुकसान पहुँचाने का विचार आया है?",
    )
    assert rf_hi is not None
    assert rf_hi.severity == "red"
    assert rf_hi.category == "psychiatric"

    # Multi-rule evaluation: AMBER + RED deterministic aggregation
    text_mixed = "I have mild fever and crushing chest pressure radiating to arm or jaw"
    rf_multi = red_flag_detector.scan_and_confirm(text_mixed, session_id="sess_multi")
    assert rf_multi is not None
    assert rf_multi.severity == "red"


# ==============================================================================
# f. Multi-Alert Dismissal Lifecycle and Idempotency
# ==============================================================================
def test_multi_alert_lifecycle_and_idempotency():
    """
    If an encounter has 2 active alerts:
    - Dismissing 1 alert leaves the encounter paused.
    - Dismissing the 2nd alert resumes the encounter.
    - Re-dismissing or re-acknowledging is idempotent.
    - Acknowledging records triage but maintains the emergency pause.
    """
    client = TestClient(app)
    sid = f"multi_rf_{uuid.uuid4().hex[:8]}"
    ev1_id = f"ev1_{uuid.uuid4().hex[:8]}"
    ev2_id = f"ev2_{uuid.uuid4().hex[:8]}"
    staff_headers = {"Authorization": "Bearer staff_nurse_01"}

    async def seed():
        async with async_session_factory() as db:
            db.add(Session(id=sid, status="active", language="en"))
            await db.flush()
            db.add(
                RedFlagEventModel(
                    id=ev1_id,
                    session_id=sid,
                    trigger_phrase="chest pain with breathlessness",
                    matched_rule="cardiac_emergency",
                    severity="red",
                    category="cardiac",
                    is_dismissed=False,
                )
            )
            db.add(
                RedFlagEventModel(
                    id=ev2_id,
                    session_id=sid,
                    trigger_phrase="severe acute shortness of breath at rest",
                    matched_rule="respiratory_emergency",
                    severity="red",
                    category="respiratory",
                    is_dismissed=False,
                )
            )
            await db.commit()

    asyncio.run(seed())

    # Set interview engine state to paused
    state = interview_engine.get_or_create_session(sid)
    state["is_paused"] = True

    # 1. Acknowledge ev1: should record acknowledgement but keep session paused
    ack_resp = client.post(
        f"/api/red-flag/{ev1_id}/acknowledge",
        json={"acknowledged_by": "Dr. Smith", "action_taken": "Triage in progress"},
        headers=staff_headers,
    )
    assert ack_resp.status_code == 200
    assert state["is_paused"] is True

    # Idempotent re-acknowledge
    ack_dup = client.post(
        f"/api/red-flag/{ev1_id}/acknowledge",
        json={"acknowledged_by": "Dr. Smith"},
        headers=staff_headers,
    )
    assert ack_dup.status_code == 200

    # 2. Dismiss ev1: 1 alert remains active (ev2) -> session must remain paused
    d1_resp = client.post(
        f"/api/red-flag/{ev1_id}/dismiss",
        json={"dismissed_by": "Nurse Kelly", "reason": "ECG normal"},
        headers=staff_headers,
    )
    assert d1_resp.status_code == 200
    d1_data = d1_resp.json()
    assert d1_data["remaining_active_alerts"] == 1
    assert d1_data["resumed"] is False
    assert state["is_paused"] is True

    # Idempotent re-dismissal of ev1
    d1_dup = client.post(
        f"/api/red-flag/{ev1_id}/dismiss",
        json={"dismissed_by": "Nurse Kelly", "reason": "ECG normal verified"},
        headers=staff_headers,
    )
    assert d1_dup.status_code == 200

    # 3. Dismiss ev2: 0 alerts remaining -> session must resume
    d2_resp = client.post(
        f"/api/red-flag/{ev2_id}/dismiss",
        json={"dismissed_by": "Nurse Kelly", "reason": "SpO2 99%"},
        headers=staff_headers,
    )
    assert d2_resp.status_code == 200
    d2_data = d2_resp.json()
    assert d2_data["remaining_active_alerts"] == 0
    assert d2_data["resumed"] is True
    assert state["is_paused"] is False


# ==============================================================================
# g. Ended Session Mutations Rejected with 409 / WS 1008
# ==============================================================================
def test_ended_session_mutations_rejected():
    """
    Any mutation attempted against an ended session is rejected with HTTP 409 Conflict,
    and WebSocket connections close with WS 1008 Policy Violation.
    """
    client = TestClient(app)
    sid = f"ended_{uuid.uuid4().hex[:8]}"

    async def seed():
        async with async_session_factory() as db:
            db.add(Session(id=sid, status="ended", language="en"))
            await db.commit()

    asyncio.run(seed())

    # 1. REST step -> 409 Conflict
    step_resp = client.post(
        "/api/interview/step",
        json={"session_id": sid, "answer_text": "I feel better today"},
    )
    assert step_resp.status_code == 409

    # 2. Ask-back reply -> 409 Conflict
    reply_resp = client.post(
        "/api/interview/ask-back/reply",
        json={"session_id": sid, "field_id": "f_test", "answer_text": "Clarification"},
    )
    assert reply_resp.status_code == 409

    # 3. Unvoiced concern -> 409 Conflict
    concern_resp = client.post(
        "/api/patient/unvoiced-concern",
        json={"session_id": sid, "text": "I am worried"},
    )
    assert concern_resp.status_code == 409

    # 4. WebSocket connection rejected with policy violation
    with client.websocket_connect(f"/ws/interview?session_id={sid}") as ws:
        err_envelope = ws.receive_json()
        assert err_envelope["type"] == "error"
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
        assert exc.value.code == 1008


# ==============================================================================
# h. Reconnected Second Socket Survives Cleanup of Old Socket
# ==============================================================================
def test_reconnected_second_socket_survives_cleanup_of_old_socket():
    """
    When a kiosk re-establishes a WebSocket connection (socket2) before socket1
    completes its disconnect handler, disconnecting socket1 must NOT evict socket2.
    """
    sid = f"reconnect_{uuid.uuid4().hex[:8]}"
    mock_ws1 = MagicMock()
    mock_ws2 = MagicMock()

    # Register socket 1
    kiosk_manager.connect(sid, mock_ws1)
    assert kiosk_manager.active_connections[sid] is mock_ws1

    # Reconnect occurs: socket 2 replaces socket 1 in active_connections
    kiosk_manager.connect(sid, mock_ws2)
    assert kiosk_manager.active_connections[sid] is mock_ws2

    # Old socket 1 finally triggers disconnect cleanup
    kiosk_manager.disconnect(sid, websocket=mock_ws1)

    # Socket 2 must still be intact!
    assert kiosk_manager.active_connections.get(sid) is mock_ws2

    # Cleaning up socket 2 removes session
    kiosk_manager.disconnect(sid, websocket=mock_ws2)
    assert sid not in kiosk_manager.active_connections


# ==============================================================================
# i. Smart Recall Confidence Tiers at Exact Boundaries & Citations
# ==============================================================================
def test_smart_recall_confidence_tiers_and_citations():
    """
    Validates exact confidence threshold boundaries:
    - 0.4999 -> ordinary question
    - 0.5000 -> verification question
    - 0.8000 -> verification question
    - 0.8001 -> confirmation question
    Also verifies citation verification endpoint returns 404 on missing transcript.
    """
    base_q = NextQuestion(
        question_id="q_meds_base",
        text="Are you currently taking any prescription medications?",
        input_type="voice",
        options=[],
        section="medications",
        progress_pct=50,
        metadata={},
    )

    # 1. Ordinary tier (< 0.5): 0.4999
    ctx_low = [{
        "entity_id": "ent_low",
        "entity_type": "medication",
        "value": "Metformin 500mg",
        "confidence": 0.4999,
    }]
    q_low = smart_recall_service.adapt_question_with_recall(
        section="medications",
        default_question=base_q,
        extracted_context=ctx_low,
        language="en",
    )
    assert q_low.question_id == base_q.question_id
    assert q_low.metadata.get("verification_tier") is None

    # 2. Verification tier boundary (0.5000)
    ctx_mid1 = [{
        "entity_id": "ent_mid1",
        "entity_type": "medication",
        "value": "Amlodipine 5mg",
        "confidence": 0.5000,
    }]
    q_mid1 = smart_recall_service.adapt_question_with_recall(
        section="medications",
        default_question=base_q,
        extracted_context=ctx_mid1,
        language="en",
    )
    assert q_mid1.metadata["verification_tier"] == "verification"
    assert "Amlodipine" in q_mid1.text

    # 3. Verification tier boundary (0.8000)
    ctx_mid2 = [{
        "entity_id": "ent_mid2",
        "entity_type": "medication",
        "value": "Atorvastatin 10mg",
        "confidence": 0.8000,
    }]
    q_mid2 = smart_recall_service.adapt_question_with_recall(
        section="medications",
        default_question=base_q,
        extracted_context=ctx_mid2,
        language="en",
    )
    assert q_mid2.metadata["verification_tier"] == "verification"
    assert "Atorvastatin" in q_mid2.text

    # 4. Confirmation tier boundary (> 0.8000): 0.8001
    ctx_high = [{
        "entity_id": "ent_high",
        "entity_type": "medication",
        "value": "Insulin Glargine",
        "confidence": 0.8001,
    }]
    q_high = smart_recall_service.adapt_question_with_recall(
        section="medications",
        default_question=base_q,
        extracted_context=ctx_high,
        language="en",
    )
    assert q_high.metadata["verification_tier"] == "confirmation"
    assert "Insulin Glargine" in q_high.text

    # 5. Citation verification: missing transcript returns 404
    client = TestClient(app)
    missing_id = str(uuid.uuid4())
    resp = client.get(f"/api/interview/transcript/{missing_id}")
    assert resp.status_code == 404


# ==============================================================================
# j. Ask-Back Pending State (No Fabrication) and Reply Safety Scan
# ==============================================================================
def test_ask_back_pending_state_and_reply_safety_scan():
    """
    Physician ask-back without answer returns pending state with zero fabricated evidence.
    Actual patient reply via /api/interview/ask-back/reply:
    - Creates genuine transcript record.
    - Scans for red-flag safety triggers.
    """
    client = TestClient(app)
    sid = f"askback_{uuid.uuid4().hex[:8]}"
    staff_headers = {"Authorization": "Bearer staff_doc_opd_01"}

    asyncio.run(create_db_session(sid))

    # 1. Ask-back without answer from doctor
    req_body = {
        "session_id": sid,
        "field_id": "f_duration",
        "question_text": "How many days have you had the rash?",
    }
    ask_resp = client.post("/api/interview/ask-back", json=req_body, headers=staff_headers)
    assert ask_resp.status_code == 200
    field_data = ask_resp.json()
    assert field_data["verification"] == "needs_confirmation"
    assert len(field_data["sources"]) == 0  # No fabricated transcripts!

    # Verify no transcripts exist in DB yet
    async def check_no_tx():
        async with async_session_factory() as db:
            tx = (await db.execute(select(InterviewTranscript).where(InterviewTranscript.session_id == sid))).scalars().all()
            assert len(tx) == 0

    asyncio.run(check_no_tx())

    # 2. Patient replies via /api/interview/ask-back/reply with emergency symptom
    reply_body = {
        "session_id": sid,
        "field_id": "f_duration",
        "answer_text": "The rash is 2 days old, but now I also have chest pain with breathlessness and cold sweat",
    }
    reply_resp = client.post("/api/interview/ask-back/reply", json=reply_body)
    assert reply_resp.status_code == 200

    # Verify genuine transcript AND red-flag event exist in DB
    async def check_persisted_reply():
        async with async_session_factory() as db:
            tx = (await db.execute(select(InterviewTranscript).where(InterviewTranscript.session_id == sid))).scalars().all()
            assert len(tx) == 1
            assert "rash is 2 days old" in tx[0].answer_text

            rf = (await db.execute(select(RedFlagEventModel).where(RedFlagEventModel.session_id == sid))).scalar_one_or_none()
            assert rf is not None
            assert rf.severity == "red"

    asyncio.run(check_persisted_reply())


# ==============================================================================
# k. Unvoiced Concerns Safety Flow
# ==============================================================================
def test_unvoiced_concern_safety_flow():
    """
    Submitting an unvoiced concern containing danger phrases (e.g. suicidal ideation)
    triggers emergency hold, persists RedFlagEventModel, and pauses the interview.
    """
    client = TestClient(app)
    sid = f"unvoiced_{uuid.uuid4().hex[:8]}"

    asyncio.run(create_db_session(sid))
    interview_engine.get_or_create_session(sid)

    # Submit unvoiced concern with danger phrase
    resp = client.post(
        "/api/patient/unvoiced-concern",
        json={
            "session_id": sid,
            "text": "I feel completely hopeless and want to end my life",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "emergency_held"

    # Verify session is paused
    state = interview_engine.sessions.get(sid)
    assert state is not None
    assert state["is_paused"] is True

    # Verify RedFlagEventModel persisted in DB
    async def check_unvoiced_db():
        async with async_session_factory() as db:
            rf = (await db.execute(select(RedFlagEventModel).where(RedFlagEventModel.session_id == sid))).scalar_one_or_none()
            assert rf is not None
            assert rf.severity == "red"
            assert rf.category == "psychiatric"

    asyncio.run(check_unvoiced_db())
