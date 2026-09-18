"""
Longitudinal Clinical Visualizations API Routes
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Endpoints:
- GET /api/visualization/timeline/{patient_id}: Multi-lane chronological patient journey
- GET /api/visualization/lab-trends/{patient_id}?test=hba1c: Longitudinal lab sparklines with normal/abnormal zones & unit guards
- GET /api/visualization/what-changed/{session_id}: Compact "What Changed" delta card
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.visualization_service import visualization_service

logger = logging.getLogger("medikiosk.routes.visualization")
router = APIRouter(prefix="/api/visualization", tags=["Longitudinal Clinical Visualizations"])


@router.get("/timeline/{patient_id}")
async def get_patient_timeline_endpoint(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    GET /api/visualization/timeline/{patient_id}
    Retrieves cross-session chronological swim lanes (Diagnoses, Medications, Labs, Procedures)
    for interactive timeline rendering.
    """
    try:
        data = await visualization_service.get_timeline(patient_id=patient_id, db=db)
        return data
    except Exception as e:
        logger.error(f"Error compiling timeline for patient {patient_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate timeline: {str(e)}")


@router.get("/lab-trends/{patient_id}")
async def get_lab_trends_endpoint(
    patient_id: str,
    test: str = Query("hba1c", description="Test name or alias, e.g. 'hba1c', 'creatinine', 'hemoglobin'"),
    db: AsyncSession = Depends(get_db),
):
    """
    GET /api/visualization/lab-trends/{patient_id}?test=hba1c
    Retrieves chronological data points for a specific lab parameter,
    including physiological normal reference range zones and unit verification exclusion flags.
    """
    try:
        data = await visualization_service.get_lab_trends(patient_id=patient_id, test_query=test, db=db)
        return data
    except Exception as e:
        logger.error(f"Error fetching lab trends for patient {patient_id} test {test}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve lab trends: {str(e)}")


@router.get("/what-changed/{session_id}")
async def get_what_changed_endpoint(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    GET /api/visualization/what-changed/{session_id}
    Retrieves compact "What Changed" delta view comparing current encounter
    findings and statements against previous documented OPD visits.
    """
    try:
        data = await visualization_service.get_what_changed(session_id=session_id, db=db)
        return data
    except Exception as e:
        logger.error(f"Error building delta view for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to compute delta summary: {str(e)}")
