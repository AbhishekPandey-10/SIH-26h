"""
Intelligence Endpoints: Contradiction Radar & Polypharmacy Alerting
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.contradiction_detector import contradiction_detector
from app.services.polypharmacy import polypharmacy_service
from app.shared.schemas import ContradictionItem, PolypharmacyAlert

logger = logging.getLogger("medikiosk.routes.intelligence")
router = APIRouter(prefix="/api/intelligence", tags=["Clinical Intelligence & Contradiction Radar"])


class ContradictionRequest(BaseModel):
    session_id: str = Field(..., description="Active kiosk encounter session UUID")


class ContradictionResponse(BaseModel):
    session_id: str
    count: int
    delta_summary: str
    contradictions: List[ContradictionItem]


class ContradictionActionRequest(BaseModel):
    contradiction_id: str = Field(..., description="Unique ID of the contradiction card")
    action: str = Field(..., description="'confirm' (acknowledges change) or 'flag_error' (flags potential error)")


class PolypharmacyRequest(BaseModel):
    session_id: str = Field(..., description="Active kiosk encounter session UUID")


class PolypharmacyResponse(BaseModel):
    session_id: str
    alert_count: int
    alerts: List[PolypharmacyAlert]


@router.post("/contradictions", response_model=ContradictionResponse)
async def get_contradictions_endpoint(
    req: ContradictionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    POST /api/intelligence/contradictions
    Compares current interview answers with historical extracted documents.
    Detects dosage changes, started/stopped medications, new diagnoses, and lab discrepancies.
    """
    try:
        items = await contradiction_detector.detect_contradictions(req.session_id, db)
        delta_str = contradiction_detector.format_delta_summary(items)

        return ContradictionResponse(
            session_id=req.session_id,
            count=len(items),
            delta_summary=delta_str,
            contradictions=items,
        )
    except Exception as e:
        logger.error(f"Error executing contradiction detection for session {req.session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/contradictions/{session_id}/action")
async def act_on_contradiction_endpoint(
    session_id: str,
    req: ContradictionActionRequest,
):
    """
    POST /api/intelligence/contradictions/{session_id}/action
    Doctor action on a contradiction card:
    - 'confirm': marks as acknowledged, validates change
    - 'flag_error': keeps both values with a clinical warning badge
    """
    if req.action not in ["confirm", "flag_error"]:
        raise HTTPException(status_code=400, detail="Action must be 'confirm' or 'flag_error'")

    contradiction_detector.record_doctor_action(
        session_id=session_id,
        contradiction_id=req.contradiction_id,
        action="confirmed" if req.action == "confirm" else "flagged_error",
    )
    return {
        "session_id": session_id,
        "contradiction_id": req.contradiction_id,
        "action": req.action,
        "status": "acknowledged" if req.action == "confirm" else "flagged_as_error",
    }


@router.post("/polypharmacy", response_model=PolypharmacyResponse)
async def get_polypharmacy_endpoint(
    req: PolypharmacyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    POST /api/intelligence/polypharmacy
    Scans active medications across prescriptions and patient statements.
    Detects duplicate brand molecules and contraindicated interaction pairs.
    """
    try:
        alerts = await polypharmacy_service.detect_polypharmacy_alerts(req.session_id, db)
        return PolypharmacyResponse(
            session_id=req.session_id,
            alert_count=len(alerts),
            alerts=alerts,
        )
    except Exception as e:
        logger.error(f"Error analyzing polypharmacy for session {req.session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
