"""
Clinical Summary API Endpoints
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.summary_generator import summary_generator
from app.shared.schemas import SummaryField

logger = logging.getLogger("medikiosk.routes.summary")
router = APIRouter(prefix="/api/summary", tags=["Clinical Summary"])


class SummaryGenerateRequest(BaseModel):
    session_id: str = Field(..., description="Active kiosk session identifier")


@router.post("/generate", response_model=List[SummaryField])
async def generate_summary_endpoint(
    req: SummaryGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a physician-ready structured summary from interview transcript
    and scanned document entities.
    """
    try:
        fields = await summary_generator.generate_summary(
            session_id=req.session_id,
            db=db,
        )
        return fields
    except Exception as e:
        logger.error(f"Failed to generate clinical summary for session {req.session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Summary generation error: {str(e)}")
