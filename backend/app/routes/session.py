"""
ABDM Identity, Consent & Session Lifecycle Endpoints
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""

import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import ConsentAudit, Patient, Session
from app.services.abdm import (
    get_mock_fhir_bundles,
    request_otp,
    verify_abha,
    verify_otp,
)
from app.shared.schemas import ABHASession, OTPRequest, OTPVerify, PatientDemographics

logger = logging.getLogger("medikiosk.routes.session")
router = APIRouter(prefix="/api/session", tags=["Identity & Session"])


# In-memory transient cache for active kiosk sessions (purged on session end)
_IN_MEMORY_SESSION_CACHE: Dict[str, Dict[str, Any]] = {}


# ==============================================================================
# Request & Response Schemas
# ==============================================================================

class SessionStartRequest(BaseModel):
    abha_id: str | None = None
    patient_name: str | None = None
    language: str = "hi"
    is_caregiver: bool = False
    caregiver_name: str | None = None
    caregiver_relationship: str | None = None
    caregiver_phone: str | None = None
    voice_only_mode: bool = False
    body_map_selections: List[str] | None = None
    interview_mode: str = "allopathic"


class SessionStartResponse(BaseModel):
    session_id: str
    patient_name: str
    language: str
    abha_id: str | None = None
    status: str = "active"
    is_caregiver: bool = False
    caregiver_name: str | None = None
    voice_only_mode: bool = False
    interview_mode: str = "allopathic"


class SessionConfigureRequest(BaseModel):
    body_map_selections: List[str] | None = None
    interview_mode: str | None = None
    voice_only_mode: bool | None = None
    is_caregiver: bool | None = None
    caregiver_name: str | None = None
    caregiver_relationship: str | None = None
    caregiver_phone: str | None = None


class VerifyAbhaRequest(BaseModel):
    abha_id: str = Field(..., description="14-digit ABHA (XX-XXXX-XXXX-XXXX) or ABHA address (name@abdm)")


class AadhaarOTPRequest(BaseModel):
    aadhaar_number: str = Field(..., description="12-digit Aadhaar number")


class AadhaarOTPVerifyRequest(BaseModel):
    txn_id: str
    otp: str
    aadhaar_number: str


class ConsentItem(BaseModel):
    action: str = Field(..., description="e.g. share_doctor, store_abdm, anonymized_research")
    granted: bool


class RecordConsentRequest(BaseModel):
    session_id: str
    consents: List[ConsentItem]
    voice_confirmation_ref: str | None = None


class SessionEndRequest(BaseModel):
    session_id: str


# ==============================================================================
# Endpoints
# ==============================================================================

@router.post("/start", response_model=SessionStartResponse)
async def start_session(req: SessionStartRequest, db: AsyncSession = Depends(get_db)):
    """
    Initialize a new clinical intake session on the Kiosk.
    Handed to Dev 1 LangGraph interview engine at the integration checkpoint.
    Response shape matches Dev 1 exact contract:
      { "session_id": "uuid", "patient_name": "...", "language": "hi", "abha_id": "..." }
    """
    session_uuid = str(uuid.uuid4())
    patient_name = req.patient_name or "मरीज (Patient)"
    patient_id = None

    # If ABHA ID is provided, verify or register patient in database
    if req.abha_id:
        try:
            demo = await verify_abha(req.abha_id)
            patient_name = demo.name
            
            # Check if patient exists
            stmt = select(Patient).where(Patient.abha_id == req.abha_id)
            res = await db.execute(stmt)
            existing_patient = res.scalar_one_or_none()
            
            if not existing_patient:
                new_patient = Patient(
                    id=str(uuid.uuid4()),
                    abha_id=demo.abha_id,
                    abha_number=demo.abha_number,
                    name=demo.name,
                    gender=demo.gender,
                    dob=demo.dob,
                    mobile=demo.mobile,
                    address=demo.address,
                    district=demo.district,
                    state=demo.state,
                )
                db.add(new_patient)
                await db.flush()
                patient_id = new_patient.id
            else:
                patient_id = existing_patient.id
        except Exception as e:
            logger.warning(f"Failed to resolve patient for session {session_uuid}: {e}")

    # Persist session record
    new_session = Session(
        id=session_uuid,
        patient_id=patient_id,
        language=req.language,
        status="active",
        is_caregiver=req.is_caregiver,
        caregiver_name=req.caregiver_name,
        caregiver_relationship=req.caregiver_relationship,
        caregiver_phone=req.caregiver_phone,
        voice_only_mode=req.voice_only_mode,
        body_map_selections=req.body_map_selections,
        interview_mode=req.interview_mode,
        started_at=datetime.now(UTC),
    )
    db.add(new_session)
    await db.commit()

    # Pre-configure interview engine if body map or mode provided
    try:
        from app.services.interview_engine import interview_engine
        if req.body_map_selections:
            interview_engine.set_body_map(session_uuid, req.body_map_selections)
        if req.interview_mode:
            interview_engine.set_interview_mode(session_uuid, req.interview_mode)
    except Exception as e:
        logger.debug(f"Interview engine preconfig warning: {e}")

    # Store in fast in-memory cache
    _IN_MEMORY_SESSION_CACHE[session_uuid] = {
        "session_id": session_uuid,
        "patient_name": patient_name,
        "language": req.language,
        "abha_id": req.abha_id,
        "started_at": datetime.now(UTC).isoformat(),
    }

    return SessionStartResponse(
        session_id=session_uuid,
        patient_name=patient_name,
        language=req.language,
        abha_id=req.abha_id,
        status="active",
        is_caregiver=req.is_caregiver,
        caregiver_name=req.caregiver_name,
        voice_only_mode=req.voice_only_mode,
        interview_mode=req.interview_mode,
    )


@router.post("/{session_id}/configure")
async def configure_session(
    session_id: str,
    req: SessionConfigureRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Configure session attributes (body map selections, interview mode, caregiver info, voice-only mode).
    """
    stmt = select(Session).where(Session.id == session_id)
    res = await db.execute(stmt)
    sess_row = res.scalar_one_or_none()
    if not sess_row:
        raise HTTPException(status_code=404, detail="Session not found")

    if req.body_map_selections is not None:
        sess_row.body_map_selections = req.body_map_selections
    if req.interview_mode is not None:
        sess_row.interview_mode = req.interview_mode
    if req.voice_only_mode is not None:
        sess_row.voice_only_mode = req.voice_only_mode
    if req.is_caregiver is not None:
        sess_row.is_caregiver = req.is_caregiver
    if req.caregiver_name is not None:
        sess_row.caregiver_name = req.caregiver_name
    if req.caregiver_relationship is not None:
        sess_row.caregiver_relationship = req.caregiver_relationship
    if req.caregiver_phone is not None:
        sess_row.caregiver_phone = req.caregiver_phone

    await db.commit()

    # Sync with interview engine in memory
    try:
        from app.services.interview_engine import interview_engine
        if req.body_map_selections is not None:
            interview_engine.set_body_map(session_id, req.body_map_selections)
        if req.interview_mode is not None:
            interview_engine.set_interview_mode(session_id, req.interview_mode)
    except Exception as e:
        logger.debug(f"Interview engine configure sync error: {e}")

    return {"status": "configured", "session_id": session_id}


