"""
FHIR R4 & ABDM Gateway Endpoints
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import ClinicalSummary
from app.services.abdm_push import abdm_push_service
from app.services.fhir_builder import fhir_builder
from app.services.summary_generator import summary_generator
from app.shared.schemas import SummaryField

logger = logging.getLogger("medikiosk.routes.fhir")
router = APIRouter(prefix="/api/fhir", tags=["FHIR & ABDM"])


class FHIRPushRequest(BaseModel):
    session_id: str = Field(..., description="Active session ID")
    patient_abha_id: str = Field(default="rajesh.kumar@abdm", description="Patient ABHA identifier")
    bundle: Dict[str, Any] | None = Field(default=None, description="Optional pre-generated FHIR bundle")


class FHIRPushResponse(BaseModel):
    success: bool
    abdm_ref: str | None = None
    error: str | None = None
    queue_id: str | None = None
    message: str | None = None


@router.post("/push", response_model=FHIRPushResponse)
async def push_fhir_bundle_endpoint(
    req: FHIRPushRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate (if needed) and push standard FHIR R4 Bundle to ABDM gateway.
    Falls back gracefully to fhir_push_queue if ABDM sandbox is unavailable.
    """
    try:
        bundle = req.bundle

        # Generate bundle if not provided
        if not bundle:
            # Check if summary already generated in DB
            stmt = select(ClinicalSummary).where(ClinicalSummary.session_id == req.session_id)
            res = await db.execute(stmt)
            summary_row = res.scalar_one_or_none()

            if summary_row and summary_row.fields_json:
                fields = [SummaryField.model_validate(f) for f in summary_row.fields_json]
            else:
                fields = await summary_generator.generate_summary(req.session_id, db)

            bundle = fhir_builder.build_bundle(
                session_id=req.session_id,
                summary_fields=fields,
                patient_abha_id=req.patient_abha_id,
            )

        result = await abdm_push_service.push_bundle(
            session_id=req.session_id,
            bundle=bundle,
            db=db,
        )

        return FHIRPushResponse(
            success=result.get("success", False),
            abdm_ref=result.get("abdm_ref"),
            error=result.get("error"),
            queue_id=result.get("queue_id"),
            message=result.get("message"),
        )
    except Exception as e:
        logger.error(f"Error in FHIR push: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preview/{session_id}")
async def get_fhir_preview_endpoint(
    session_id: str,
    patient_abha_id: str = "rajesh.kumar@abdm",
    db: AsyncSession = Depends(get_db),
):
    """
    GET /api/fhir/preview/{session_id}
    Builds and returns the FHIR R4 Bundle JSON preview without pushing to ABDM gateway.
    """
    stmt = select(ClinicalSummary).where(ClinicalSummary.session_id == session_id)
    res = await db.execute(stmt)
    summary_row = res.scalar_one_or_none()

    if summary_row and summary_row.fields_json:
        fields = [SummaryField.model_validate(f) for f in summary_row.fields_json]
    else:
        fields = await summary_generator.generate_summary(session_id, db)

    bundle = fhir_builder.build_bundle(
        session_id=session_id,
        summary_fields=fields,
        patient_abha_id=patient_abha_id,
    )
    return bundle


@router.post("/retry-queue")
async def process_retry_queue(db: AsyncSession = Depends(get_db)):
    """
    POST /api/fhir/retry-queue
    Drains the fhir_push_queue table: re-attempts push for all failed entries.
    Called on network reconnect or manually by staff.
    """
    from app.db.models import FHIRPushQueue

    stmt = select(FHIRPushQueue).where(FHIRPushQueue.status == "failed")
    res = await db.execute(stmt)
    pending = list(res.scalars().all())

    if not pending:
        return {"processed": 0, "message": "No pending items in retry queue."}

    results = []
    for entry in pending:
        try:
            push_result = await abdm_push_service.push_bundle(
                session_id=entry.session_id,
                bundle=entry.bundle_json,
                db=db,
            )
            if push_result.get("success"):
                entry.status = "pushed"
                results.append({"queue_id": entry.id, "status": "pushed"})
            else:
                entry.retry_count += 1
                entry.last_error = push_result.get("error", "Unknown")
                results.append({"queue_id": entry.id, "status": "retry_failed", "retry_count": entry.retry_count})
        except Exception as e:
            entry.retry_count += 1
            entry.last_error = str(e)
            results.append({"queue_id": entry.id, "status": "error", "error": str(e)})

    await db.commit()
    return {
        "processed": len(results),
        "results": results,
    }

