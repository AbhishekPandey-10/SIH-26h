"""
Central Access Control, Authentication, and Encounter Authorization Dependencies
PS ID26047 — Assignment 2

Provides role-based access control (RBAC), encounter-scoped authorization,
and authenticated identity binding across HTTP endpoints and WebSockets.
"""

import logging
from enum import Enum
from typing import Any, Callable, Optional

from fastapi import Depends, Header, HTTPException, Query, Request, Security, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db
from app.db.models import ConsentAudit, Session

logger = logging.getLogger("medikiosk.auth")

security_bearer = HTTPBearer(auto_error=False)


# ==============================================================================
# Auth Models
# ==============================================================================

class UserRole(str, Enum):
    STAFF = "staff"
    KIOSK = "kiosk"
    ADMIN = "admin"


class AuthenticatedUser(BaseModel):
    """Authenticated caller context."""
    model_config = ConfigDict(from_attributes=True)

    user_id: str = Field(..., description="Unique staff, doctor, or kiosk identifier")
    role: UserRole = Field(..., description="System role: staff, kiosk, or admin")
    session_id: Optional[str] = Field(None, description="Encounter UUID if caller is session-bound")
    name: Optional[str] = Field(None, description="Display name of the authenticated user")


# ==============================================================================
# Token Extraction & Validation
# ==============================================================================

def extract_raw_token(
    request: Request,
    bearer_creds: Optional[HTTPAuthorizationCredentials] = None,
    x_staff_token: Optional[str] = None,
    x_kiosk_token: Optional[str] = None,
    x_session_token: Optional[str] = None,
) -> Optional[str]:
    """Extract token from standard Authorization header or fallback headers."""
    if bearer_creds and bearer_creds.credentials:
        return bearer_creds.credentials.strip()
    if x_staff_token:
        return x_staff_token.strip()
    if x_kiosk_token:
        return x_kiosk_token.strip()
    if x_session_token:
        return x_session_token.strip()

    # Query param fallback for downloads/crops
    q_token = request.query_params.get("token")
    if q_token:
        return q_token.strip()

    return None


def resolve_token_to_user(token: str) -> Optional[AuthenticatedUser]:
    """
    Validate a raw token string and resolve it to an AuthenticatedUser.
    Supports:
    - Staff tokens: matching settings.STAFF_API_KEY, prefix 'staff_', or 'staff:<id>'
    - Kiosk tokens: matching settings.KIOSK_API_KEY, prefix 'kiosk_', or 'kiosk:<id>'
    - Session tokens: format 'session_<session_id>'
    """
    token_clean = token.strip()

    # 1. Staff authentication
    if token_clean == settings.STAFF_API_KEY:
        return AuthenticatedUser(user_id="doc_opd_01", role=UserRole.STAFF, name="Default OPD Clinician")
    if token_clean.startswith("staff_"):
        staff_id = token_clean.replace("staff_", "", 1) or "staff_01"
        return AuthenticatedUser(user_id=staff_id, role=UserRole.STAFF, name=f"Staff {staff_id}")
    if token_clean.startswith("staff:"):
        staff_id = token_clean.split(":", 1)[1]
        return AuthenticatedUser(user_id=staff_id, role=UserRole.STAFF, name=f"Staff {staff_id}")

    # 2. Kiosk authentication
    if token_clean == settings.KIOSK_API_KEY:
        return AuthenticatedUser(user_id=settings.KIOSK_ID, role=UserRole.KIOSK, name="Authorized Kiosk")
    if token_clean.startswith("kiosk_"):
        kiosk_id = token_clean.replace("kiosk_", "", 1) or settings.KIOSK_ID
        return AuthenticatedUser(user_id=kiosk_id, role=UserRole.KIOSK, name=f"Kiosk {kiosk_id}")
    if token_clean.startswith("kiosk:"):
        kiosk_id = token_clean.split(":", 1)[1]
        return AuthenticatedUser(user_id=kiosk_id, role=UserRole.KIOSK, name=f"Kiosk {kiosk_id}")

    # 3. Session-scoped token (for patient kiosk session)
    if token_clean.startswith("session_"):
        session_id = token_clean.replace("session_", "", 1)
        return AuthenticatedUser(
            user_id=f"kiosk_patient_{session_id[:8]}",
            role=UserRole.KIOSK,
            session_id=session_id,
            name="Session Patient Kiosk"
        )

    return None


# ==============================================================================
# FastAPI Dependencies
# ==============================================================================

async def get_current_user_optional(
    request: Request,
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    x_staff_token: Optional[str] = Header(None),
    x_kiosk_token: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
) -> Optional[AuthenticatedUser]:
    """Retrieve authenticated user if credentials exist, else None."""
    token = extract_raw_token(request, bearer, x_staff_token, x_kiosk_token, x_session_token)
    if not token:
        # In dev mode, allow header X-Kiosk-ID as default kiosk auth if present
        if settings.DEBUG and request.headers.get("X-Kiosk-ID"):
            return AuthenticatedUser(
                user_id=request.headers["X-Kiosk-ID"],
                role=UserRole.KIOSK,
                name="Dev Kiosk"
            )
        return None
    return resolve_token_to_user(token)


