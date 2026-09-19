"""
Consent-Bound FHIR R4 Export Endpoints
PS ID26047 — Assignment 6

Design invariants:
- Patient/encounter identity resolved from authorized database records.
- Effective store_abdm consent required and revalidated at dispatch time.
- Clinician affirmation (doctor_verified summary) required before export.
- Server builds FHIR bundle from reviewed snapshot; client-supplied bundles rejected.
- One durable export job per idempotency key (session_id:version).
- Retry updates same row, never creates duplicates.
- Preview does NOT imply consent, sign-off, or delivery.
"""

import logging
from datetime import UTC, datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

HTTP_422 = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)

from app.db.database import get_db
from app.db.models import ClinicalSummary, ConsentAudit, FHIRPushQueue, Patient, Session
from app.dependencies import (
    AuthenticatedUser,
    check_effective_consent,
    require_staff,
)
from app.services.abdm_push import export_queue
from app.services.fhir_builder import fhir_builder
from app.shared.schemas import (
    FHIRExportRequest,
    FHIRExportResponse,
    FHIRPreviewResponse,
    SummaryField,
)

logger = logging.getLogger("medikiosk.routes.fhir")
router = APIRouter(prefix="/api/fhir", tags=["FHIR & ABDM Export"])


class ExportJobStatus(BaseModel):
    job_id: str
    session_id: str
    status: str
    idempotency_key: str
    summary_version: int
    retry_count: int
    max_retry_count: int
    abdm_transaction_id: str | None = None
    delivered_at: str | None = None
    last_error: str | None = None
    created_at: str
    updated_at: str


class RetryQueueResult(BaseModel):
    processed: int
    results: list[dict[str, Any]]


# ==============================================================================
# Internal Helpers
# ==============================================================================

async def _resolve_session_patient(
    session_id: str, db: AsyncSession
) -> tuple[Session, Patient]:
    """
    Resolve session → patient from database.
    Raises HTTPException if session not found, patient not linked, or ABHA not available.
    """
    stmt = select(Session).where(Session.id == session_id)
    res = await db.execute(stmt)
    session_record = res.scalar_one_or_none()

    if not session_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found.",
        )

    if not session_record.patient_id:
        raise HTTPException(
            status_code=HTTP_422,
            detail=(
                f"Session {session_id} has no linked patient. "
                "ABDM export requires a verified patient identity with ABHA."
            ),
        )

    patient_stmt = select(Patient).where(Patient.id == session_record.patient_id)
    patient_res = await db.execute(patient_stmt)
    patient_record = patient_res.scalar_one_or_none()

    if not patient_record:
        raise HTTPException(
            status_code=HTTP_422,
            detail=f"Patient record for session {session_id} not found in database.",
        )

    if not patient_record.abha_id or not str(patient_record.abha_id).strip():
        raise HTTPException(
            status_code=HTTP_422,
            detail="Patient has no ABHA identifier. ABDM export requires a verified ABHA.",
        )

    return session_record, patient_record


async def _get_verified_summary(
    session_id: str, db: AsyncSession, require_verified: bool = True
) -> ClinicalSummary:
    """
    Get the latest clinical summary for the session.
    Optionally requires doctor_verified status.
    """
    stmt = (
        select(ClinicalSummary)
        .where(ClinicalSummary.session_id == session_id)
        .order_by(ClinicalSummary.version.desc())
    )
    res = await db.execute(stmt)
    summary = res.scalar_one_or_none()

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No clinical summary found for session {session_id}. Generate and verify a summary first.",
        )

    if not summary.fields_json:
        raise HTTPException(
            status_code=HTTP_422,
            detail=f"Clinical summary for session {session_id} has no content.",
        )

    if require_verified and summary.status != "doctor_verified":
        raise HTTPException(
            status_code=HTTP_422,
            detail=(
                f"Summary for session {session_id} has not been verified by a clinician "
                f"(current status: '{summary.status}'). "
                f"Use POST /api/summary/{session_id}/verify to sign off before exporting."
            ),
        )

    return summary


# ==============================================================================
# Endpoints
# ==============================================================================

