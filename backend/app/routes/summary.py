"""
Clinical Summary API Endpoints & Doctor Field Review
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""

import copy
import logging
from datetime import UTC, datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.db.database import get_db
from app.db.models import ClinicalSummary, SummaryResolution
from app.dependencies import (
    AuthenticatedUser,
    UserRole,
    check_effective_consent,
    require_authenticated_user,
    require_staff,
)
from app.services.summary_generator import summary_generator
from app.shared.schemas import ResolveFieldRequest, SummaryField

logger = logging.getLogger("medikiosk.routes.summary")
router = APIRouter(prefix="/api/summary", tags=["Clinical Summary"])


class SummaryGenerateRequest(BaseModel):
    session_id: str = Field(..., description="Active kiosk session identifier")
    lens: str = Field("allopathic", description="Clinical summary lens: 'allopathic' or 'ayurvedic'")


class UpdateSummaryFieldRequest(BaseModel):
    content: str = Field(..., description="Updated field text verified/edited by doctor")
    doctor_notes: str | None = Field(None, description="Optional physician annotation")


class VerifySummaryRequest(BaseModel):
    doctor_notes: str | None = Field(None, description="Optional physician sign-off note")


@router.post("/generate", response_model=List[SummaryField])
async def generate_summary_endpoint(
    req: SummaryGenerateRequest,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a physician-ready structured summary from interview transcript
    and scanned document entities. Supports 'allopathic' and 'ayurvedic' clinical lenses.
    Requires session access and effective consent for 'share_doctor'.
    """
    if current_user.role != UserRole.STAFF and current_user.session_id and current_user.session_id != req.session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Access denied to encounter session {req.session_id}.",
        )

    await check_effective_consent(req.session_id, "share_doctor", db)

    try:
        fields = await summary_generator.generate_summary(
            session_id=req.session_id,
            db=db,
            lens=req.lens,
        )
        return fields
    except Exception as e:
        logger.error(f"Failed to generate clinical summary for session {req.session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Summary generation error: {str(e)}")


@router.get("/{session_id}", response_model=List[SummaryField])
async def get_summary_endpoint(
    session_id: str,
    lens: str = "allopathic",
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """
    GET /api/summary/{session_id}?lens=allopathic|ayurvedic
    Retrieves the clinical summary fields for a session.
    Strictly read-only: does not auto-regenerate or mutate database state.
    Requires encounter authorization and effective patient consent for 'share_doctor'.
    """
    if current_user.role != UserRole.STAFF and current_user.session_id and current_user.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Access denied to encounter session {session_id}.",
        )

    # Consent gate
    await check_effective_consent(session_id, "share_doctor", db)

    stmt = (
        select(ClinicalSummary)
        .where(ClinicalSummary.session_id == session_id)
        .order_by(ClinicalSummary.version.desc())
    )
    res = await db.execute(stmt)
    summaries = list(res.scalars().all())

    if not summaries:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No clinical summary found for session {session_id}. Please generate a summary first.",
        )

    # Return summary matching lens if available, otherwise latest version
    matching = next((s for s in summaries if s.lens == lens and s.fields_json), summaries[0])
    if matching and matching.fields_json:
        return [SummaryField.model_validate(f) for f in matching.fields_json]

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Summary content empty for session {session_id}.",
    )