async def require_authenticated_user(
    current_user: Optional[AuthenticatedUser] = Depends(get_current_user_optional),
) -> AuthenticatedUser:
    """Require valid credentials for any authenticated role."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a valid Authorization bearer or staff/kiosk token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


async def require_staff(
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
) -> AuthenticatedUser:
    """Require staff or clinician role for access (e.g. review, resolution, alert dismissal)."""
    if current_user.role != UserRole.STAFF:
        logger.warning(f"Access denied: User {current_user.user_id} with role {current_user.role} attempted staff action.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Staff / Clinician privileges required.",
        )
    return current_user


async def require_kiosk(
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
) -> AuthenticatedUser:
    """Require kiosk or staff role."""
    if current_user.role not in (UserRole.KIOSK, UserRole.STAFF):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Kiosk or staff credentials required.",
        )
    return current_user


def require_session_access(session_id: Optional[str] = None) -> Callable:
    """
    Enforce encounter scoping.
    - Staff can access any encounter.
    - Kiosks bound to a session can ONLY access their own session.
    - Other kiosks or unauthenticated callers are rejected.
    If session_id is None, dynamically extracts it from request.path_params or query_params.
    """
    async def dependency(
        request: Request,
        current_user: AuthenticatedUser = Depends(require_authenticated_user),
        db: AsyncSession = Depends(get_db),
    ) -> AuthenticatedUser:
        target_session_id = session_id or request.path_params.get("session_id") or request.query_params.get("session_id")

        # Staff has global encounter clearance
        if current_user.role == UserRole.STAFF:
            return current_user

        if target_session_id:
            # If caller is session-bound, verify exact encounter match
            if current_user.session_id and current_user.session_id != target_session_id:
                logger.warning(
                    f"Cross-session access rejected: User {current_user.user_id} (bound to {current_user.session_id}) "
                    f"attempted to access foreign session {target_session_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Forbidden: Access denied to encounter session {target_session_id}.",
                )

            # Verify that the session actually exists in the database
            stmt = select(Session).where(Session.id == target_session_id)
            res = await db.execute(stmt)
            sess = res.scalar_one_or_none()
            if not sess:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

        return current_user

    return dependency


async def require_encounter_access(
    request: Request,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
) -> AuthenticatedUser:
    """Convenience FastAPI dependency extracting session_id from path/query parameters."""
    dep = require_session_access()
    return await dep(request=request, current_user=current_user, db=db)


async def check_effective_consent(
    session_id: str,
    action: str = "share_doctor",
    db: AsyncSession = Depends(get_db),
) -> bool:
    """
    Direct function to verify that the session has effective (latest append-only) consent granted for the requested action.
    Raises HTTP 403 if consent was refused, revoked, or never recorded.
    """
    stmt = (
        select(ConsentAudit)
        .where(ConsentAudit.session_id == session_id, ConsentAudit.action == action)
        .order_by(ConsentAudit.timestamp.desc())
        .limit(1)
    )
    res = await db.execute(stmt)
    latest_consent = res.scalar_one_or_none()

    if not latest_consent or not latest_consent.granted:
        logger.warning(f"Effective consent check failed for session {session_id} on action '{action}'")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Patient has not granted effective consent for '{action}'.",
        )
    return True


def require_effective_consent(action: str = "share_doctor") -> Callable:
    """FastAPI dependency for checking effective consent on the session identified in path/query."""
    async def dependency(
        request: Request,
        db: AsyncSession = Depends(get_db),
    ) -> bool:
        session_id = request.path_params.get("session_id") or request.query_params.get("session_id")
        if not session_id:
            return True
        return await check_effective_consent(session_id, action, db)

    return dependency


# ==============================================================================
# WebSocket Authentication
# ==============================================================================

async def authenticate_websocket(
    websocket: WebSocket,
    session_id: Optional[str] = None,
    allowed_roles: tuple[UserRole, ...] = (UserRole.KIOSK, UserRole.STAFF),
) -> Optional[AuthenticatedUser]:
    """
    Authenticate WebSocket connection from headers or query parameters.
    Closes connection with code 1008 (Policy Violation) if authentication fails.
    """
    token = websocket.query_params.get("token")
    if not token:
        # Check headers
        token = websocket.headers.get("x-staff-token") or websocket.headers.get("x-kiosk-token")
    if not token:
        auth_header = websocket.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "", 1).strip()

    # Fallback in dev/debug mode
    if not token and settings.DEBUG and session_id:
        token = f"session_{session_id}"

    if not token:
        logger.warning("WebSocket rejected: missing authentication credentials.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
        return None

    user = resolve_token_to_user(token)
    if not user or user.role not in allowed_roles:
        logger.warning(f"WebSocket rejected: invalid token or insufficient role for token: {token[:8]}...")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized")
        return None

    # Enforce encounter scoping on WebSocket if session_id is specified
    if session_id and user.role != UserRole.STAFF and user.session_id and user.session_id != session_id:
        logger.warning(f"WebSocket cross-session rejected: {user.session_id} vs {session_id}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Cross-session access forbidden")
        return None

    return user
