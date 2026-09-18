"""
Clinical Intelligence API Routes
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Endpoints:
- POST /api/intelligence/polypharmacy: Evaluates medications for duplicates & interactions
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.polypharmacy_detector import PolypharmacyReport, polypharmacy_detector

logger = logging.getLogger("medikiosk.routes.intelligence")
router = APIRouter(prefix="/api/intelligence", tags=["Clinical Intelligence"])


class PolypharmacyRequest(BaseModel):
    session_id: str = Field(..., description="Active session ID to evaluate medications for")


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
