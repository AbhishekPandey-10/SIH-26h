"""
Consent Lifecycle and Audit Route Handlers
PS ID26047 — Assignment 2

Manages granular, append-only consent decisions and derivations.
Enforces DPDP Act immutability and deterministic latest-decision semantics.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import ConsentAudit, Session
from app.dependencies import (
    AuthenticatedUser,
    UserRole,
    require_authenticated_user,
    require_session_access,
)
from app.services.session_manager import session_manager

logger = logging.getLogger("medikiosk.routes.consent")
router = APIRouter(prefix="/api/consent", tags=["Consent & Privacy"])


# ==============================================================================
# DTOs
# ==============================================================================

class ConsentItem(BaseModel):
    action: str = Field(
        ...,
        description="Consent action purpose, e.g. share_doctor, store_abdm, anonymized_research"
    )
    granted: bool = Field(..., description="Whether patient granted (True) or refused/revoked (False)")


class RecordConsentRequest(BaseModel):
    session_id: str = Field(..., description="Target encounter session ID")
    consents: List[ConsentItem] = Field(..., min_length=1, description="List of granular consent choices")
    voice_confirmation_ref: Optional[str] = Field(None, description="Optional audio recording reference or digest")


class RevokeConsentRequest(BaseModel):
    session_id: str = Field(..., description="Target encounter session ID")
    action: str = Field(..., description="Action purpose to revoke (e.g. share_doctor)")
    reason: Optional[str] = Field(None, description="Clinical or patient justification for revocation")


class EffectiveConsentResponse(BaseModel):
    session_id: str
    effective_consents: Dict[str, bool]
    audit_history_count: int


# ==============================================================================
# Business Logic Utilities
# ==============================================================================

async def get_effective_consent(db: AsyncSession, session_id: str, action: str) -> bool:
    """
    Derives whether consent is currently granted for a specific action.
    Inspects the latest append-only ConsentAudit record for (session_id, action).
    Returns False if no consent was ever granted or if the latest decision is False.
    """
    stmt = (
        select(ConsentAudit)
        .where(ConsentAudit.session_id == session_id, ConsentAudit.action == action)
        .order_by(ConsentAudit.timestamp.desc())
        .limit(1)
    )
    res = await db.execute(stmt)
    latest_record = res.scalar_one_or_none()
    return bool(latest_record and latest_record.granted)


async def get_all_effective_consents(db: AsyncSession, session_id: str) -> Dict[str, bool]:
    """
    Computes effective consent across all recorded actions for an encounter session.
    Chronological ordering guarantees the latest append-only decision determines the state.
    """
    stmt = (
        select(ConsentAudit)
        .where(ConsentAudit.session_id == session_id)
        .order_by(ConsentAudit.timestamp.asc())
    )
    res = await db.execute(stmt)
    records = res.scalars().all()

    effective_map: Dict[str, bool] = {}
    for rec in records:
        effective_map[rec.action] = rec.granted

    return effective_map


# ==============================================================================
# Endpoints
# ==============================================================================

@router.post("", status_code=status.HTTP_201_CREATED)
async def record_consent_endpoint(
    req: RecordConsentRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Record granular consent agreements in append-only consent_audit log.
    Rejects mutations if session is ended (HTTP 409) or unauthorized (HTTP 403).
    """
    # Authorization: Bound session check
    if current_user.role != UserRole.STAFF and current_user.session_id and current_user.session_id != req.session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot record consent for another encounter session.",
        )

    # Lifecycle check: Session must be active
    await session_manager.assert_session_active(req.session_id, db)

    client_ip = request.client.host if request.client else "127.0.0.1"

    created_records = []
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
        created_records.append(audit_entry)

    await db.commit()
    logger.info(f"Recorded {len(created_records)} consent entries for session {req.session_id} by {current_user.user_id}")

    return {
        "status": "recorded",
        "session_id": req.session_id,
        "count": len(created_records),
        "has_voice_evidence": bool(req.voice_confirmation_ref),
    }


@router.get("/{session_id}", response_model=EffectiveConsentResponse)
async def get_session_consent_endpoint(
    session_id: str,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve current effective consent states across all actions for a session,
    along with total audit trail length.
    """
    # Enforce encounter scoping
    if current_user.role != UserRole.STAFF and current_user.session_id and current_user.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Access denied to encounter session {session_id}.",
        )

    # Check session existence
    sess_stmt = select(Session).where(Session.id == session_id)
    sess_res = await db.execute(sess_stmt)
    if not sess_res.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    effective_map = await get_all_effective_consents(db, session_id)

    # Total audit count
    count_stmt = select(ConsentAudit).where(ConsentAudit.session_id == session_id)
    count_res = await db.execute(count_stmt)
    total_count = len(count_res.scalars().all())

    return EffectiveConsentResponse(
        session_id=session_id,
        effective_consents=effective_map,
        audit_history_count=total_count,
    )


@router.post("/revoke", status_code=status.HTTP_200_OK)
async def revoke_consent_endpoint(
    req: RevokeConsentRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Explicitly revoke a previously granted consent purpose.
    Appends a new ConsentAudit entry with granted=False to maintain immutable audit trail.
    """
    if current_user.role != UserRole.STAFF and current_user.session_id and current_user.session_id != req.session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot revoke consent for another encounter session.",
        )

    # Session must be active to accept online consent modifications
    await session_manager.assert_session_active(req.session_id, db)

    client_ip = request.client.host if request.client else "127.0.0.1"

    revoke_entry = ConsentAudit(
        id=str(uuid.uuid4()),
        session_id=req.session_id,
        action=req.action,
        granted=False,
        voice_confirmation_ref=f"REVOKED: {req.reason}" if req.reason else "REVOKED",
        timestamp=datetime.now(UTC),
        ip_address=client_ip,
    )
    db.add(revoke_entry)
    await db.commit()

    logger.info(f"Revoked consent '{req.action}' for session {req.session_id} by {current_user.user_id}")

    return {
        "status": "revoked",
        "session_id": req.session_id,
        "action": req.action,
        "effective_granted": False,
    }
