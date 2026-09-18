"""
AYUSH Dashavidha Pariksha & Ayurvedic Clinical Lens Endpoints
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
Dev 1 Core AYUSH Route
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import ClinicalSummary, Session
from app.services.ayush_service import (
    DASHHAVIDHA_STAGES,
    evaluate_prakriti_and_dosha,
    generate_ayush_clinical_lens,
)

logger = logging.getLogger("medikiosk.routes.ayush")
router = APIRouter(prefix="/api/ayush", tags=["AYUSH Clinical Track"])


class PrakritiEvaluationRequest(BaseModel):
    session_id: Optional[str] = Field(None, description="Optional active session ID to attach result to")
    answers: Dict[str, Any] = Field(..., description="Stage ID to selected answer text or dosha value")


class ClinicalLensRequest(BaseModel):
    session_id: str = Field(..., description="Active session ID")
    chief_complaint: Optional[str] = Field(None, description="Primary presenting complaint")
    hpi: Optional[Dict[str, Any]] = Field(default_factory=dict, description="HPI elements (site, onset, etc.)")


@router.get("/stages")
async def get_dashavidha_stages():
    """
    GET /api/ayush/stages
    Returns the 10 classical Dashavidha Pariksha assessment stages with bilingual prompts.
    """
    return {
        "count": len(DASHHAVIDHA_STAGES),
        "stages": DASHHAVIDHA_STAGES,
    }


@router.post("/evaluate-prakriti")
async def evaluate_prakriti_endpoint(
    req: PrakritiEvaluationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    POST /api/ayush/evaluate-prakriti
    Computes Prakriti (Vata, Pitta, Kapha percentage scores), primary and secondary Dosha,
    Agni status, and Koshtha bowel constitution.
    """
    result = evaluate_prakriti_and_dosha(req.answers)

    if req.session_id:
        try:
            stmt = select(Session).where(Session.id == req.session_id)
            res = await db.execute(stmt)
            session_row = res.scalar_one_or_none()
            if session_row:
                session_row.prakriti_result = result
                session_row.interview_mode = "ayush"
                await db.commit()
                logger.info(f"Attached Prakriti evaluation to session {req.session_id}")
        except Exception as e:
            logger.warning(f"Unable to persist Prakriti result to session {req.session_id}: {e}")

    return result


@router.post("/clinical-lens")
async def generate_ayush_lens_endpoint(
    req: ClinicalLensRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    POST /api/ayush/clinical-lens
    Generates the classical Ayurvedic 8-fold clinical diagnostic summary:
    Nidana, Purvarupa, Rupa, Upashaya, Samprapti, Agni/Koshtha, Pathya-Apathya, Chikitsa Sootra.
    """
    # 1. Fetch session for prakriti or chief complaint if not passed
    cc = req.chief_complaint or ""
    hpi = req.hpi or {}
    prakriti_data = {}

    try:
        stmt = select(Session).where(Session.id == req.session_id)
        res = await db.execute(stmt)
        sess = res.scalar_one_or_none()
        if sess and sess.prakriti_result:
            prakriti_data = sess.prakriti_result

        # Check existing summary if CC is blank
        if not cc:
            stmt_sum = select(ClinicalSummary).where(ClinicalSummary.session_id == req.session_id)
            res_sum = await db.execute(stmt_sum)
            summary_row = res_sum.scalar_one_or_none()
            if summary_row and summary_row.chief_complaint:
                cc = summary_row.chief_complaint
    except Exception as e:
        logger.warning(f"Error loading session data for AYUSH lens: {e}")

    if not prakriti_data:
        # Default assessment if Prakriti test wasn't completed
        prakriti_data = evaluate_prakriti_and_dosha({"prakriti": "vata", "vikriti": "pitta"})

    lens_result = generate_ayush_clinical_lens(
        chief_complaint=cc,
        hpi=hpi,
        prakriti_result=prakriti_data,
    )

    # Persist in ClinicalSummary
    try:
        stmt_sum = select(ClinicalSummary).where(ClinicalSummary.session_id == req.session_id)
        res_sum = await db.execute(stmt_sum)
        summary_row = res_sum.scalar_one_or_none()
        if summary_row:
            summary_row.lens = "ayurvedic"
            summary_row.ayush_json = lens_result
            await db.commit()
    except Exception as e:
        logger.warning(f"Error saving AYUSH lens to summary: {e}")

    return lens_result


@router.get("/summary/{session_id}")
async def get_ayush_summary_endpoint(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    GET /api/ayush/summary/{session_id}
    Retrieves the persisted Ayurvedic clinical summary for a session.
    """
    stmt = select(ClinicalSummary).where(ClinicalSummary.session_id == session_id)
    res = await db.execute(stmt)
    summary_row = res.scalar_one_or_none()

    if not summary_row or not summary_row.ayush_json:
        # Generate on the fly
        req = ClinicalLensRequest(session_id=session_id)
        return await generate_ayush_lens_endpoint(req, db)

    return summary_row.ayush_json
