"""
Clinical Summary API Endpoints & Doctor Field Review
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import ClinicalSummary
from app.services.summary_generator import summary_generator
from app.shared.schemas import SummaryField

logger = logging.getLogger("medikiosk.routes.summary")
router = APIRouter(prefix="/api/summary", tags=["Clinical Summary"])


class SummaryGenerateRequest(BaseModel):
    session_id: str = Field(..., description="Active kiosk session identifier")


class UpdateSummaryFieldRequest(BaseModel):
    content: str = Field(..., description="Updated field text verified/edited by doctor")
    doctor_notes: str | None = Field(None, description="Optional physician annotation")


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


@router.get("/{session_id}", response_model=List[SummaryField])
async def get_summary_endpoint(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    GET /api/summary/{session_id}
    Retrieves the existing clinical summary fields for a session.
    Generates summary on-the-fly if not already persisted.
    """
    stmt = (
        select(ClinicalSummary)
        .where(ClinicalSummary.session_id == session_id)
        .order_by(ClinicalSummary.version.desc())
    )
    res = await db.execute(stmt)
    summary = res.scalar_one_or_none()

    if summary and summary.fields_json:
        return [SummaryField.model_validate(f) for f in summary.fields_json]

    # Generate if not exists
    return await summary_generator.generate_summary(session_id=session_id, db=db)


@router.put("/{session_id}/field/{field_id}", response_model=SummaryField)
async def update_summary_field_endpoint(
    session_id: str,
    field_id: str,
    req: UpdateSummaryFieldRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    PUT /api/summary/{session_id}/field/{field_id}
    Inline editing for doctors. Updates content, marks verification as 'doctor_edited',
    and tracks audit history.
    """
    stmt = (
        select(ClinicalSummary)
        .where(ClinicalSummary.session_id == session_id)
        .order_by(ClinicalSummary.version.desc())
    )
    res = await db.execute(stmt)
    summary = res.scalar_one_or_none()

    if not summary or not summary.fields_json:
        # Generate summary first if missing
        await summary_generator.generate_summary(session_id=session_id, db=db)
        res = await db.execute(stmt)
        summary = res.scalar_one_or_none()
        if not summary or not summary.fields_json:
            raise HTTPException(status_code=404, detail="Summary not found for session")

    # Locate field in fields_json
    matched_field = None
    updated_fields = []
    for field_dict in summary.fields_json:
        if field_dict.get("field_id") == field_id:
            # Preserve original content if first time editing
            if "original_content" not in field_dict:
                field_dict["original_content"] = field_dict.get("content", "")

            field_dict["content"] = req.content
            field_dict["verification"] = "doctor_edited"
            field_dict["changed_since_last"] = True
            matched_field = field_dict
        updated_fields.append(field_dict)

    if not matched_field:
        raise HTTPException(status_code=404, detail=f"Field {field_id} not found in summary")

    summary.fields_json = updated_fields
    summary.status = "doctor_verified"
    if req.doctor_notes:
        summary.doctor_notes = req.doctor_notes

    await db.commit()
    logger.info(f"Physician updated field {field_id} for session {session_id}")
    return SummaryField.model_validate(matched_field)
