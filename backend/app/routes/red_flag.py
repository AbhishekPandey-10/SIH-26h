"""
Red-Flag Escalation System: Staff Alert WebSocket & Dismiss/Acknowledge Workflow
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session_factory, get_db
from app.db.models import RedFlagEventModel
from app.dependencies import (
    AuthenticatedUser,
    UserRole,
    authenticate_websocket,
    require_encounter_access,
    require_staff,
)


logger = logging.getLogger("medikiosk.red_flag_routes")
router = APIRouter(tags=["Red Flag Safety & Staff Escalation"])


class StaffAlertManager:
    """Manages active WebSocket connections for OPD triage nurses and staff alert dashboards."""

    def __init__(self):
        self.active_staff: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_staff.append(websocket)
        logger.info(f"Staff alert dashboard connected (total connected: {len(self.active_staff)})")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_staff:
            self.active_staff.remove(websocket)
            logger.info("Staff alert dashboard disconnected")

    async def broadcast_alert(self, alert_data: Dict[str, Any]) -> int:
        """Broadcast emergency red-flag alert to all active staff consoles."""
        payload = json.dumps({
            "event": "red_flag_alert",
            "data": alert_data,
            "timestamp": datetime.now(UTC).isoformat(),
        })
        dead = []
        sent_count = 0
        for ws in self.active_staff:
            try:
                await ws.send_text(payload)
                sent_count += 1
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)
        return sent_count


staff_alert_manager = StaffAlertManager()


@router.websocket("/ws/staff-alerts")
async def staff_alerts_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for triage staff consoles and nurse station displays.
    Requires authenticated staff credentials (token in query param, header, or Bearer).
    Receives real-time red_flag_alert events with high-priority audio chime signals.
    Automatically replays all active unacknowledged/undismissed alerts upon connection.
    """
    user = await authenticate_websocket(websocket, allowed_roles=(UserRole.STAFF,))
    if not user:
        return

    await staff_alert_manager.connect(websocket)

    # Durable replay of all unresolved (is_dismissed=False) emergency alerts
    try:
        async with async_session_factory() as db:
            stmt = (
                select(RedFlagEventModel)
                .where(RedFlagEventModel.is_dismissed.is_(False))
                .order_by(RedFlagEventModel.timestamp.asc())
            )
            res = await db.execute(stmt)
            active_events = res.scalars().all()
            for ev in active_events:
                replay_payload = {
                    "event": "red_flag_alert",
                    "is_replay": True,
                    "data": {
                        "event_id": ev.id,
                        "session_id": ev.session_id,
                        "trigger_phrase": ev.trigger_phrase,
                        "severity": ev.severity,
                        "category": ev.category,
                        "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
                        "is_acknowledged": ev.is_acknowledged,
                        "acknowledged_by": ev.acknowledged_by,
                    },
                }
                await websocket.send_text(json.dumps(replay_payload, ensure_ascii=False))
    except Exception as e:
        logger.warning(f"Error replaying active alerts to staff console: {e}")

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"event": "pong"}))
    except WebSocketDisconnect:
        staff_alert_manager.disconnect(websocket)
    except Exception as e:
        staff_alert_manager.disconnect(websocket)
        logger.warning(f"Error in staff alerts websocket: {e}")


class DismissRedFlagRequest(BaseModel):
    dismissed_by: Optional[str] = Field(None, description="Staff identifier (overridden by authenticated staff identity)")
    reason: str = Field(..., description="Clinical justification for dismissing red flag")


class AcknowledgeRedFlagRequest(BaseModel):
    acknowledged_by: Optional[str] = Field(None, description="Staff identifier (overridden by authenticated staff identity)")
    action_taken: str = Field("Triage nurse dispatched to kiosk", description="Emergency action taken")


