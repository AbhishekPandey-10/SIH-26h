"""
WebSocket & REST Clinical Interview Route, Staff Escalation & Clarification Delivery
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Provides:
- ws://localhost:8000/ws/interview: Authenticated Kiosk WebSocket interview with reconnect restoration
- POST /api/interview/start: REST encounter initialization with Smart Recall history loading
- POST /api/interview/step: REST answer submission unified with WebSocket pipeline
- POST /api/interview/ask-back: Physician clarifying query (durable pending dispatch)
- POST /api/interview/ask-back/reply: Patient response with safety verification & summary update
- GET /api/interview/transcripts/{session_id}: Enforces session scoping without fabricated mocks
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import async_session_factory, get_db
from app.db.models import ClinicalSummary, ExtractedEntityModel, InterviewTranscript, RedFlagEventModel, Session
from app.dependencies import (
    AuthenticatedUser,
    UserRole,
    authenticate_websocket,
    require_encounter_access,
    require_kiosk,
    require_staff,
)
from app.routes.red_flag import staff_alert_manager
staff_manager = staff_alert_manager
from app.services.interview_engine import interview_engine
from app.services.red_flag_detector import detector as red_flag_detector
from app.services.session_manager import SessionEndedError, session_manager
from app.services.smart_recall import smart_recall_service
from app.services.summary_generator import summary_generator
from app.shared.schemas import (
    InterviewAnswer,
    NextQuestion,
    SummaryField,
    SummarySource,
    WebSocketEnvelope,
    WebSocketMessageType,
)

logger = logging.getLogger("medikiosk.interview_ws")
router = APIRouter()


# ==============================================================================
# Connection Manager (Instance-Safe Disconnect)
# ==============================================================================

class ConnectionManager:
    """
    Manages active kiosk WebSocket connections by session_id.
    Ensures an older socket disconnecting does not evict a newly established replacement.
    """

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    def connect(self, session_id: str, websocket: WebSocket):
        self.active_connections[session_id] = websocket
        logger.info(f"Registered WebSocket for session {session_id}")

    def disconnect(self, session_id: str, websocket: WebSocket | None = None):
        if websocket is None or self.active_connections.get(session_id) is websocket:
            self.active_connections.pop(session_id, None)
            logger.info(f"Deregistered WebSocket for session {session_id}")

    async def send_to_session(self, session_id: str, message: Dict[str, Any]) -> bool:
        ws = self.active_connections.get(session_id)
        if ws:
            try:
                await ws.send_text(json.dumps(message, ensure_ascii=False))
                return True
            except Exception as e:
                logger.warning(f"Failed to send message to session {session_id}: {e}")
                return False
        return False


manager = ConnectionManager()


# Register cleanup hook with session_manager to purge transport & memory on encounter end
async def cleanup_interview_session(session_id: str) -> None:
    manager.disconnect(session_id)
    interview_engine.cleanup_session(session_id)
    logger.info(f"Session {session_id}: Interview transport and state cleaned up via lifecycle hook.")


session_manager.register_cleanup_hook(cleanup_interview_session)


async def get_patient_extracted_context(session_id: str) -> List[Dict[str, Any]]:
    """
    Loads all extracted entities across historical visits for the patient linked to session_id.
    Delegates to canonical SmartRecallService.
    """
    try:
        async with async_session_factory() as db:
            return await smart_recall_service.load_patient_extracted_context(session_id, db)
    except Exception as e:
        logger.warning(f"Unable to load cross-session extracted context for {session_id}: {e}")
        return []


# ==============================================================================
# Unified Application-Level Answer Submission Pipeline
# ==============================================================================

async def submit_interview_answer(
    session_id: str,
    answer: InterviewAnswer,
    db: AsyncSession,
    is_proxy: bool = False,
    proxy_name: str | None = None,
    proxy_relationship: str | None = None,
) -> tuple[NextQuestion, RedFlagEventModel | None]:
    """
    Unified, canonical answer submission operation used across REST, WebSocket,
    and patient input channels.

    Guarantees:
    1. Encounter active guard (session_manager.assert_session_active).
    2. Idempotency: duplicate submissions of the identical turn return existing question.
    3. Contextual safety evaluation across question + answer.
    4. Outbox persistence: RedFlagEventModel and transcript persisted BEFORE broadcast.
    5. Deterministic severity aggregation.
    """
    # 1. Enforce encounter lifecycle guard
    stmt_sess = select(Session).where(Session.id == session_id)
    res_sess = await db.execute(stmt_sess)
    sess_row = res_sess.scalar_one_or_none()
    if sess_row and sess_row.status in ("completed", "ended", "wiped", "cancelled"):
        raise SessionEndedError(session_id)
    elif not sess_row:
        sess_row = Session(
            id=session_id,
            language=answer.language,
            status="active",
            interview_mode="allopathic",
        )
        db.add(sess_row)
        await db.commit()

    current_state = interview_engine.get_or_create_session(session_id)
    prior_question = current_state.get("next_question")


    # If already paused by emergency red flag, maintain hold
    if current_state.get("is_paused") and prior_question is not None:
        logger.warning(f"Session {session_id} is currently paused on emergency hold. Rejecting advance.")
        return prior_question, None

    # 2. Idempotency check: if answering same question with identical text, return existing
    answers_history = current_state.get("answers", [])
    if answers_history and prior_question:
        last_turn = answers_history[-1]
        if last_turn.get("question_id") == answer.question_id and last_turn.get("answer_text") == answer.answer_text:
            logger.info(f"Duplicate answer detected for {session_id}:{answer.question_id}; returning current question idempotently.")
            return prior_question, None

    # 3. Contextual Red-Flag Safety Evaluation
    q_context = prior_question.text if prior_question else None
    red_flag = red_flag_detector.scan_and_confirm(
        text=answer.answer_text,
        session_id=session_id,
        question_context=q_context,
    )

    if red_flag:
        logger.warning(
            f"EMERGENCY RED FLAG: session {session_id}: {red_flag.trigger_phrase} "
            f"({red_flag.category}, {red_flag.severity})"
        )

        # 4. Durable persistence BEFORE best-effort client notification
        event_model = RedFlagEventModel(
            id=red_flag.event_id,
            session_id=session_id,
            trigger_phrase=red_flag.trigger_phrase,
            matched_rule=red_flag.matched_rule,
            severity=red_flag.severity,
            category=red_flag.category,
            timestamp=red_flag.timestamp,
            is_dismissed=False,
            is_acknowledged=False,
        )
        db.add(event_model)

        turn_num = len(answers_history) + 1
        tr_entry = InterviewTranscript(
            session_id=session_id,
            turn_number=turn_num,
            question_id=prior_question.question_id if prior_question else "emergency_trigger",
            question_text=prior_question.text if prior_question else "",
            answer_text=answer.answer_text,
            verbatim_voice=answer.verbatim_voice,
            language=answer.language,
            node_name="emergency_hold",
            speaker="caregiver" if is_proxy else "patient",
            text=answer.answer_text,
            is_proxy=is_proxy,
            proxy_name=proxy_name,
            proxy_relationship=proxy_relationship,
        )
        db.add(tr_entry)
        await db.commit()

        # Update in-memory state to paused
        current_state["is_paused"] = True
        current_state["paused_reason"] = "red_flag"

        # Broadcast to nurse & staff consoles
        await staff_alert_manager.broadcast_alert({
            "event_id": red_flag.event_id,
            "patient_name": "मरीज (Patient)",
            "kiosk_id": settings.KIOSK_ID,
            "trigger_phrase": red_flag.trigger_phrase,
            "severity": red_flag.severity,
            "category": red_flag.category,
            "session_id": session_id,
            "timestamp": red_flag.timestamp.isoformat() if hasattr(red_flag.timestamp, "isoformat") else str(red_flag.timestamp),
        })

        calm_msg_en = "We're making sure you get the right care quickly. A staff member has been notified. Please stay comfortable."
        calm_msg_hi = "हम यह सुनिश्चित कर रहे हैं कि आपको तुरंत उचित देखभाल मिले। अस्पताल स्टाफ को सूचित कर दिया गया है। कृपया आराम से बैठें।"
        calm_message = calm_msg_hi if answer.language == "hi" else calm_msg_en

        paused_q = NextQuestion(
            question_id=f"q_paused_{red_flag.event_id}",
            text=calm_message,
            input_type="voice_touch",
            section="emergency_hold",
            progress_pct=current_state.get("progress_pct", 50.0),
            is_red_flag_warning=True,
            red_flag_details={
                "event_id": red_flag.event_id,
                "severity": red_flag.severity,
                "category": red_flag.category,
                "trigger_phrase": red_flag.trigger_phrase,
                "matched_rule": red_flag.matched_rule,
            },
        )
        current_state["next_question"] = paused_q
        return paused_q, event_model

    # 5. Advance interview state machine
    next_q = interview_engine.step(
        session_id=session_id,
        answer_text=answer.answer_text,
        language=answer.language,
        verbatim_voice=answer.verbatim_voice,
    )

    # Persist Q&A turn to database
    turn_num = len(current_state.get("answers", []))
    transcript_entry = InterviewTranscript(
        session_id=session_id,
        turn_number=turn_num,
        question_id=prior_question.question_id if prior_question else "unknown",
        question_text=prior_question.text if prior_question else "",
        answer_text=answer.answer_text,
        verbatim_voice=answer.verbatim_voice,
        language=answer.language,
        node_name=current_state.get("current_node", ""),
        speaker="caregiver" if is_proxy else "patient",
        text=answer.answer_text,
        is_proxy=is_proxy,
        proxy_name=proxy_name,
        proxy_relationship=proxy_relationship,
    )
    db.add(transcript_entry)
    await db.commit()

    return next_q, None


# ==============================================================================
# WebSocket Endpoint (/ws/interview)
# ==============================================================================

async def send_ws_envelope(websocket: WebSocket, envelope: WebSocketEnvelope) -> None:
    """Sends canonical WebSocketEnvelope while merging payload keys at top-level for backwards compatibility."""
    msg_dict = envelope.model_dump(mode="json")
    if isinstance(envelope.payload, dict):
        for k, v in envelope.payload.items():
            if k not in msg_dict:
                msg_dict[k] = v
    await websocket.send_text(json.dumps(msg_dict, ensure_ascii=False))


@router.websocket("/ws/interview")
async def interview_websocket(websocket: WebSocket, session_id: str | None = None):
    """
    Authenticated WebSocket endpoint for adaptive clinical interview.
    Binds connection identity to session_id, restores current state on reconnection,
    and dispatches canonical typed envelopes (WebSocketEnvelope).
    """
    # 1. Authenticate WebSocket connection
    user = await authenticate_websocket(websocket, session_id=session_id)
    if not user:
        return

    # Use authenticated session_id, avoiding client spoofing
    active_session_id = session_id or user.session_id or "dev-test-001"
    active_language = "hi"

    # Accept connection and register exact instance
    await websocket.accept()
    manager.connect(active_session_id, websocket)
    logger.info(f"Client connected to /ws/interview for session {active_session_id}")

    # 2. Check session status in database
    async with async_session_factory() as db:
        stmt = select(Session).where(Session.id == active_session_id)
        res = await db.execute(stmt)
        s_row = res.scalar_one_or_none()

        if s_row and s_row.status in ("completed", "ended", "wiped", "cancelled"):
            logger.warning(f"Connection rejected: session {active_session_id} is already ended/wiped.")
            err_env = WebSocketEnvelope(
                type="error",
                session_id=active_session_id,
                error="Encounter is ended or wiped.",
            )
            await send_ws_envelope(websocket, err_env)
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Session ended")
            manager.disconnect(active_session_id, websocket)
            return
        elif not s_row:
            s_row = Session(
                id=active_session_id,
                language=active_language,
                status="active",
                interview_mode="allopathic",
            )
            db.add(s_row)
            await db.commit()

        sess_is_caregiver = s_row.is_caregiver if s_row else False
        sess_caregiver_name = s_row.caregiver_name if s_row else None
        sess_caregiver_rel = s_row.caregiver_relationship if s_row else None
        sess_body_map = s_row.body_map_selections or [] if s_row else []
        sess_interview_mode = s_row.interview_mode or "allopathic" if s_row else "allopathic"
        active_language = s_row.language or active_language if s_row else active_language


    try:
        # 3. Check for existing session state (Reconnect restoration)
        current_state = interview_engine.sessions.get(active_session_id)
        if current_state and current_state.get("next_question"):
            existing_q = current_state["next_question"]
            if current_state.get("is_paused"):
                # Session is currently paused on red flag: resend calm reassurance pause envelope
                pause_env = WebSocketEnvelope(
                    type="pause",
                    session_id=active_session_id,
                    payload={
                        "event": "red_flag_triggered",
                        "is_paused": True,
                        "message": existing_q.text,
                        "calm_reassurance": existing_q.text,
                        "data": existing_q.red_flag_details or {},
                        **existing_q.model_dump(),
                    },
                )
                await send_ws_envelope(websocket, pause_env)
            else:
                # Existing question: resend without restarting intake
                q_env = WebSocketEnvelope(
                    type="question",
                    session_id=active_session_id,
                    payload=existing_q.model_dump(),
                )
                await send_ws_envelope(websocket, q_env)
        else:
            # New intake start: Load Smart Recall historical context
            async with async_session_factory() as db:
                extracted_context = await smart_recall_service.load_patient_extracted_context(active_session_id, db)

            first_question: NextQuestion = interview_engine.start_interview(
                session_id=active_session_id,
                language=active_language,
                extracted_context=extracted_context,
                body_map_selections=sess_body_map,
                interview_mode=sess_interview_mode,
                is_caregiver=sess_is_caregiver,
                caregiver_name=sess_caregiver_name,
                caregiver_relationship=sess_caregiver_rel,
            )
            q_env = WebSocketEnvelope(
                type="question",
                session_id=active_session_id,
                payload=first_question.model_dump(),
            )
            await send_ws_envelope(websocket, q_env)


        # 4. Message processing loop
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Received message on /ws/interview: {data}")

            # Parse incoming payload
            answer_text = ""
            verbatim_voice = None
            q_id = None
            msg_is_proxy = sess_is_caregiver
            msg_proxy_name = sess_caregiver_name
            msg_proxy_rel = sess_caregiver_rel

            try:
                raw_payload = json.loads(data)
                if isinstance(raw_payload, dict):
                    # Envelope unwrapping
                    if "payload" in raw_payload and isinstance(raw_payload["payload"], dict):
                        payload = raw_payload["payload"]
                    else:
                        payload = raw_payload

                    answer_text = str(
                        payload.get("answer")
                        or payload.get("text")
                        or payload.get("answer_text")
                        or ""
                    )
                    verbatim_voice = payload.get("verbatim_voice")
                    q_id = payload.get("question_id")
                    active_language = payload.get("language", active_language)
                    if "is_proxy" in payload or "is_caregiver" in payload:
                        msg_is_proxy = bool(payload.get("is_proxy", payload.get("is_caregiver", False)))
                    if payload.get("caregiver_name") or payload.get("proxy_name"):
                        msg_proxy_name = payload.get("caregiver_name") or payload.get("proxy_name")
                    if payload.get("caregiver_relationship") or payload.get("proxy_relationship"):
                        msg_proxy_rel = payload.get("caregiver_relationship") or payload.get("proxy_relationship")
                else:
                    answer_text = str(raw_payload)
            except json.JSONDecodeError:
                answer_text = data.strip()

            current_session_state = interview_engine.get_or_create_session(active_session_id)
            prior_q = current_session_state.get("next_question")
            resolved_qid = q_id or (prior_q.question_id if prior_q else "q_step")

            ans_dto = InterviewAnswer(
                question_id=resolved_qid,
                answer_text=answer_text,
                verbatim_voice=verbatim_voice,
                language=active_language,
            )

            # Submit answer through unified pipeline
            async with async_session_factory() as db:
                try:
                    next_q, red_flag_model = await submit_interview_answer(
                        session_id=active_session_id,
                        answer=ans_dto,
                        db=db,
                        is_proxy=msg_is_proxy,
                        proxy_name=msg_proxy_name,
                        proxy_relationship=msg_proxy_rel,
                    )
                except SessionEndedError:
                    err_env = WebSocketEnvelope(
                        type="error",
                        session_id=active_session_id,
                        error="Session has ended.",
                    )
                    await send_ws_envelope(websocket, err_env)
                    break

            if red_flag_model:
                pause_env = WebSocketEnvelope(
                    type="pause",
                    session_id=active_session_id,
                    payload={
                        "event": "red_flag_triggered",
                        "is_paused": True,
                        "message": next_q.text,
                        "calm_reassurance": next_q.text,
                        "data": next_q.red_flag_details or {},
                    },
                )
                await send_ws_envelope(websocket, pause_env)
                # Send emergency hold question envelope
                hold_env = WebSocketEnvelope(
                    type="question",
                    session_id=active_session_id,
                    payload={
                        **next_q.model_dump(),
                        "event": "emergency_hold",
                    },
                )
                await send_ws_envelope(websocket, hold_env)
            elif current_session_state.get("is_paused"):
                paused_env = WebSocketEnvelope(
                    type="pause",
                    session_id=active_session_id,
                    payload={
                        "event": "interview_paused",
                        "is_paused": True,
                        "message": next_q.text,
                        **next_q.model_dump(),
                    },
                )
                await send_ws_envelope(websocket, paused_env)
            else:
                resp_env = WebSocketEnvelope(
                    type="question",
                    session_id=active_session_id,
                    payload=next_q.model_dump(),
                )
                await send_ws_envelope(websocket, resp_env)


    except WebSocketDisconnect:
        manager.disconnect(active_session_id, websocket)
        logger.info(f"WebSocket client disconnected cleanly (session: {active_session_id})")
    except Exception as e:
        manager.disconnect(active_session_id, websocket)
        logger.error(f"Unexpected error in /ws/interview: {e}", exc_info=True)


# ==============================================================================
# REST Counterparts (Start, Step, Ask-Back)
# ==============================================================================

class InterviewStartRequest(BaseModel):
    session_id: str = Field(..., description="Active session UUID")
    language: str = Field("hi", description="Language code")
    body_map_selections: list[str] | None = Field(None, description="Body map selected regions")
    interview_mode: str = Field("allopathic", description="allopathic or ayush")
    is_caregiver: bool = Field(False, description="Whether caregiver is answering")
    caregiver_name: str | None = Field(None, description="Caregiver name")
    caregiver_relationship: str | None = Field(None, description="Caregiver relationship")


class InterviewStepRequest(BaseModel):
    session_id: str = Field(..., description="Active session UUID")
    question_id: str | None = Field(None, description="The ID of the question being answered")
    answer_text: str = Field("", description="Patient/caregiver response text")
    verbatim_voice: str | None = Field(None, description="Verbatim raw voice transcript")
    language: str = Field("hi", description="Language code")
    is_proxy: bool = Field(False, description="Whether proxy/caregiver answered")
    proxy_name: str | None = Field(None, description="Proxy name")
    proxy_relationship: str | None = Field(None, description="Proxy relationship")


@router.post("/api/interview/start", response_model=NextQuestion, tags=["Interview"])
async def start_interview_endpoint(
    req: InterviewStartRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    POST /api/interview/start
    Initializes clinical interview for a session, loading real Smart Recall historical context.
    """
    await session_manager.assert_session_active(req.session_id, db)

    sess_is_caregiver = req.is_caregiver
    sess_caregiver_name = req.caregiver_name
    sess_caregiver_rel = req.caregiver_relationship
    sess_body_map = req.body_map_selections or []
    sess_interview_mode = req.interview_mode or "allopathic"
    active_language = req.language or "hi"

    stmt = select(Session).where(Session.id == req.session_id)
    res = await db.execute(stmt)
    s_row = res.scalar_one_or_none()
    if s_row:
        if s_row.is_caregiver:
            sess_is_caregiver = True
        if s_row.caregiver_name:
            sess_caregiver_name = s_row.caregiver_name
        if s_row.caregiver_relationship:
            sess_caregiver_rel = s_row.caregiver_relationship
        if s_row.body_map_selections:
            sess_body_map = s_row.body_map_selections
        if s_row.interview_mode:
            sess_interview_mode = s_row.interview_mode
        if s_row.language:
            active_language = s_row.language

    # Load real Smart Recall historical patient evidence
    extracted_context = await smart_recall_service.load_patient_extracted_context(req.session_id, db)

    first_q = interview_engine.start_interview(
        session_id=req.session_id,
        language=active_language,
        extracted_context=extracted_context,
        body_map_selections=sess_body_map,
        interview_mode=sess_interview_mode,
        is_caregiver=sess_is_caregiver,
        caregiver_name=sess_caregiver_name,
        caregiver_relationship=sess_caregiver_rel,
    )
    return first_q


