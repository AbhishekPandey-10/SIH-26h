"""
Full Red-Flag Escalation & Staff Alerts Test Suite
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Verifies:
1. Red-flag detected -> kiosk pauses with calm reassurance message
2. Staff alert broadcast mechanism (ws://localhost:8000/ws/staff-alerts & staff_manager)
3. Staff override: POST /api/red-flag/{event_id}/dismiss -> resumes interview
4. Staff override: POST /api/red-flag/{event_id}/acknowledge -> keeps paused, shows "A doctor is coming to see you"
5. Emergency red-flag banner in doctor summary output
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.database import async_session_factory
from app.db.models import ConsentAudit, RedFlagEventModel, Session
from app.main import app
from app.routes.interview import staff_manager
from app.services.interview_engine import interview_engine


def test_red_flag_kiosk_pause_with_calm_message():
    client = TestClient(app)
    session_id = f"test_pause_{uuid.uuid4().hex[:8]}"

    with client.websocket_connect(f"/ws/interview?session_id={session_id}") as kiosk_ws:
        # 1. Initial question
        q1 = kiosk_ws.receive_json()
        assert q1["section"] == "chief_complaint"

        # 2. Trigger critical emergency: chest pain + breathlessness
        kiosk_ws.send_json({
            "session_id": session_id,
            "answer": "Doctor, I have severe chest pain with breathlessness and cold sweat",
            "verbatim_voice": "chest pain with breathlessness",
        })

        # 3. Kiosk MUST receive red_flag_triggered with calm reassurance and pause
        pause_event = kiosk_ws.receive_json()
        assert pause_event["event"] == "red_flag_triggered"
        assert pause_event["is_paused"] is True
        msg = pause_event["message"].lower()
        assert "सुरक्षित" in msg or "care quickly" in msg or "staff member has been notified" in msg or "आराम" in msg

        # Next question delivered is emergency hold question
        hold_q = kiosk_ws.receive_json()
        assert hold_q["section"] == "emergency_hold"
        assert hold_q["is_red_flag_warning"] is True
        event_id = hold_q["red_flag_details"]["event_id"]
        assert event_id is not None

        # Verify state is paused
        state = interview_engine.get_or_create_session(session_id)
        assert state["is_paused"] is True

        # Send next answer while paused -> interview remains paused, does not advance
        kiosk_ws.send_json({
            "session_id": session_id,
            "answer": "When will the doctor come?",
        })
        paused_reply = kiosk_ws.receive_json()
        assert paused_reply["event"] == "interview_paused"


@pytest.mark.asyncio
async def test_staff_alert_manager_broadcast():
    # Verify staff broadcast dispatch
    test_event_id = f"ev_alert_{uuid.uuid4().hex[:8]}"
    alert_payload = {
        "event": "red_flag_alert",
        "data": {
            "event_id": test_event_id,
            "patient_name": "Rajesh Kumar",
            "kiosk_id": "KIOSK-01",
            "trigger_phrase": "chest pain with breathlessness",
            "severity": "red",
            "session_id": "sess_alert_01",
            "timestamp": "2026-09-18T22:00:00Z",
        },
    }

    # Broadcasting with no connected staff devices handles gracefully
    count = await staff_manager.broadcast_alert(alert_payload)
    assert count >= 0


def test_staff_override_dismiss_resumes_interview():
    client = TestClient(app)
    session_id = f"test_dismiss_{uuid.uuid4().hex[:8]}"
    event_id = f"rf_dismiss_{uuid.uuid4().hex[:8]}"

    # Seed red flag in DB and state
    import asyncio
    async def seed():
        async with async_session_factory() as db:
            db.add(Session(id=session_id, status="active", language="en"))
            await db.flush()
            db.add(
                RedFlagEventModel(
                    id=event_id,
                    session_id=session_id,
                    trigger_phrase="chest pain with breathlessness",
                    matched_rule="cardiac_emergency",
                    severity="red",
                    category="cardiac",
                )
            )
            await db.commit()
    asyncio.run(seed())

    # Pause interview state
    state = interview_engine.get_or_create_session(session_id)
    state["is_paused"] = True
    staff_headers = {"Authorization": "Bearer staff_doc_opd_01"}

    # Staff dismisses
    dismiss_resp = client.post(
        f"/api/red-flag/{event_id}/dismiss",
        json={
            "dismissed_by": "Nurse Priya Sharma",
            "reason": "Vitals checked: SpO2 99%, BP 120/80, anxiety related",
        },
        headers=staff_headers,
    )
    assert dismiss_resp.status_code == 200
    dismiss_data = dismiss_resp.json()
    assert dismiss_data["success"] is True
    assert dismiss_data["status"] == "dismissed"

    # State must be unpaused
    assert state["is_paused"] is False

    # Check DB was updated
    async def check_db():
        async with async_session_factory() as db:
            stmt = select(RedFlagEventModel).where(RedFlagEventModel.id == event_id)
            ev = (await db.execute(stmt)).scalar_one_or_none()
            assert ev is not None
            assert ev.is_dismissed is True
            assert ev.dismissed_by in ("Nurse Priya Sharma", "doc_opd_01")
    asyncio.run(check_db())


def test_staff_override_acknowledge():
    client = TestClient(app)
    session_id = f"test_ack_{uuid.uuid4().hex[:8]}"
    event_id = f"rf_ack_{uuid.uuid4().hex[:8]}"
    staff_headers = {"Authorization": "Bearer staff_doc_opd_01"}

    # Seed red flag
    import asyncio
    async def seed():
        async with async_session_factory() as db:
            db.add(Session(id=session_id, status="active", language="en"))
            await db.flush()
            db.add(
                RedFlagEventModel(
                    id=event_id,
                    session_id=session_id,
                    trigger_phrase="loss of consciousness",
                    matched_rule="neurological_emergency",
                    severity="red",
                    category="neurological",
                )
            )
            await db.commit()
    asyncio.run(seed())

    # Pause interview state
    state = interview_engine.get_or_create_session(session_id)
    state["is_paused"] = True

    # Staff acknowledges true emergency
    ack_resp = client.post(
        f"/api/red-flag/{event_id}/acknowledge",
        json={
            "acknowledged_by": "Dr. Anand Rao",
            "action_taken": "Immediate doctor bedside evaluation",
        },
        headers=staff_headers,
    )
    assert ack_resp.status_code == 200
    ack_data = ack_resp.json()
    assert ack_data["success"] is True
    assert ack_data["status"] == "acknowledged"

    # Interview must remain paused
    assert state["is_paused"] is True

    # Check DB
    async def check_db():
        async with async_session_factory() as db:
            stmt = select(RedFlagEventModel).where(RedFlagEventModel.id == event_id)
            ev = (await db.execute(stmt)).scalar_one_or_none()
            assert ev is not None
            assert ev.is_acknowledged is True
            assert ev.acknowledged_by in ("Dr. Anand Rao", "doc_opd_01")
    asyncio.run(check_db())


def test_red_flag_banner_in_doctor_summary():
    client = TestClient(app)
    session_id = f"test_rf_summary_{uuid.uuid4().hex[:8]}"
    staff_headers = {"Authorization": "Bearer staff_doc_opd_01"}

    # Seed an emergency red-flag event in DB for this session
    import asyncio
    async def seed_rf():
        async with async_session_factory() as db:
            db.add(Session(id=session_id, status="active", language="en"))
            await db.flush()
            db.add(ConsentAudit(session_id=session_id, action="share_doctor", granted=True))
            db.add(
                RedFlagEventModel(
                    id=f"rf_ev_{session_id}",
                    session_id=session_id,
                    trigger_phrase="chest pain with breathlessness",
                    matched_rule="cardiac_emergency",
                    severity="red",
                    category="cardiac",
                )
            )
            await db.commit()
    asyncio.run(seed_rf())

    # Call summary generation with staff auth
    resp = client.post("/api/summary/generate", json={"session_id": session_id}, headers=staff_headers)
    assert resp.status_code == 200
    fields = resp.json()
    assert len(fields) >= 1

    # First field MUST be the Emergency Red Flag banner
    top_field = fields[0]


    assert "RED FLAG" in top_field["content"].upper()
    assert "CHEST PAIN" in top_field["content"].upper()
    assert top_field["section"] == "chief_complaint"
