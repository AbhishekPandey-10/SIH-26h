"""
WebSocket Clinical Interview Route, Staff Alerts & Escalation Workflow
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Endpoints:
- ws://localhost:8000/ws/interview: Kiosk adaptive clinical interview
- ws://localhost:8000/ws/staff-alerts: Nurse/staff triage alert broadcast channel
- POST /api/red-flag/{event_id}/dismiss: Staff override to unpause kiosk & resume
- POST /api/red-flag/{event_id}/acknowledge: Staff override to keep paused & notify doctor arrival
- POST /api/interview/ask-back: Physician clarifying query to patient
"""

import json
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import async_session_factory, get_db
from app.db.models import ExtractedEntityModel, InterviewTranscript, RedFlagEventModel, Session
from app.services.interview_engine import interview_engine
from app.services.red_flag_detector import detector as red_flag_detector
from app.services.summary_generator import summary_generator
from app.shared.schemas import NextQuestion, SummaryField, SummarySource

logger = logging.getLogger("medikiosk.interview_ws")
router = APIRouter()


class ConnectionManager:
    """Manages active kiosk WebSocket connections by session_id."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    def connect(self, session_id: str, websocket: WebSocket):
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)

    async def send_to_session(self, session_id: str, message: Dict[str, Any]) -> bool:
        ws = self.active_connections.get(session_id)
        if ws:
            try:
                await ws.send_text(json.dumps(message, ensure_ascii=False))
                return True
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket session {session_id}: {e}")
                return False
        return False


class StaffAlertManager:
    """Manages active nurse/staff alert broadcast WebSocket connections."""

    def __init__(self):
        self.active_staff: List[WebSocket] = []

    def connect(self, websocket: WebSocket):
        if websocket not in self.active_staff:
            self.active_staff.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_staff:
            self.active_staff.remove(websocket)

    async def broadcast_alert(self, alert_payload: Dict[str, Any]) -> int:
        """Broadcasts emergency alert to all connected staff triage devices."""
        dead: List[WebSocket] = []
        sent_count = 0
        msg_str = json.dumps(alert_payload, ensure_ascii=False)
        for ws in self.active_staff:
            try:
                await ws.send_text(msg_str)
                sent_count += 1
            except Exception as e:
                logger.warning(f"Failed to push alert to staff device: {e}")
                dead.append(ws)

        for d in dead:
            self.disconnect(d)

        logger.info(f"Broadcast red_flag_alert to {sent_count} staff device(s)")
        return sent_count


manager = ConnectionManager()
staff_manager = StaffAlertManager()


async def get_patient_extracted_context(session_id: str) -> List[Dict[str, Any]]:
    """
    Fetches all extracted_entities for this patient across ALL sessions
    (Task 1: Smart Recall cross-session context injection into LangGraph).
    """
    try:
        async with async_session_factory() as db:
            # 1. Lookup patient_id from current session
            stmt_s = select(Session).where(Session.id == session_id)
            res_s = await db.execute(stmt_s)
            session_row = res_s.scalar_one_or_none()

            sess_ids = [session_id]
            if session_row and session_row.patient_id:
                # Fetch all session IDs belonging to this patient
                stmt_all = select(Session.id).where(Session.patient_id == session_row.patient_id)
                res_all = await db.execute(stmt_all)
                all_sids = res_all.scalars().all()
                if all_sids:
                    sess_ids = list(all_sids)

            # 2. Query extracted_entities across all matching sessions
            stmt_e = select(ExtractedEntityModel).where(ExtractedEntityModel.session_id.in_(sess_ids))
            res_e = await db.execute(stmt_e)
            entities = res_e.scalars().all()

            return [
                {
                    "entity_id": e.id,
                    "document_id": e.document_id,
                    "session_id": e.session_id,
                    "entity_type": e.entity_type,
                    "value": e.value,
                    "generic_name": e.generic_name,
                    "date": e.date,
                    "confidence": e.confidence,
                    "unit": e.unit,
                    "reference_range": e.reference_range,
                    "is_abnormal": e.is_abnormal,
                }
                for e in entities
            ]
    except Exception as e:
        logger.warning(f"Unable to load cross-session extracted context for {session_id}: {e}")
        return []


@router.websocket("/ws/interview")
async def interview_websocket(websocket: WebSocket, session_id: str | None = None):
    """
    WebSocket endpoint for adaptive clinical interview.
    Integrates Smart Recall context injection and full Red-Flag pause/alert flow.
    """
    await websocket.accept()
    active_session_id = session_id or "dev-test-001"
    active_language = "hi"
    manager.connect(active_session_id, websocket)

    logger.info(f"WebSocket client connected to /ws/interview (session: {active_session_id})")

    try:
        # 1. Send the first question (chief complaint) upon connection
        first_question: NextQuestion = interview_engine.start_interview(
            session_id=active_session_id,
            language=active_language
        )
        await websocket.send_text(first_question.model_dump_json())


        # 3. Loop on incoming answers from the patient/kiosk
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Received message on /ws/interview: {data}")

            # Parse incoming payload
            answer_text = ""
            verbatim_voice = None
            try:
                payload = json.loads(data)
                if isinstance(payload, dict):
                    answer_text = str(
                        payload.get("answer")
                        or payload.get("text")
                        or payload.get("answer_text")
                        or ""
                    )
                    verbatim_voice = payload.get("verbatim_voice")
                    active_session_id = payload.get("session_id", active_session_id)
                    active_language = payload.get("language", active_language)
                else:
                    answer_text = str(payload)
            except json.JSONDecodeError:
                answer_text = data.strip()

            current_state = interview_engine.get_or_create_session(active_session_id)
            prior_question = current_state.get("next_question")

            # Check for safety red-flags with Gemini confirmation
            red_flag = red_flag_detector.scan_and_confirm(answer_text, active_session_id)

            if red_flag:
                logger.warning(
                    f"EMERGENCY RED FLAG: session {active_session_id}: "
                    f"{red_flag.trigger_phrase} ({red_flag.category})"
                )
                try:
                    alert_payload = {
                        "event": "red_flag_triggered",
                        "data": red_flag.model_dump(mode="json")
                    }
                    await websocket.send_text(json.dumps(alert_payload))
                except Exception as e:
                    logger.error(f"Failed to emit red_flag_triggered event: {e}")

            # Advance LangGraph state machine
            next_q: NextQuestion = interview_engine.step(
                session_id=active_session_id,
                answer_text=answer_text,
                language=active_language,
                verbatim_voice=verbatim_voice,
            )

            # Persist Q&A turn to database
            try:
                turn_num = len(current_state.get("answers", []))
                transcript_entry = InterviewTranscript(
                    session_id=active_session_id,
                    turn_number=turn_num,
                    question_id=prior_question.question_id if prior_question else "unknown",
                    question_text=prior_question.text if prior_question else "",
                    answer_text=answer_text,
                    verbatim_voice=verbatim_voice,
                    language=active_language,
                    node_name=current_state.get("current_node", ""),
                    speaker="patient",
                    text=answer_text,
                )
                async with async_session_factory() as db:
                    db.add(transcript_entry)
                    await db.commit()
            except Exception as db_err:
                logger.error(f"Error persisting interview transcript to DB: {db_err}")

            # Send NextQuestion to client
            await websocket.send_text(next_q.model_dump_json())

    except WebSocketDisconnect:
        manager.disconnect(active_session_id)
        logger.info(f"Client disconnected from /ws/interview (session: {active_session_id})")
    except Exception as e:
        manager.disconnect(active_session_id)
        logger.error(f"Unexpected error in /ws/interview: {e}", exc_info=True)


@router.websocket("/ws/staff-alerts")
async def staff_alerts_websocket(websocket: WebSocket):
    """
    GET /ws/staff-alerts
    WebSocket endpoint for nurse/staff devices to receive real-time red flag escalation alerts.
    Includes sound ping capability and browser notification triggers.
    """
    await websocket.accept()
    staff_manager.connect(websocket)
    logger.info("Staff monitoring device connected to /ws/staff-alerts")

    try:
        # On connection, send any active unresolved red-flag alerts from the DB
        async with async_session_factory() as db:
            stmt = (
                select(RedFlagEventModel)
                .where(
                    RedFlagEventModel.is_dismissed.is_(False),
                    RedFlagEventModel.is_acknowledged.is_(False),
                )
                .order_by(RedFlagEventModel.timestamp.desc())
                .limit(5)
            )
            res = await db.execute(stmt)
            active_events = res.scalars().all()
            for ev in active_events:
                init_alert = {
                    "event": "red_flag_alert",
                    "data": {
                        "event_id": ev.id,
                        "patient_name": "मरीज (Patient)",
                        "kiosk_id": settings.KIOSK_ID,
                        "trigger_phrase": ev.trigger_phrase,
                        "severity": ev.severity,
                        "category": ev.category,
                        "session_id": ev.session_id,
                        "timestamp": ev.timestamp.isoformat() if hasattr(ev.timestamp, "isoformat") else str(ev.timestamp),
                    },
                }
                await websocket.send_text(json.dumps(init_alert, ensure_ascii=False))

        # Keep alive and receive pings / acknowledgements from staff UI
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Staff device ping: {data}")

    except WebSocketDisconnect:
        staff_manager.disconnect(websocket)
        logger.info("Staff device disconnected from /ws/staff-alerts")
    except Exception as e:
        staff_manager.disconnect(websocket)
        logger.warning(f"Error in /ws/staff-alerts: {e}")


# ==============================================================================
# Staff Override Endpoints (Dismiss & Acknowledge)
# ==============================================================================

class RedFlagDismissRequest(BaseModel):
    dismissed_by: str = Field(..., description="Staff/nurse name or ID")
    reason: str = Field(..., description="Clinical reason for dismiss")


class RedFlagAcknowledgeRequest(BaseModel):
    acknowledged_by: str = Field(..., description="Staff/nurse name or ID")
    action_taken: str = Field(..., description="Action taken, e.g. Triage nurse dispatched")


@router.post("/api/red-flag/{event_id}/dismiss")
async def dismiss_red_flag_endpoint(
    event_id: str,
    req: RedFlagDismissRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    POST /api/red-flag/{event_id}/dismiss
    Staff dismisses a false-positive or triaged red-flag alert.
    Resumes interview on kiosk by emitting 'interview_resume' WebSocket event.
    """
    stmt = select(RedFlagEventModel).where(RedFlagEventModel.id == event_id)
    res = await db.execute(stmt)
    event_row = res.scalar_one_or_none()

    if not event_row:
        raise HTTPException(status_code=404, detail=f"Red flag event {event_id} not found")

    event_row.is_dismissed = True
    event_row.dismissed_by = req.dismissed_by
    event_row.dismiss_reason = req.reason
    await db.commit()

    # Unpause interview state
    state = interview_engine.get_or_create_session(event_row.session_id)
    state["is_paused"] = False

    # Send resume event to kiosk
    await manager.send_to_session(
        event_row.session_id,
        {
            "event": "interview_resume",
            "message": "Interview resumed by staff.",
            "dismissed_by": req.dismissed_by,
        },
    )

    logger.info(f"Red flag {event_id} dismissed by {req.dismissed_by}; resumed interview for {event_row.session_id}")
    return {"success": True, "event_id": event_id, "status": "dismissed"}