@router.get("/preview/{session_id}", response_model=FHIRPreviewResponse)
async def get_fhir_preview_endpoint(
    session_id: str,
    current_user: AuthenticatedUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    GET /api/fhir/preview/{session_id}
    Clinician preview of the FHIR R4 Bundle. Does NOT imply consent, sign-off, or delivery.
    Requires staff authentication and session/patient identity resolution.
    """
    session_record, patient_record = await _resolve_session_patient(session_id, db)
    summary = await _get_verified_summary(session_id, db, require_verified=False)

    fields = [SummaryField.model_validate(f) for f in summary.fields_json]
    is_verified = summary.status == "doctor_verified"

    bundle = fhir_builder.build_bundle(
        session_id=session_id,
        summary_fields=fields,
        patient_id=patient_record.id,
        patient_abha_id=patient_record.abha_id,
        summary_verified=is_verified,
        verified_by=current_user.user_id if is_verified else None,
    )

    return FHIRPreviewResponse(
        session_id=session_id,
        patient_abha_id=patient_record.abha_id,
        summary_version=summary.version,
        summary_status=summary.status,
        bundle_type="document",
        resource_count=len(bundle.get("entry", [])),
        preview_json=bundle,
        is_signed_off=is_verified,
    )


@router.post("/export", response_model=FHIRExportResponse)
async def export_fhir_bundle_endpoint(
    req: FHIRExportRequest,
    current_user: AuthenticatedUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    POST /api/fhir/export
    Affirm and enqueue a consent-bound FHIR export to ABDM gateway.

    Preconditions enforced:
    1. Session → Patient → ABHA identity resolved from database.
    2. Effective store_abdm consent granted.
    3. Summary has been doctor_verified.
    4. Server builds bundle from reviewed snapshot (no client bundles).
    5. Idempotent: returns existing job if already queued/delivered for same version.
    """
    session_record, patient_record = await _resolve_session_patient(req.session_id, db)

    # 1. Enforce store_abdm consent
    await check_effective_consent(req.session_id, "store_abdm", db)

    # 2. Require doctor-verified summary
    summary = await _get_verified_summary(req.session_id, db, require_verified=True)

    # 3. Check transport availability
    if not export_queue.transport.is_available:
        return FHIRExportResponse(
            session_id=req.session_id,
            status="provider_not_configured",
            summary_version=summary.version,
            error_message=(
                f"ABDM push provider not configured (current: {export_queue.transport.provider_name}). "
                "Set ABDM_PUSH_PROVIDER environment variable to enable export delivery."
            ),
        )

    # 4. Build FHIR bundle from server-side reviewed data
    fields = [SummaryField.model_validate(f) for f in summary.fields_json]
    bundle = fhir_builder.build_bundle(
        session_id=req.session_id,
        summary_fields=fields,
        patient_id=patient_record.id,
        patient_abha_id=patient_record.abha_id,
        summary_verified=True,
        verified_by=current_user.user_id,
    )

    # 5. Enqueue (idempotent)
    enqueue_result = await export_queue.enqueue_export(
        session_id=req.session_id,
        patient_abha_id=patient_record.abha_id,
        summary_version=summary.version,
        affirmed_by_doctor_id=current_user.user_id,
        bundle_json=bundle,
        db=db,
    )

    final_status = enqueue_result["status"]
    abdm_txn_id = enqueue_result.get("abdm_transaction_id")
    error_msg = None

    if enqueue_result["is_new"]:
        job_stmt = select(FHIRPushQueue).where(FHIRPushQueue.id == enqueue_result["job_id"])
        job_res = await db.execute(job_stmt)
        job = job_res.scalar_one_or_none()
        if job:
            delivery_result = await export_queue.attempt_delivery(
                job, db, worker_id=current_user.user_id
            )
            final_status = delivery_result["status"]
            abdm_txn_id = delivery_result.get("transaction_id")
            error_msg = delivery_result.get("error")

    await db.commit()

    logger.info(
        f"FHIR export {'enqueued and dispatched' if enqueue_result['is_new'] else 'already exists'} "
        f"for session {req.session_id} v{summary.version} "
        f"by {current_user.user_id} (job: {enqueue_result['job_id']}, status: {final_status})"
    )

    return FHIRExportResponse(
        export_id=enqueue_result["job_id"],
        session_id=req.session_id,
        status=final_status,
        idempotency_key=enqueue_result["idempotency_key"],
        abdm_transaction_id=abdm_txn_id,
        summary_version=summary.version,
        is_new=enqueue_result["is_new"],
        error_message=error_msg,
    )


@router.post("/retry-queue", response_model=RetryQueueResult)
async def process_retry_queue(
    current_user: AuthenticatedUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    POST /api/fhir/retry-queue
    Process all retryable export jobs. Re-validates consent before each attempt.
    Updates the same job row (never creates duplicates).
    """
    if not export_queue.transport.is_available:
        return RetryQueueResult(
            processed=0,
            results=[{
                "status": "provider_not_configured",
                "message": f"Transport '{export_queue.transport.provider_name}' is not available.",
            }],
        )

    jobs = await export_queue.get_retryable_jobs(db)

    if not jobs:
        return RetryQueueResult(processed=0, results=[])

    results = []
    for job in jobs:
        # 1. Revalidate store_abdm consent
        try:
            await check_effective_consent(job.session_id, "store_abdm", db)
        except HTTPException:
            await export_queue.block_job(
                job,
                reason="Consent for store_abdm revoked or missing at dispatch time.",
                status="blocked_consent_revoked",
                db=db,
            )
            results.append({
                "job_id": job.id,
                "status": "blocked_consent_revoked",
                "reason": "Consent revoked",
            })
            continue

        # 2. Revalidate summary version still matches
        summary_stmt = (
            select(ClinicalSummary)
            .where(ClinicalSummary.session_id == job.session_id)
            .order_by(ClinicalSummary.version.desc())
        )
        summary_res = await db.execute(summary_stmt)
        current_summary = summary_res.scalar_one_or_none()

        if not current_summary or current_summary.version != job.summary_version:
            await export_queue.block_job(
                job,
                reason=(
                    f"Summary version changed since export was queued "
                    f"(queued: v{job.summary_version}, current: v{current_summary.version if current_summary else 'none'})."
                ),
                status="blocked_stale_version",
                db=db,
            )
            results.append({
                "job_id": job.id,
                "status": "blocked_stale_version",
                "reason": "Summary version mismatch",
            })
            continue

        if current_summary.status != "doctor_verified":
            await export_queue.block_job(
                job,
                reason=f"Summary no longer doctor_verified (current: {current_summary.status}).",
                status="blocked_stale_version",
                db=db,
            )
            results.append({
                "job_id": job.id,
                "status": "blocked_stale_version",
                "reason": "Summary no longer verified",
            })
            continue

        # 3. Update consent verification timestamp
        job.consent_verified_at = datetime.now(UTC)

        # 4. Attempt delivery
        delivery_result = await export_queue.attempt_delivery(
            job=job,
            db=db,
            worker_id=f"retry_by_{current_user.user_id}",
        )
        results.append(delivery_result)

    await db.commit()

    return RetryQueueResult(
        processed=len(results),
        results=results,
    )


@router.get("/jobs/{session_id}", response_model=list[ExportJobStatus])
async def get_export_jobs_endpoint(
    session_id: str,
    current_user: AuthenticatedUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    GET /api/fhir/jobs/{session_id}
    Retrieve all export jobs for a session with status, attempts, and delivery info.
    """
    jobs = await export_queue.get_jobs_for_session(session_id, db)

    return [
        ExportJobStatus(
            job_id=j.id,
            session_id=j.session_id,
            status=j.status,
            idempotency_key=j.idempotency_key,
            summary_version=j.summary_version,
            retry_count=j.retry_count,
            max_retry_count=j.max_retry_count,
            abdm_transaction_id=j.abdm_transaction_id,
            delivered_at=j.delivered_at.isoformat() if j.delivered_at else None,
            last_error=j.last_error,
            created_at=j.created_at.isoformat(),
            updated_at=j.updated_at.isoformat(),
        )
        for j in jobs
    ]
