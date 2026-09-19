"""
Encounter-End Lifecycle and Privacy Wipe Manager
PS ID26047 — Assignment 2

Orchestrates idempotent session termination, unconsented record destruction,
active transport disconnection, and lifecycle cleanup hooks.
"""

import logging
import os
from datetime import UTC, datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional

from fastapi import HTTPException, WebSocket, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ClinicalSummary,
    ConsentAudit,
    Document,
    ExtractedEntityModel,
    FHIRPushQueue,
    InterviewTranscript,
    Session,
)

logger = logging.getLogger("medikiosk.session_manager")


class SessionEndedError(HTTPException):
    """Raised when a mutation is attempted on a terminated encounter."""

    def __init__(self, session_id: str, detail: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail or f"Session {session_id} has already ended and cannot be modified.",
        )


class SessionManager:
    """Central lifecycle coordinator for kiosk encounters."""

    def __init__(self):
        self._active_websockets: Dict[str, List[WebSocket]] = {}
        self._cleanup_hooks: List[Callable[[str], Awaitable[None]]] = []

    def register_websocket(self, session_id: str, ws: WebSocket) -> None:
        """Register an active WebSocket connection for a session."""
        if session_id not in self._active_websockets:
            self._active_websockets[session_id] = []
        if ws not in self._active_websockets[session_id]:
            self._active_websockets[session_id].append(ws)

    def unregister_websocket(self, session_id: str, ws: WebSocket) -> None:
        """Unregister a WebSocket connection when closed or disconnected."""
        if session_id in self._active_websockets:
            if ws in self._active_websockets[session_id]:
                self._active_websockets[session_id].remove(ws)
            if not self._active_websockets[session_id]:
                del self._active_websockets[session_id]

    def register_cleanup_hook(self, hook: Callable[[str], Awaitable[None]]) -> None:
        """
        Register an async cleanup callback to be invoked when any session ends.
        Services (OCR, Crop, Interview, Export) register their memory/task purges here.
        """
        if hook not in self._cleanup_hooks:
            self._cleanup_hooks.append(hook)

    async def is_session_active(self, session_id: str, db: AsyncSession) -> bool:
        """Check if session exists and is currently in an active, mutable state."""
        stmt = select(Session.status).where(Session.id == session_id)
        res = await db.execute(stmt)
        sess_status = res.scalar_one_or_none()
        if sess_status is None:
            return False
        return sess_status not in ("completed", "ended", "wiped", "cancelled")

    async def assert_session_active(self, session_id: str, db: AsyncSession) -> Session:
        """
        Assert that session is active.
        Raises HTTP 404 if not found, or HTTP 409 Conflict if ended.
        """
        stmt = select(Session).where(Session.id == session_id)
        res = await db.execute(stmt)
        sess = res.scalar_one_or_none()
        if not sess:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
        if sess.status in ("completed", "ended", "wiped", "cancelled"):
            raise SessionEndedError(session_id)
        return sess

    async def end_session(
        self,
        session_id: str,
        db: AsyncSession,
        reason: str = "completed",
    ) -> Dict[str, Any]:
        """
        Idempotent encounter-end workflow:
        1. Atomically verify state; if already terminal, return idempotent success.
        2. Evaluate latest effective consent for 'share_doctor'.
        3. If unconsented/revoked: purge transcripts, entities, summaries, documents,
           and queued exports from DB and storage.
        4. Close all active WebSockets for this session.
        5. Invoke all registered service cleanup hooks.
        6. Wipe in-memory caches.
        7. Set session status ('completed' if consented, 'wiped' if unconsented) and ended_at.
        8. Commit changes.
        """
        stmt = select(Session).where(Session.id == session_id)
        res = await db.execute(stmt)
        session_record = res.scalar_one_or_none()

        if not session_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found.",
            )

        # 1. Idempotency guard: If already ended, do not re-run purge or fail
        if session_record.status in ("completed", "ended", "wiped", "cancelled"):
            logger.info(f"Session {session_id} is already in terminal state '{session_record.status}'. Returning idempotent response.")
            return {
                "status": session_record.status,
                "session_id": session_id,
                "message": "Session was already ended.",
                "idempotent": True,
                "ended_at": session_record.ended_at.isoformat() if session_record.ended_at else None,
            }

        # 2. Check effective consent for 'share_doctor'
        consent_stmt = (
            select(ConsentAudit)
            .where(ConsentAudit.session_id == session_id, ConsentAudit.action == "share_doctor")
            .order_by(ConsentAudit.timestamp.desc())
            .limit(1)
        )
        consent_res = await db.execute(consent_stmt)
        latest_consent = consent_res.scalar_one_or_none()
        share_doctor_granted = bool(latest_consent and latest_consent.granted)

        purged_records = False
        target_status = "completed"

        # 3. Purge unconsented clinical data if share_doctor not granted
        if not share_doctor_granted:
            purged_records = True
            target_status = "wiped"
            logger.warning(
                f"Session {session_id} ended without effective 'share_doctor' consent. "
                "Executing privacy wipe: purging transcripts, entities, summaries, documents, and queued exports."
            )

            # Delete unconsented Extracted Entities
            await db.execute(
                delete(ExtractedEntityModel).where(ExtractedEntityModel.session_id == session_id)
            )

            # Delete unconsented Transcripts
            await db.execute(
                delete(InterviewTranscript).where(InterviewTranscript.session_id == session_id)
            )

            # Delete unconsented Clinical Summaries
            await db.execute(
                delete(ClinicalSummary).where(ClinicalSummary.session_id == session_id)
            )

            # Delete unconsented Queued FHIR Bundles
            await db.execute(
                delete(FHIRPushQueue).where(FHIRPushQueue.session_id == session_id)
            )

            # Delete unconsented Documents and unlink files from storage
            doc_stmt = select(Document).where(Document.session_id == session_id)
            doc_res = await db.execute(doc_stmt)
            docs = doc_res.scalars().all()
            for doc in docs:
                if doc.file_path and os.path.exists(doc.file_path):
                    try:
                        os.remove(doc.file_path)
                    except OSError as e:
                        logger.warning(f"Failed to delete disk document {doc.file_path}: {e}")
            await db.execute(
                delete(Document).where(Document.session_id == session_id)
            )

        # 4. Terminate active WebSockets for this encounter
        if session_id in self._active_websockets:
            sockets_to_close = list(self._active_websockets[session_id])
            for ws in sockets_to_close:
                try:
                    await ws.close(code=status.WS_1000_NORMAL_CLOSURE, reason="Encounter ended")
                except Exception as e:
                    logger.debug(f"Error closing WebSocket for session {session_id}: {e}")
            self._active_websockets.pop(session_id, None)

        # 5. Invoke registered service cleanup hooks
        for hook in self._cleanup_hooks:
            try:
                await hook(session_id)
            except Exception as e:
                logger.error(f"Error executing cleanup hook {hook.__name__} for session {session_id}: {e}", exc_info=True)

        # 6. Wipe process-level in-memory caches
        try:
            from app.routes.session import _IN_MEMORY_SESSION_CACHE
            _IN_MEMORY_SESSION_CACHE.pop(session_id, None)
        except Exception:
            pass

        try:
            from app.services.interview_engine import interview_engine
            interview_engine.cleanup_session(session_id)
        except Exception:
            pass

        # 7. Update session status and timestamp
        now_utc = datetime.now(UTC)
        session_record.status = target_status
        session_record.ended_at = now_utc

        await db.commit()
        await db.refresh(session_record)

        logger.info(f"Session {session_id} ended successfully. Final status: '{target_status}', unconsented purged: {purged_records}")

        return {
            "status": target_status,
            "session_id": session_id,
            "message": f"Session completed and finalized as '{target_status}'.",
            "purged_unconsented": purged_records,
            "idempotent": False,
            "ended_at": now_utc.isoformat(),
        }


session_manager = SessionManager()