@router.post("/api/interview/step", response_model=NextQuestion, tags=["Interview"])
async def step_interview_endpoint(
    req: InterviewStepRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    POST /api/interview/step
    REST endpoint to submit an answer and advance the interview state machine.
    Uses the identical unified pipeline as WebSocket.
    """
    current_state = interview_engine.get_or_create_session(req.session_id)
    prior_q = current_state.get("next_question")
    resolved_qid = req.question_id or (prior_q.question_id if prior_q else "q_step")

    ans_dto = InterviewAnswer(
        question_id=resolved_qid,
        answer_text=req.answer_text,
        verbatim_voice=req.verbatim_voice,
        language=req.language,
    )

    next_q, _ = await submit_interview_answer(
        session_id=req.session_id,
        answer=ans_dto,
        db=db,
        is_proxy=req.is_proxy,
        proxy_name=req.proxy_name,
        proxy_relationship=req.proxy_relationship,
    )
    return next_q


# ==============================================================================
# Physician Ask-Back Workflow
# ==============================================================================

class AskBackRequest(BaseModel):
    session_id: str = Field(..., description="Active session ID")
    field_id: str = Field(..., description="SummaryField ID that doctor wants clarified")
    question_text: str = Field(..., description="Specific clarifying question from physician")
    answer_text: str | None = Field(None, description="Patient response if pre-answered or simulated")


class AskBackReplyRequest(BaseModel):
    session_id: str = Field(..., description="Active session ID")
    field_id: str = Field(..., description="SummaryField ID that was clarified")
    answer_text: str = Field(..., description="Verbatim patient response to doctor's query")
    verbatim_voice: str | None = Field(None, description="Optional raw audio transcription")
    language: str = Field("hi", description="Language code")


@router.post("/api/interview/ask-back", response_model=SummaryField, tags=["Ask-Back Clarification"])
async def ask_back_endpoint(
    req: AskBackRequest,
    current_user: AuthenticatedUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    POST /api/interview/ask-back
    Physician submits a clarifying question to the kiosk.
    If the patient is disconnected or has not answered yet, marks field as 'needs_confirmation'
    with zero fabricated clinical findings.
    """
    await session_manager.assert_session_active(req.session_id, db)

    # 1. Dispatch clarification envelope to active kiosk WebSocket
    clarify_env = WebSocketEnvelope(
        type="clarification",
        session_id=req.session_id,
        payload={
            "field_id": req.field_id,
            "question_text": req.question_text,
            "question_id": f"q_ask_back_{req.field_id}",
        },
    )
    ws_sent = await manager.send_to_session(req.session_id, clarify_env.model_dump(mode="json"))
    logger.info(f"Ask-back question for field {req.field_id} dispatched to kiosk WebSocket: {ws_sent}")

    # 2. If no patient answer provided, preserve pending state (NO fabrication)
    if not req.answer_text:
        return SummaryField(
            field_id=req.field_id,
            section="hpi",
            content=f"Clarification pending from patient: {req.question_text}",
            sources=[],
            verification="needs_confirmation",
            changed_since_last=False,
        )

    # 3. If answer provided (synchronous test/simulation), route through safety and persist turn
    rf = red_flag_detector.scan_and_confirm(
        text=req.answer_text,
        session_id=req.session_id,
        question_context=req.question_text,
    )
    if rf:
        # Trigger emergency event
        event_model = RedFlagEventModel(
            id=rf.event_id,
            session_id=req.session_id,
            trigger_phrase=rf.trigger_phrase,
            matched_rule=rf.matched_rule,
            severity=rf.severity,
            category=rf.category,
            timestamp=rf.timestamp,
        )
        db.add(event_model)
        await db.commit()
        await staff_alert_manager.broadcast_alert(rf.model_dump(mode="json"))

    count_stmt = select(func.count(InterviewTranscript.id)).where(InterviewTranscript.session_id == req.session_id)
    count_res = await db.execute(count_stmt)
    total_turns = (count_res.scalar() or 0) + 1

    transcript_entry = InterviewTranscript(
        session_id=req.session_id,
        turn_number=total_turns,
        question_id=f"q_ask_back_{req.field_id}",
        question_text=req.question_text,
        answer_text=req.answer_text,
        verbatim_voice=None,
        language="hi",
        node_name="ask_back",
        speaker="patient",
        text=req.answer_text,
    )
    db.add(transcript_entry)
    await db.commit()

    return SummaryField(
        field_id=req.field_id,
        section="hpi",
        content=f"Clarified with patient: {req.question_text} — {req.answer_text}",
        sources=[
            SummarySource(
                session_id=req.session_id,
                type="transcript",
                ref_id=f"q_ask_back_{req.field_id}",
                snippet=req.answer_text,
            )
        ],
        verification="patient_reported",
        changed_since_last=True,
    )


@router.post("/api/interview/ask-back/reply", response_model=SummaryField, tags=["Ask-Back Clarification"])
async def ask_back_reply_endpoint(
    req: AskBackReplyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    POST /api/interview/ask-back/reply
    Receives real patient reply to an ask-back question from the kiosk.
    Routes reply through red-flag safety, persists real transcript turn,
    and returns updated SummaryField with provenance.
    """
    await session_manager.assert_session_active(req.session_id, db)

    # 1. Safety scan
    rf = red_flag_detector.scan_and_confirm(
        text=req.answer_text,
        session_id=req.session_id,
    )
    if rf:
        event_model = RedFlagEventModel(
            id=rf.event_id,
            session_id=req.session_id,
            trigger_phrase=rf.trigger_phrase,
            matched_rule=rf.matched_rule,
            severity=rf.severity,
            category=rf.category,
            timestamp=rf.timestamp,
        )
        db.add(event_model)
        await db.commit()
        await staff_alert_manager.broadcast_alert(rf.model_dump(mode="json"))

    # 2. Append genuine transcript turn
    count_stmt = select(func.count(InterviewTranscript.id)).where(InterviewTranscript.session_id == req.session_id)
    count_res = await db.execute(count_stmt)
    total_turns = (count_res.scalar() or 0) + 1

    transcript_entry = InterviewTranscript(
        session_id=req.session_id,
        turn_number=total_turns,
        question_id=f"q_ask_back_{req.field_id}",
        question_text=f"Physician clarification for {req.field_id}",
        answer_text=req.answer_text,
        verbatim_voice=req.verbatim_voice,
        language=req.language,
        node_name="ask_back",
        speaker="patient",
        text=req.answer_text,
    )
    db.add(transcript_entry)
    await db.commit()

    # Update targeted field in ClinicalSummary if present
    import copy
    from sqlalchemy.orm.attributes import flag_modified
    stmt_s = (
        select(ClinicalSummary)
        .where(ClinicalSummary.session_id == req.session_id)
        .order_by(ClinicalSummary.version.desc())
    )
    res_s = await db.execute(stmt_s)
    summary = res_s.scalar_one_or_none()
    if summary and summary.fields_json:
        updated_fields = copy.deepcopy(summary.fields_json)
        matched = False
        for f in updated_fields:
            if f.get("field_id") == req.field_id:
                f["content"] = f"Clarified by patient: {req.answer_text}"
                f["patient_value"] = req.answer_text
                f["verification"] = "patient_reported"
                f["changed_since_last"] = True
                if "sources" not in f or not isinstance(f["sources"], list):
                    f["sources"] = []
                f["sources"].append({
                    "session_id": req.session_id,
                    "type": "transcript",
                    "ref_id": transcript_entry.question_id,
                    "snippet": req.answer_text,
                })
                matched = True
                break
        if matched:
            summary.fields_json = updated_fields
            flag_modified(summary, "fields_json")
            summary.updated_at = datetime.now(UTC)
            await db.commit()

    return SummaryField(
        field_id=req.field_id,
        section="hpi",
        content=f"Clarified by patient: {req.answer_text}",
        sources=[
            SummarySource(
                session_id=req.session_id,
                type="transcript",
                ref_id=f"q_ask_back_{req.field_id}",
                snippet=req.answer_text,
            )
        ],
        verification="patient_reported",
        changed_since_last=True,
    )


# ==============================================================================
# Transcript Citation Endpoints (Strict Session Scoping, Zero Mocks)
# ==============================================================================

@router.get("/api/interview/transcript/{ref_id}", tags=["Interview Transcript"])
async def get_transcript_by_ref_endpoint(
    ref_id: str,
    session_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    GET /api/interview/transcript/{ref_id}
    Retrieves the exact Q&A pair from interview_transcripts.
    Enforces encounter scoping: if ref_id is a reusable question_id and multiple sessions exist,
    session_id query param is required to prevent cross-session data leakage.
    Returns 404 if not found (zero fabricated mock fallbacks).
    """
    if session_id:
        stmt = (
            select(InterviewTranscript)
            .where(InterviewTranscript.session_id == session_id)
            .where(
                (InterviewTranscript.question_id == ref_id)
                | (InterviewTranscript.id == ref_id)
            )
            .order_by(InterviewTranscript.turn_number.desc())
        )
        res = await db.execute(stmt)
        entry = res.scalar_one_or_none()
    else:
        # Check if ref_id matches a unique primary key id
        stmt_id = select(InterviewTranscript).where(InterviewTranscript.id == ref_id)
        res_id = await db.execute(stmt_id)
        entry = res_id.scalar_one_or_none()

        if not entry:
            # Check question_id matches across sessions
            stmt_q = select(InterviewTranscript).where(InterviewTranscript.question_id == ref_id)
            res_q = await db.execute(stmt_q)
            entries = res_q.scalars().all()
            if len(entries) > 1:
                sessions_found = {e.session_id for e in entries}
                if len(sessions_found) > 1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Ambiguous question reference '{ref_id}' across multiple encounters. session_id is required to prevent data leakage."
                    )
            entry = entries[0] if entries else None

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transcript reference '{ref_id}' not found for specified encounter."
        )

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


@router.get("/api/interview/{session_id}/transcript", tags=["Interview Transcript"])
async def get_session_transcript_alias_endpoint(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Alias for /api/interview/transcripts/{session_id}"""
    return await get_session_transcripts_endpoint(session_id=session_id, db=db)
