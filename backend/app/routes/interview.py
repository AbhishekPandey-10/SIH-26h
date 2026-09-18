"""
WebSocket Clinical Interview Route
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Endpoint: ws://localhost:8000/ws/interview
Bi-directional real-time communication between Kiosk UI and LangGraph Interview Engine.
"""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.interview_engine import interview_engine
from app.services.red_flag_detector import detector as red_flag_detector
from app.shared.schemas import NextQuestion

logger = logging.getLogger("medikiosk.interview_ws")
router = APIRouter()


@router.websocket("/ws/interview")
async def interview_websocket(websocket: WebSocket, session_id: str | None = None):
    """
    WebSocket endpoint for adaptive clinical interview.

    Protocol:
    1. On connect: Kiosk connects (with optional ?session_id=<uuid> query param).
       Backend sends the initial chief complaint question (NextQuestion).
    2. Client sends answer:
       JSON format: {"session_id": "...", "answer": "...", "language": "hi"}
       Or plain text string (treated as answer for current question).
    3. Backend processes:
       - Runs RedFlagDetector on answer text
       - Advances LangGraph state machine to next node
       - Returns next NextQuestion serialized as JSON
    """
    await websocket.accept()
    active_session_id = session_id or f"sess_{id(websocket)}"
    active_language = "hi"

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
            try:
                payload = json.loads(data)
                if isinstance(payload, dict):
                    answer_text = str(payload.get("answer") or payload.get("text") or payload.get("answer_text") or "")
                    active_session_id = payload.get("session_id", active_session_id)
                    active_language = payload.get("language", active_language)
                else:
                    answer_text = str(payload)
            except json.JSONDecodeError:
                answer_text = data.strip()

            # Check for safety red-flags
            red_flag = red_flag_detector.scan_text(answer_text, active_session_id)

            # Advance LangGraph state machine
            next_q: NextQuestion = interview_engine.step(
                session_id=active_session_id,
                answer_text=answer_text,
                language=active_language
            )

            # Attach red-flag alert to response if detected
            if red_flag:
                logger.warning(
                    f"SAFETY ALERT: Red flag detected for session {active_session_id}: "
                    f"{red_flag.trigger_phrase} ({red_flag.category})"
                )
                next_q.is_red_flag_warning = True
                next_q.red_flag_details = {
                    "event_id": red_flag.event_id,
                    "severity": red_flag.severity,
                    "category": red_flag.category,
                    "trigger_phrase": red_flag.trigger_phrase,
                    "matched_rule": red_flag.matched_rule,
                }

            # Send NextQuestion to client
            await websocket.send_text(next_q.model_dump_json())

    except WebSocketDisconnect:
        logger.info(f"Client disconnected from /ws/interview (session: {active_session_id})")
    except Exception as e:
        logger.error(f"Unexpected error in /ws/interview WebSocket: {e}", exc_info=True)
        try:
            await websocket.close(code=1011, reason="Internal error in interview engine")
        except Exception:
            pass