@router.post("/verify-abha", response_model=PatientDemographics)
async def verify_abha_endpoint(
    body: VerifyAbhaRequest | None = None,
    abha_id: str | None = Query(None, description="ABHA address or 14-digit number")
):
    """
    Verify ABHA ID against ABDM Sandbox.
    Supports both JSON body and query parameter for flexibility.
    Validates format: XX-XXXX-XXXX-XXXX or name@abdm.
    """
    target_id = body.abha_id if body else abha_id
    if not target_id or not target_id.strip():
        raise HTTPException(status_code=400, detail="ABHA ID is required.")

    clean_id = target_id.strip()

    # Format check: must be either email-like (@abdm) or digits with optional dashes
    is_address = "@" in clean_id
    digits_only = re.sub(r"\D", "", clean_id)
    if not is_address and len(digits_only) not in (10, 12, 14):
        raise HTTPException(
            status_code=400,
            detail="Invalid ABHA format. Please enter a 14-digit ABHA number (XX-XXXX-XXXX-XXXX) or ABHA address (name@abdm)."
        )

    try:
        demo = await verify_abha(clean_id)
        return demo
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"ABDM Sandbox communication error: {e}")
        raise HTTPException(status_code=503, detail="ABDM Sandbox is currently unreachable. Please try again.")


