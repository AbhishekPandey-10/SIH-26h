"""
ABDM Identity & Session Lifecycle Endpoints
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""

import logging
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.abdm import (
    get_mock_fhir_bundles,
    request_otp,
    verify_abha,
    verify_otp,
)
from app.shared.schemas import ABHASession, OTPRequest, OTPVerify, PatientDemographics

logger = logging.getLogger("medikiosk.routes.session")
router = APIRouter(prefix="/api/session", tags=["Identity & Session"])


class SessionStartRequest(BaseModel):
    abha_id: str | None = None
    language: str = "hi"
    is_caregiver: bool = False


class SessionStartResponse(BaseModel):
    session_id: str
    language: str
    status: str
    patient: PatientDemographics | None = None


@router.post("/start", response_model=SessionStartResponse)
async def start_session(req: SessionStartRequest):
    """
    Initialize a new clinical intake session on the Kiosk.
    Used by Dev 1 LangGraph interview engine and kiosk frontend.
    """
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    patient_demo = None

    if req.abha_id:
        try:
            patient_demo = await verify_abha(req.abha_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    return SessionStartResponse(
        session_id=session_id,
        language=req.language,
        status="active",
        patient=patient_demo,
    )


@router.post("/verify-abha", response_model=PatientDemographics)
async def verify_abha_endpoint(abha_id: str = Query(..., description="ABHA address e.g. rajesh.kumar@abdm")):
    """Verify ABHA ID against ABDM Sandbox."""
    try:
        return await verify_abha(abha_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/request-otp")
async def request_otp_endpoint(req: OTPRequest) -> Dict[str, str]:
    """Request OTP for ABHA/Aadhaar authentication."""
    try:
        txn_id = await request_otp(req.identifier)
        return {"txn_id": txn_id, "message": "OTP sent successfully. (Sandbox default is 123456)"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/verify-otp", response_model=ABHASession)
async def verify_otp_endpoint(req: OTPVerify):
    """Verify OTP and return active authenticated session."""
    try:
        return await verify_otp(req.txn_id, req.otp, req.abha_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{session_id}/fhir")
async def get_patient_fhir_records(session_id: str, abha_id: str = Query("rajesh.kumar@abdm")) -> List[Dict[str, Any]]:
    """Retrieve pre-seeded FHIR R4 medical records from sandbox."""
    return get_mock_fhir_bundles(abha_id)