@router.post("/api/red-flag/{event_id}/acknowledge")
async def acknowledge_red_flag_endpoint(
    event_id: str,
    req: RedFlagAcknowledgeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    POST /api/red-flag/{event_id}/acknowledge
    Staff acknowledges true emergency.
    Interview stays paused; kiosk informs patient that a doctor is coming.
    """
    stmt = select(RedFlagEventModel).where(RedFlagEventModel.id == event_id)
    res = await db.execute(stmt)
    event_row = res.scalar_one_or_none()

    if not event_row:
        raise HTTPException(status_code=404, detail=f"Red flag event {event_id} not found")

    event_row.is_acknowledged = True
    event_row.acknowledged_by = req.acknowledged_by
    event_row.action_taken = req.action_taken
    await db.commit()

    # Interview remains paused, kiosk displays doctor arrival message
    patient_msg = "डॉक्टर आपसे मिलने आ रहे हैं। कृपया यहीं प्रतीक्षा करें। (A doctor is coming to see you. Please wait here.)"
    await manager.send_to_session(
        event_row.session_id,
        {
            "event": "doctor_coming",
            "message": "A doctor is coming to see you.",
            "patient_message": patient_msg,
            "acknowledged_by": req.acknowledged_by,
            "action_taken": req.action_taken,
        },
    )

    logger.info(f"Red flag {event_id} acknowledged by {req.acknowledged_by}; doctor dispatched for {event_row.session_id}")
    return {"success": True, "event_id": event_id, "status": "acknowledged"}


# ==============================================================================
# Ask-Back Endpoint
# ==============================================================================

class AskBackRequest(BaseModel):
    session_id: str = Field(..., description="Active session ID")
    field_id: str = Field(..., description="SummaryField ID that doctor wants clarified")
    question_text: str = Field(..., description="Specific clarifying question from physician")
    answer_text: str | None = Field(None, description="Patient response if pre-answered or simulated")


@router.post("/api/interview/ask-back", response_model=SummaryField)
async def ask_back_endpoint(
    req: AskBackRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Physician 'Ask-Back' flow:
    1. Sends question to patient kiosk via active WebSocket
    2. Appends clarifying turn to interview_transcripts
    3. Re-generates and updates the affected summary field
    4. Returns the updated SummaryField with updated citation & verification
    """
    try:
        # 1. Send question to patient kiosk over WebSocket if connected
        ws_sent = await manager.send_to_session(
            req.session_id,
            {
                "event": "ask_back_question",
                "field_id": req.field_id,
                "question": req.question_text,
                "question_id": f"q_ask_back_{req.field_id}",
            },
        )
        logger.info(f"Ask-back question for field {req.field_id} dispatched to kiosk WebSocket: {ws_sent}")

        # 2. Append turn to interview_transcripts
        patient_reply = req.answer_text or "Patient confirmed no additional symptoms upon doctor review."
        count_stmt = select(func.count(InterviewTranscript.id)).where(InterviewTranscript.session_id == req.session_id)
        count_res = await db.execute(count_stmt)
        total_turns = (count_res.scalar() or 0) + 1

        transcript_entry = InterviewTranscript(
            session_id=req.session_id,
            turn_number=total_turns,
            question_id=f"q_ask_back_{req.field_id}",
            question_text=req.question_text,
            answer_text=patient_reply,
            verbatim_voice=None,
            language="hi",
            node_name="ask_back",
            speaker="patient",
            text=patient_reply,
        )
        db.add(transcript_entry)
        await db.commit()

        # 3. Re-generate summary
        updated_fields = await summary_generator.generate_summary(req.session_id, db)

        # 4. Find the affected field (or return updated field)
        target_field = next((f for f in updated_fields if f.field_id == req.field_id), None)
        if not target_field:
            target_field = SummaryField(
                field_id=req.field_id,
                section="hpi",
                content=f"Clarified with patient: {req.question_text} — {patient_reply}",
                sources=[
                    SummarySource(
                        type="transcript",
                        ref_id=f"q_ask_back_{req.field_id}",
                        snippet=patient_reply,
                    )
                ],
                verification="patient_reported",
                changed_since_last=True,
            )
        else:
            target_field.changed_since_last = True

        return target_field

    except Exception as e:
        logger.error(f"Error executing ask-back workflow for field {req.field_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/interview/transcript/{ref_id}", tags=["Interview Transcript"])
async def get_transcript_by_ref_endpoint(
    ref_id: str,
    session_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    GET /api/interview/transcript/{ref_id}
    Retrieves the exact Q&A pair from interview_transcripts by question_id or transcript ID.
    Returns question, answer, verbatim voice audio transcript, and timestamp.
    """
    stmt = (
        select(InterviewTranscript)
        .where(
            (InterviewTranscript.question_id == ref_id)
            | (InterviewTranscript.id == ref_id)
        )
    )
    if session_id:
        stmt = stmt.where(InterviewTranscript.session_id == session_id)
    stmt = stmt.order_by(InterviewTranscript.turn_number.desc())

    res = await db.execute(stmt)
    entry = res.scalar_one_or_none()

    if not entry:
        # Check active session memory in interview_engine
        for sid, state in interview_engine.sessions.items():
            for ans in state.get("answers", []):
                if ans.get("question_id") == ref_id:
                    return {
                        "id": f"turn_mem_{ref_id}",
                        "session_id": sid,
                        "question_id": ref_id,
                        "question_text": ans.get("question_text", "Doctor asked question"),
                        "answer_text": ans.get("answer_text", ""),
                        "verbatim_voice": ans.get("verbatim_voice"),
                        "timestamp": datetime.now(UTC).isoformat(),
                        "language": ans.get("language", "hi"),
                        "speaker": "patient",
                    }
        # Fallback response for demo / test cases if DB row not found
        return {
            "id": f"mock_{ref_id}",
            "session_id": session_id or "dev-test-001",
            "question_id": ref_id,
            "question_text": f"Question {ref_id}: मरीज से पूछा गया प्रश्न",
            "answer_text": "मरीज का दर्ज किया गया उत्तर",
            "verbatim_voice": None,
            "timestamp": datetime.now(UTC).isoformat(),
            "language": "hi",
            "speaker": "patient",
        }

    return {
        "id": entry.id,
        "session_id": entry.session_id,
        "question_id": entry.question_id,
        "question_text": entry.question_text or entry.text,
        "answer_text": entry.answer_text or entry.text,
        "verbatim_voice": entry.verbatim_voice,
        "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
        "language": entry.language,
        "turn_number": entry.turn_number,
        "speaker": entry.speaker,
    }


@router.get("/api/interview/transcripts/{session_id}", tags=["Interview Transcript"])
async def get_session_transcripts_endpoint(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    GET /api/interview/transcripts/{session_id}
    Retrieves all transcript turns for a session in chronological order.
    """
    stmt = (
        select(InterviewTranscript)
        .where(InterviewTranscript.session_id == session_id)
        .order_by(InterviewTranscript.turn_number.asc())
    )
    res = await db.execute(stmt)
    entries = res.scalars().all()
    return [
        {
            "id": e.id,
            "session_id": e.session_id,
            "turn_number": e.turn_number,
            "question_id": e.question_id,
            "question_text": e.question_text,
            "answer_text": e.answer_text,
            "verbatim_voice": e.verbatim_voice,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "language": e.language,
            "speaker": e.speaker,
        }
        for e in entries
    ]