@router.post("/aadhaar-otp")
async def aadhaar_otp_endpoint(req: AadhaarOTPRequest) -> Dict[str, str]:
    """
    Aadhaar OTP fallback endpoint when patient has no ABHA ID.
    Validates 12-digit Aadhaar number and sends mock OTP in sandbox.
    """
    digits = re.sub(r"\D", "", req.aadhaar_number)
    if len(digits) != 12:
        raise HTTPException(status_code=400, detail="Aadhaar number must be exactly 12 digits.")

    try:
        txn_id = await request_otp(digits)
        return {
            "txn_id": txn_id,
            "message": "OTP sent to registered mobile linked with Aadhaar. (Sandbox code: 123456)"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/verify-aadhaar-otp")
async def verify_aadhaar_otp_endpoint(req: AadhaarOTPVerifyRequest) -> Dict[str, Any]:
    """
    Verify Aadhaar OTP and create a temporary unlinked patient identity.
    UI clearly labels this: 'Session created without ABHA linkage'.
    """
    digits = re.sub(r"\D", "", req.aadhaar_number)
    if len(digits) != 12:
        raise HTTPException(status_code=400, detail="Aadhaar number must be exactly 12 digits.")

    try:
        # In sandbox, 123456 is the fixed OTP
        await verify_otp(req.txn_id, req.otp.strip())
        masked_aadhaar = f"XXXX-XXXX-{digits[-4:]}"
        return {
            "name": "आधार सत्यापित नागरिक (Aadhaar Citizen)",
            "gender": "O",
            "dob": "1990-01-01",
            "mobile": "9876543210",
            "aadhaar_masked": masked_aadhaar,
            "is_temporary": True,
            "label": "Session created without ABHA linkage",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/consent")
async def record_consent(req: RecordConsentRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Record granular 3-step digital consent to the append-only consent_audit table.
    Enforces immutability: no UPDATE or DELETE operations permitted.
    """
    # Verify session exists
    stmt = select(Session).where(Session.id == req.session_id)
    res = await db.execute(stmt)
    session_record = res.scalar_one_or_none()
    if not session_record:
        raise HTTPException(status_code=404, detail="Session not found.")

    client_ip = request.client.host if request.client else "127.0.0.1"

    for c in req.consents:
        audit_entry = ConsentAudit(
            id=str(uuid.uuid4()),
            session_id=req.session_id,
            action=c.action,
            granted=c.granted,
            voice_confirmation_ref=req.voice_confirmation_ref,
            timestamp=datetime.now(UTC),
            ip_address=client_ip,
        )
        db.add(audit_entry)

    await db.commit()
    logger.info(f"Recorded {len(req.consents)} consent decisions for session {req.session_id}")

    return {
        "status": "recorded",
        "count": len(req.consents),
        "session_id": req.session_id,
        "has_voice_evidence": bool(req.voice_confirmation_ref),
    }


@router.post("/end")
async def end_session(req: SessionEndRequest, db: AsyncSession = Depends(get_db)):
    """
    Marks session complete and triggers privacy wipe on backend.
    Purges transient in-memory caches, keeping only consented DB records.
    """
    # 1. Update session status in DB
    stmt = select(Session).where(Session.id == req.session_id)
    res = await db.execute(stmt)
    session_record = res.scalar_one_or_none()
    if session_record:
        session_record.status = "completed"
        session_record.ended_at = datetime.now(UTC)
        await db.commit()

    # 2. Server-side purge of in-memory cache
    if req.session_id in _IN_MEMORY_SESSION_CACHE:
        del _IN_MEMORY_SESSION_CACHE[req.session_id]

    # 3. Purge interview engine in-memory session state (prevents memory leaks)
    from app.services.interview_engine import interview_engine
    interview_engine.cleanup_session(req.session_id)

    logger.info(f"Session {req.session_id} ended. Transient memory wiped.")

    return {
        "status": "wiped",
        "session_id": req.session_id,
        "message": "Session completed and transient data wiped."
    }



@router.get("/{session_id}/status")
async def get_session_status(session_id: str, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Retrieve the current state of a kiosk encounter session."""
    stmt = select(Session).where(Session.id == session_id)
    res = await db.execute(stmt)
    s = res.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found.")

    return {
        "session_id": s.id,
        "status": s.status,
        "language": s.language,
        "patient_id": s.patient_id,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "ended_at": s.ended_at.isoformat() if s.ended_at else None,
    }


@router.post("/request-otp")
async def legacy_request_otp(req: OTPRequest) -> Dict[str, str]:
    """Legacy OTP endpoint for backward compatibility with Phase 0 tests."""
    txn_id = await request_otp(req.identifier)
    return {"txn_id": txn_id, "message": "OTP sent successfully. (Sandbox default is 123456)"}


@router.post("/verify-otp", response_model=ABHASession)
async def legacy_verify_otp(req: OTPVerify):
    """Legacy OTP verify endpoint for backward compatibility with Phase 0 tests."""
    return await verify_otp(req.txn_id, req.otp, req.abha_id)


@router.get("/{session_id}/fhir")
async def get_patient_fhir_records(session_id: str, abha_id: str = Query("rajesh.kumar@abdm")) -> List[Dict[str, Any]]:
    """Retrieve pre-seeded FHIR R4 medical records from sandbox."""
    return get_mock_fhir_bundles(abha_id)