@router.put("/{session_id}/field/{field_id}", response_model=SummaryField)
async def update_summary_field_endpoint(
    session_id: str,
    field_id: str,
    req: UpdateSummaryFieldRequest,
    current_user: AuthenticatedUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    PUT /api/summary/{session_id}/field/{field_id}
    Inline editing for doctors. Requires authenticated staff role.
    Uses deep copy and flag_modified to guarantee reliable JSON column persistence.
    Marks edited field as 'doctor_edited' and transitions summary status to 'in_review'.
    """
    stmt = (
        select(ClinicalSummary)
        .where(ClinicalSummary.session_id == session_id)
        .order_by(ClinicalSummary.version.desc())
    )
    res = await db.execute(stmt)
    summary = res.scalar_one_or_none()

    if not summary or not summary.fields_json:
        raise HTTPException(status_code=404, detail="Summary not found for session")

    # Locate and edit field in deep-copied fields_json
    updated_fields = copy.deepcopy(summary.fields_json)
    matched_field = None
    for field_dict in updated_fields:
        if field_dict.get("field_id") == field_id:
            if "original_content" not in field_dict:
                field_dict["original_content"] = field_dict.get("content", "")

            field_dict["content"] = req.content
            field_dict["verification"] = "doctor_edited"
            field_dict["changed_since_last"] = True
            matched_field = field_dict
            break

    if not matched_field:
        raise HTTPException(status_code=404, detail=f"Field {field_id} not found in summary")

    summary.fields_json = updated_fields
    flag_modified(summary, "fields_json")

    # Granular status: single field edit transitions draft to in_review, not whole-summary verified
    if summary.status == "draft":
        summary.status = "in_review"
    summary.updated_at = datetime.now(UTC)
    if req.doctor_notes:
        summary.doctor_notes = req.doctor_notes

    await db.commit()
    await db.refresh(summary)
    logger.info(f"Physician {current_user.user_id} updated field {field_id} for session {session_id}")
    return SummaryField.model_validate(matched_field)


@router.post("/{session_id}/resolve/{field_id}", response_model=SummaryField)
async def resolve_summary_field_endpoint(
    session_id: str,
    field_id: str,
    req: ResolveFieldRequest,
    current_user: AuthenticatedUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    POST /api/summary/{session_id}/resolve/{field_id}
    Doctor resolves a conflicting summary field.
    Binds doctor identity to the authenticated staff caller.
    Logs the resolution in summary_resolutions table for DPDP Act auditability.
    Uses deep copy and flag_modified for bulletproof JSON persistence.
    """
    doctor_id = current_user.user_id

    stmt = (
        select(ClinicalSummary)
        .where(ClinicalSummary.session_id == session_id)
        .order_by(ClinicalSummary.version.desc())
    )
    res = await db.execute(stmt)
    summary = res.scalar_one_or_none()

    if not summary or not summary.fields_json:
        raise HTTPException(status_code=404, detail="Summary not found for session")

    updated_fields = copy.deepcopy(summary.fields_json)
    matched_field = None
    for field_dict in updated_fields:
        if field_dict.get("field_id") == field_id:
            if "original_content" not in field_dict:
                field_dict["original_content"] = field_dict.get("content", "")

            # Log audit record in summary_resolutions
            resolution_log = SummaryResolution(
                session_id=session_id,
                field_id=field_id,
                doctor_id=doctor_id,
                resolution_choice=req.resolution_choice,
                document_value=field_dict.get("document_value"),
                patient_value=field_dict.get("patient_value"),
                resolved_value=req.resolved_value,
                doctor_note=req.doctor_note,
            )
            db.add(resolution_log)

            field_dict["content"] = req.resolved_value
            field_dict["verification"] = "doctor_edited"
            field_dict["changed_since_last"] = True
            field_dict["resolution"] = {
                "choice": req.resolution_choice,
                "doctor_id": doctor_id,
                "resolved_value": req.resolved_value,
            }
            matched_field = field_dict
            break

    if not matched_field:
        raise HTTPException(status_code=404, detail=f"Field {field_id} not found in summary")

    summary.fields_json = updated_fields
    flag_modified(summary, "fields_json")

    # Transition to in_review
    if summary.status == "draft":
        summary.status = "in_review"
    summary.updated_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(summary)

    logger.info(f"Doctor {doctor_id} resolved conflicting field {field_id} with choice: {req.resolution_choice}")
    return SummaryField.model_validate(matched_field)


@router.post("/{session_id}/verify")
async def verify_summary_endpoint(
    session_id: str,
    req: VerifySummaryRequest | None = None,
    current_user: AuthenticatedUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    POST /api/summary/{session_id}/verify
    Explicit physician sign-off certifying that the summary has been fully reviewed.
    Sets summary status to 'doctor_verified' and records certifying physician identity.
    """
    stmt = (
        select(ClinicalSummary)
        .where(ClinicalSummary.session_id == session_id)
        .order_by(ClinicalSummary.version.desc())
    )
    res = await db.execute(stmt)
    summary = res.scalar_one_or_none()

    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found for session")

    summary.status = "doctor_verified"
    summary.updated_at = datetime.now(UTC)
    if req and req.doctor_notes:
        summary.doctor_notes = req.doctor_notes

    await db.commit()
    await db.refresh(summary)
    logger.info(f"Physician {current_user.user_id} certified summary for session {session_id}")
    return {
        "session_id": session_id,
        "version": summary.version,
        "status": summary.status,
        "verified_by": current_user.user_id,
        "updated_at": summary.updated_at.isoformat(),
    }
