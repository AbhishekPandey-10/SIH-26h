"""
Red-Flag Escalation System: Staff Alert WebSocket & Dismiss/Acknowledge Workflow
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import RedFlagEventModel
from app.routes.interview import manager as interview_ws_manager

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

    async def broadcast_alert(self, alert_data: Dict[str, Any]):
        """Broadcast emergency red-flag alert to all active staff consoles."""
        payload = json.dumps({
            "event": "red_flag_alert",
            "data": alert_data,
            "timestamp": datetime.now(UTC).isoformat(),
        })
        dead = []
        for ws in self.active_staff:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


staff_alert_manager = StaffAlertManager()


@router.websocket("/ws/staff-alerts")
async def staff_alerts_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for triage staff consoles and nurse station displays.
    Receives real-time red_flag_alert events with high-priority audio chime signals.
    """
    await staff_alert_manager.connect(websocket)
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
    dismissed_by: str = Field(..., description="Staff/Triage nurse identifier")
    reason: str = Field(..., description="Clinical justification for dismissing red flag")


class AcknowledgeRedFlagRequest(BaseModel):
    acknowledged_by: str = Field(..., description="Staff identifier who acknowledged alert")
    action_taken: str = Field("Triage nurse dispatched to kiosk", description="Emergency action taken")


@router.post("/api/red-flag/{event_id}/dismiss")
async def dismiss_red_flag_endpoint(
    event_id: str,
    req: DismissRedFlagRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    POST /api/red-flag/{event_id}/dismiss
    Staff override: dismisses red flag safety pause, records audit justification,
    and resumes kiosk interview session.
    """
    stmt = select(RedFlagEventModel).where(RedFlagEventModel.id == event_id)
    res = await db.execute(stmt)
    event = res.scalar_one_or_none()

    if not event:
        raise HTTPException(status_code=404, detail="Red flag event not found")

    event.is_dismissed = True
    event.dismissed_by = req.dismissed_by
    event.dismiss_reason = req.reason
    await db.commit()

    # Resume kiosk interview via active interview WebSocket
    resumed = await interview_ws_manager.send_to_session(
        event.session_id,
        {
            "event": "interview_resume",
            "event_id": event_id,
            "session_id": event.session_id,
            "message": "Staff verified and cleared safety hold. Resuming intake.",
            "dismissed_by": req.dismissed_by,
        }
    )
    logger.info(f"Red flag {event_id} dismissed by {req.dismissed_by}. Kiosk resume sent: {resumed}")

    return {
        "event_id": event_id,
        "status": "dismissed",
        "resumed_kiosk": resumed,
        "dismissed_by": req.dismissed_by,
        "reason": req.reason,
    }


@router.post("/api/red-flag/{event_id}/acknowledge")
async def acknowledge_red_flag_endpoint(
    event_id: str,
    req: AcknowledgeRedFlagRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    POST /api/red-flag/{event_id}/acknowledge
    Staff acknowledges alert. Kiosk remains paused and shows "A doctor is coming to see you".
    """
    stmt = select(RedFlagEventModel).where(RedFlagEventModel.id == event_id)
    res = await db.execute(stmt)
    event = res.scalar_one_or_none()

    if not event:
        raise HTTPException(status_code=404, detail="Red flag event not found")

    # Send status update to kiosk
    await interview_ws_manager.send_to_session(
        event.session_id,
        {
            "event": "red_flag_acknowledged",
            "event_id": event_id,
            "message": "A medical professional has been assigned and is attending to you immediately.",
            "acknowledged_by": req.acknowledged_by,
            "action_taken": req.action_taken,
        }
    )

    return {
        "event_id": event_id,
        "status": "acknowledged",
        "acknowledged_by": req.acknowledged_by,
        "action_taken": req.action_taken,
    }


@router.get("/api/red-flag/events/{session_id}")
async def get_session_red_flags_endpoint(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    GET /api/red-flag/events/{session_id}
    Retrieves all red-flag safety events logged for a session.
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
        }
        for e in events
    ]
