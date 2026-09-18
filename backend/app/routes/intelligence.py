"""
Clinical Intelligence & Contradiction Radar API Routes
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Endpoints:
- POST /api/intelligence/contradictions: Compares interview vs document records
- POST /api/intelligence/contradictions/{session_id}/action: Doctor confirms or flags contradiction
- POST /api/intelligence/polypharmacy: Evaluates medications for duplicates & interactions
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.contradiction_detector import contradiction_detector
from app.services.polypharmacy_detector import PolypharmacyReport, polypharmacy_detector
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
    session_id: str = Field(..., description="Active session ID to evaluate medications for")


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


@router.post("/polypharmacy", response_model=PolypharmacyReport)
async def evaluate_polypharmacy_endpoint(
    req: PolypharmacyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    POST /api/intelligence/polypharmacy
    Extracts all medications from interview answers and document entities,
    maps brand names to generic molecules, and flags duplicate active ingredients
    and dangerous drug-drug interactions.
    """
    try:
        report = await polypharmacy_detector.detect_polypharmacy(session_id=req.session_id, db=db)
        logger.info(
            f"Polypharmacy check for session {req.session_id}: "
            f"{len(report.duplicates)} duplicates, {len(report.interactions)} interactions."
        )
        return report
    except Exception as e:
        logger.error(f"Error analyzing polypharmacy for session {req.session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Polypharmacy analysis failed: {str(e)}")
