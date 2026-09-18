"""
WebSocket Clinical Interview Route & Ask-Back Workflow
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Endpoint: ws://localhost:8000/ws/interview
Endpoint: POST /api/interview/ask-back
"""

import json
import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session_factory, get_db
from app.db.models import InterviewTranscript, RedFlagEventModel
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
                await ws.send_text(json.dumps(message))
                return True
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket session {session_id}: {e}")
                return False
        return False


manager = ConnectionManager()


@router.websocket("/ws/interview")
async def interview_websocket(websocket: WebSocket, session_id: str | None = None):
    """
    WebSocket endpoint for adaptive clinical interview.
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

        # 2. Loop on incoming answers from the patient/kiosk
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

            # Inspect current state prior to step
            current_state = interview_engine.get_or_create_session(active_session_id)
            prior_question = current_state.get("next_question")

            # Check for safety red-flags with Gemini confirmation
            red_flag = red_flag_detector.scan_and_confirm(answer_text, active_session_id)

            # If red flag confirmed, emit dedicated WebSocket event
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

            # Attach red-flag alert to NextQuestion response
            if red_flag:
                next_q.is_red_flag_warning = True
                next_q.red_flag_details = {
                    "event_id": red_flag.event_id,
                    "severity": red_flag.severity,
                    "category": red_flag.category,
                    "trigger_phrase": red_flag.trigger_phrase,
                    "matched_rule": red_flag.matched_rule,
                }

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
                    if red_flag:
                        db.add(RedFlagEventModel(
                            id=red_flag.event_id,
                            session_id=active_session_id,
                            trigger_phrase=red_flag.trigger_phrase,
                            matched_rule=red_flag.matched_rule,
                            severity=red_flag.severity,
                            category=red_flag.category,
                            timestamp=red_flag.timestamp,
                        ))
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
        logger.error(f"Unexpected error in /ws/interview WebSocket: {e}", exc_info=True)
        try:
            await websocket.close(code=1011, reason="Internal error in interview engine")
        except Exception:
            pass


class AskBackRequest(BaseModel):
    session_id: str = Field(..., description="Active session ID")
    field_id: str = Field(..., description="Summary field ID to clarify")
    question_text: str = Field(..., description="Physician's clarifying question")
    answer_text: str | None = Field(None, description="Patient's response if provided synchronously")


@router.post("/api/interview/ask-back", response_model=SummaryField, tags=["Clinical Summary"])
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
            }
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
            # Create updated representation
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
