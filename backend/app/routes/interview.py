"""
WebSocket Clinical Interview Route
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Endpoint: ws://localhost:8000/ws/interview
Bi-directional real-time communication between Kiosk UI and LangGraph Interview Engine.
"""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.db.database import async_session_factory
from app.db.models import InterviewTranscript, RedFlagEventModel
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
    1. On connect: Kiosk connects (defaults to session_id='dev-test-001').
       Backend sends the initial chief complaint question (NextQuestion).
    2. Client sends answer:
       JSON format: {
           "session_id": "dev-test-001",
           "answer": "...",
           "verbatim_voice": "...",
           "language": "hi"
       }
       Or plain text string.
    3. Backend processes:
       - Runs RedFlagDetector (scan + Gemini confirmation)
       - If confirmed, emits WebSocket event `red_flag_triggered` and logs to DB
       - Advances LangGraph state machine to next node
       - Writes turn Q&A to `interview_transcripts` table in DB
       - Returns next NextQuestion serialized as JSON
    """
    await websocket.accept()
    active_session_id = session_id or "dev-test-001"
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
        logger.info(f"Client disconnected from /ws/interview (session: {active_session_id})")
    except Exception as e:
        logger.error(f"Unexpected error in /ws/interview WebSocket: {e}", exc_info=True)
        try:
            await websocket.close(code=1011, reason="Internal error in interview engine")
        except Exception:
            pass