@router.post("/api/red-flag/{event_id}/dismiss")
async def dismiss_red_flag_endpoint(
    event_id: str,
    req: DismissRedFlagRequest,
    current_user: AuthenticatedUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    POST /api/red-flag/{event_id}/dismiss
    Staff override: dismisses red flag safety pause and records audit justification.
    Checks for any other active unresolved red flags on the encounter:
    Resumes kiosk ONLY if all active alerts for this session have been resolved.
    """
    stmt = select(RedFlagEventModel).where(RedFlagEventModel.id == event_id)
    res = await db.execute(stmt)
    event = res.scalar_one_or_none()

    if not event:
        raise HTTPException(status_code=404, detail="Red flag event not found")

    staff_id = current_user.user_id

    event.is_dismissed = True
    event.dismissed_by = staff_id
    event.dismiss_reason = req.reason
    await db.commit()

    # Query for any other unresolved red flags for this session
    stmt_remain = (
        select(func.count(RedFlagEventModel.id))
        .where(
            RedFlagEventModel.session_id == event.session_id,
            RedFlagEventModel.is_dismissed.is_(False),
            RedFlagEventModel.id != event_id,
        )
    )
    res_remain = await db.execute(stmt_remain)
    remaining_active = res_remain.scalar() or 0

    resumed = False
    if remaining_active == 0:
        # Clear paused state in interview engine
        from app.services.interview_engine import interview_engine
        sess_state = interview_engine.sessions.get(event.session_id)
        if sess_state:
            sess_state["is_paused"] = False
            sess_state["paused_reason"] = None

        # Resume kiosk interview via active interview WebSocket
        from app.routes.interview import manager as interview_ws_manager
        resumed = await interview_ws_manager.send_to_session(
            event.session_id,
            {
                "event": "interview_resume",
                "event_id": event_id,
                "session_id": event.session_id,
                "message": "Staff verified and cleared safety hold. Resuming intake.",
                "dismissed_by": staff_id,
            }
        )
        logger.info(f"Red flag {event_id} dismissed by staff {staff_id}. All alerts resolved; kiosk resume sent: {resumed}")
    else:
        logger.info(
            f"Red flag {event_id} dismissed by staff {staff_id}, but {remaining_active} other active "
            f"alert(s) remain for session {event.session_id}. Session remains held."
        )

    return {
        "success": True,
        "event_id": event_id,
        "status": "dismissed",
        "resumed": (remaining_active == 0),
        "resumed_kiosk": resumed,
        "remaining_active_alerts": remaining_active,
        "dismissed_by": staff_id,
        "reason": req.reason,
    }


@router.post("/api/red-flag/{event_id}/acknowledge")
async def acknowledge_red_flag_endpoint(
    event_id: str,
    req: AcknowledgeRedFlagRequest,
    current_user: AuthenticatedUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    POST /api/red-flag/{event_id}/acknowledge
    Staff acknowledges alert. Kiosk remains paused and shows "A doctor is coming to see you".
    Binds acknowledged_by to the authenticated staff identity.
    Acknowledgement does NOT dismiss the hold or clear active red flags.
    """
    stmt = select(RedFlagEventModel).where(RedFlagEventModel.id == event_id)
    res = await db.execute(stmt)
    event = res.scalar_one_or_none()

    if not event:
        raise HTTPException(status_code=404, detail="Red flag event not found")

    staff_id = current_user.user_id

    event.is_acknowledged = True
    event.acknowledged_by = staff_id
    event.action_taken = req.action_taken
    await db.commit()

    # Send status update to kiosk (maintaining pause)
    from app.routes.interview import manager as interview_ws_manager
    await interview_ws_manager.send_to_session(
        event.session_id,
        {
            "event": "red_flag_acknowledged",
            "event_id": event_id,
            "message": "A medical professional has been assigned and is attending to you immediately.",
            "acknowledged_by": staff_id,
            "action_taken": req.action_taken,
        }
    )


    logger.info(f"Red flag {event_id} acknowledged by authenticated staff {staff_id}.")

    return {
        "success": True,
        "event_id": event_id,
        "status": "acknowledged",
        "acknowledged_by": staff_id,
        "action_taken": req.action_taken,
    }




@router.get("/api/red-flag/events/{session_id}")
async def get_session_red_flags_endpoint(
    session_id: str,
    current_user: AuthenticatedUser = Depends(require_encounter_access),
    db: AsyncSession = Depends(get_db),
):
    """
    GET /api/red-flag/events/{session_id}
    Retrieves all red-flag safety events logged for a session.
    Requires session access or staff role.
    """
    stmt = (
        select(RedFlagEventModel)
        .where(RedFlagEventModel.session_id == session_id)
        .order_by(RedFlagEventModel.timestamp.desc())
    )
    res = await db.execute(stmt)
    events = res.scalars().all()
    return [
        {
            "id": e.id,
            "session_id": e.session_id,
            "trigger_phrase": e.trigger_phrase,
            "matched_rule": e.matched_rule,
            "severity": e.severity,
            "category": e.category,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "is_dismissed": e.is_dismissed,
            "dismissed_by": e.dismissed_by,
            "dismiss_reason": e.dismiss_reason,
            "is_acknowledged": e.is_acknowledged,
            "acknowledged_by": e.acknowledged_by,
            "action_taken": e.action_taken,
        }
        for e in events
    ]
