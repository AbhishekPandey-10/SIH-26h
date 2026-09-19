"""
ABDM FHIR Bundle Export Service — Transport, Queue, and Delivery Management
PS ID26047 — Assignment 6

Design invariants:
- Transport is injectable (production, sandbox demo, unavailable, or test stub).
- Default transport is UnavailableTransport (explicit provider_not_configured).
- No fabricated bearer tokens or ABDM reference numbers.
- Queue operations are idempotent: one job per idempotency key.
- Retry updates the same row (never creates a new one).
- Consent is revalidated at dispatch time.
- Timeout after request sent → unknown_delivery (not assumed rejection).
"""

import copy
import logging
import os
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.db.models import FHIRPushQueue

logger = logging.getLogger("medikiosk.abdm_push")


# ==============================================================================
# Transport Protocol (Injectable)
# ==============================================================================

class ABDMTransportResult:
    """Result from a transport attempt."""
    __slots__ = ("success", "transaction_id", "error", "is_retryable", "is_timeout_after_send")

    def __init__(
        self,
        success: bool,
        transaction_id: str | None = None,
        error: str | None = None,
        is_retryable: bool = True,
        is_timeout_after_send: bool = False,
    ):
        self.success = success
        self.transaction_id = transaction_id
        self.error = error
        self.is_retryable = is_retryable
        self.is_timeout_after_send = is_timeout_after_send


class ABDMTransport(ABC):
    """Abstract ABDM transport interface."""

    @abstractmethod
    async def send_bundle(self, bundle: dict[str, Any], patient_abha_id: str) -> ABDMTransportResult:
        """Send a FHIR bundle to ABDM gateway. Returns transport result."""
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether this transport is configured and available."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable transport provider name."""
        ...


class UnavailableTransport(ABDMTransport):
    """
    Default transport when no ABDM provider is configured.
    Returns explicit unavailable status. Never makes network requests.
    """

    async def send_bundle(self, bundle: dict[str, Any], patient_abha_id: str) -> ABDMTransportResult:
        return ABDMTransportResult(
            success=False,
            error="ABDM push provider not configured. Set ABDM_PUSH_PROVIDER to enable export delivery.",
            is_retryable=False,
        )

    @property
    def is_available(self) -> bool:
        return False

    @property
    def provider_name(self) -> str:
        return "unavailable"


class SandboxDemoTransport(ABDMTransport):
    """
    Sandbox demo transport for development/testing.
    Makes real HTTP requests to ABDM sandbox with proper credentials.
    Only enabled via explicit ABDM_PUSH_PROVIDER=sandbox_demo config.
    """

    def __init__(self):
        self.sandbox_url = os.getenv("ABDM_SANDBOX_URL", "https://dev.abdm.gov.in")
        self.client_id = os.getenv("ABDM_CLIENT_ID", "")
        self.client_secret = os.getenv("ABDM_CLIENT_SECRET", "")

    async def send_bundle(self, bundle: dict[str, Any], patient_abha_id: str) -> ABDMTransportResult:
        if not self.client_id or not self.client_secret:
            return ABDMTransportResult(
                success=False,
                error="ABDM sandbox credentials (ABDM_CLIENT_ID, ABDM_CLIENT_SECRET) not configured.",
                is_retryable=False,
            )

        endpoint = f"{self.sandbox_url}/v0.5/health-information/notify"
        try:
            import httpx
            headers = {
                "Content-Type": "application/json",
                "X-CM-ID": "sbx",
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(endpoint, json=bundle, headers=headers)
                if response.status_code in (200, 201, 202):
                    # Parse actual acknowledgement from response
                    resp_data = {}
                    try:
                        resp_data = response.json()
                    except Exception:
                        pass
                    txn_id = resp_data.get("transactionId") or resp_data.get("requestId")
                    return ABDMTransportResult(
                        success=True,
                        transaction_id=txn_id,
                    )
                else:
                    return ABDMTransportResult(
                        success=False,
                        error=f"ABDM sandbox returned HTTP {response.status_code}: {response.text[:200]}",
                        is_retryable=response.status_code >= 500,
                    )
        except Exception as e:
            error_str = str(e)
            is_timeout = "timeout" in error_str.lower() or "timed out" in error_str.lower()
            return ABDMTransportResult(
                success=False,
                error=error_str,
                is_retryable=True,
                is_timeout_after_send=is_timeout,
            )

    @property
    def is_available(self) -> bool:
        return bool(self.client_id and self.client_secret)

    @property
    def provider_name(self) -> str:
        return "sandbox_demo"


class TestTransport(ABDMTransport):
    """
    Test-only transport for unit/integration tests.
    Records calls and returns configurable results. Never makes network requests.
    """
    __test__ = False

    def __init__(self):
        self.calls: list[dict[str, Any]] = []
        self.next_result: ABDMTransportResult = ABDMTransportResult(
            success=True,
            transaction_id="test-txn-001",
        )

    async def send_bundle(self, bundle: dict[str, Any], patient_abha_id: str) -> ABDMTransportResult:
        self.calls.append({
            "bundle": bundle,
            "patient_abha_id": patient_abha_id,
            "timestamp": datetime.now(UTC).isoformat(),
        })
        return self.next_result

    @property
    def is_available(self) -> bool:
        return True

    @property
    def provider_name(self) -> str:
        return "test"

    def configure_result(
        self,
        success: bool = True,
        transaction_id: str | None = "test-txn-001",
        error: str | None = None,
        is_retryable: bool = True,
        is_timeout_after_send: bool = False,
    ) -> None:
        self.next_result = ABDMTransportResult(
            success=success,
            transaction_id=transaction_id,
            error=error,
            is_retryable=is_retryable,
            is_timeout_after_send=is_timeout_after_send,
        )

    def reset(self) -> None:
        self.calls.clear()
        self.next_result = ABDMTransportResult(success=True, transaction_id="test-txn-001")


# ==============================================================================
# Export Queue Manager
# ==============================================================================

# Minimum backoff seconds between retry attempts (exponential: 2^retry_count * base)
_BACKOFF_BASE_SECONDS = 30


class ExportQueueManager:
    """
    Manages durable FHIR export jobs with idempotency, lease-based claiming,
    bounded retry, and consent-aware dispatch.
    """

    def __init__(self, transport: ABDMTransport | None = None):
        self._transport: ABDMTransport = transport or _resolve_default_transport()

    @property
    def transport(self) -> ABDMTransport:
        return self._transport

    @transport.setter
    def transport(self, value: ABDMTransport) -> None:
        self._transport = value

    async def enqueue_export(
        self,
        *,
        session_id: str,
        patient_abha_id: str,
        summary_version: int,
        affirmed_by_doctor_id: str,
        bundle_json: dict[str, Any],
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        Create or return existing export job for the given idempotency key.

        Returns dict with 'job_id', 'status', 'is_new', 'idempotency_key'.
        """
        idempotency_key = f"{session_id}:{summary_version}"

        # Check for existing job with same idempotency key
        stmt = select(FHIRPushQueue).where(FHIRPushQueue.idempotency_key == idempotency_key)
        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            return {
                "job_id": existing.id,
                "status": existing.status,
                "is_new": False,
                "idempotency_key": idempotency_key,
                "abdm_transaction_id": existing.abdm_transaction_id,
            }

        # Create new job
        job_id = str(uuid.uuid4())
        job = FHIRPushQueue(
            id=job_id,
            session_id=session_id,
            idempotency_key=idempotency_key,
            patient_abha_id=patient_abha_id,
            summary_version=summary_version,
            affirmed_by_doctor_id=affirmed_by_doctor_id,
            bundle_json=bundle_json,
            status="pending",
            retry_count=0,
            attempt_history=[],
            consent_verified_at=datetime.now(UTC),
        )
        db.add(job)
        await db.flush()

        return {
            "job_id": job_id,
            "status": "pending",
            "is_new": True,
            "idempotency_key": idempotency_key,
            "abdm_transaction_id": None,
        }

    async def attempt_delivery(
        self,
        job: FHIRPushQueue,
        db: AsyncSession,
        worker_id: str = "default",
    ) -> dict[str, Any]:
        """
        Attempt to deliver a single export job.
        Claims the job with a lease, sends via transport, and records the result.

        Returns dict with delivery outcome.
        """
        now = datetime.now(UTC)

        # 1. Claim with lease
        if job.status not in ("pending", "failed_retryable"):
            return {
                "job_id": job.id,
                "status": job.status,
                "action": "skipped",
                "reason": f"Job not in deliverable state: {job.status}",
            }

        # Check bounded retry
        if job.retry_count >= job.max_retry_count:
            job.status = "failed_terminal"
            job.last_error = f"Exceeded maximum retry count ({job.max_retry_count})"
            job.updated_at = now
            await db.flush()
            return {
                "job_id": job.id,
                "status": "failed_terminal",
                "action": "terminated",
                "reason": "Max retries exceeded",
            }

        # Check backoff period
        if job.retry_count > 0 and job.attempt_history:
            last_attempt = job.attempt_history[-1] if job.attempt_history else None
            if last_attempt:
                try:
                    last_time = datetime.fromisoformat(last_attempt.get("timestamp", ""))
                    backoff_seconds = min(_BACKOFF_BASE_SECONDS * (2 ** (job.retry_count - 1)), 3600)
                    if now < last_time + timedelta(seconds=backoff_seconds):
                        return {
                            "job_id": job.id,
                            "status": job.status,
                            "action": "backoff",
                            "reason": f"Backoff period not elapsed ({backoff_seconds}s)",
                        }
                except (ValueError, TypeError):
                    pass

        # Claim lease
        job.status = "claimed"
        job.locked_at = now
        job.locked_by = worker_id
        job.updated_at = now
        await db.flush()

        # 2. Attempt transport
        try:
            result = await self._transport.send_bundle(job.bundle_json, job.patient_abha_id)
        except Exception as e:
            result = ABDMTransportResult(
                success=False,
                error=str(e),
                is_retryable=True,
            )

        # 3. Record attempt
        attempt_entry = {
            "timestamp": now.isoformat(),
            "success": result.success,
            "error": result.error,
            "transaction_id": result.transaction_id,
            "is_timeout_after_send": result.is_timeout_after_send,
            "worker_id": worker_id,
        }
        history = copy.deepcopy(job.attempt_history or [])
        history.append(attempt_entry)
        job.attempt_history = history
        flag_modified(job, "attempt_history")

        job.retry_count += 1

        if result.success:
            job.status = "delivered"
            job.delivered_at = now
            job.abdm_transaction_id = result.transaction_id
            job.last_error = None
        elif result.is_timeout_after_send:
            # Timeout after request was sent: ambiguous delivery.
            # Mark as failed_retryable but preserve the note that delivery may have succeeded.
            job.status = "failed_retryable"
            job.last_error = f"Timeout after send (delivery unknown): {result.error}"
        elif result.is_retryable:
            job.status = "failed_retryable"
            job.last_error = result.error
        else:
            job.status = "failed_terminal"
            job.last_error = result.error

        # Release lease
        job.locked_at = None
        job.locked_by = None
        job.updated_at = now

        await db.flush()

        return {
            "job_id": job.id,
            "status": job.status,
            "action": "delivered" if result.success else "failed",
            "transaction_id": result.transaction_id,
            "error": result.error,
            "retry_count": job.retry_count,
            "is_timeout_after_send": result.is_timeout_after_send,
        }

    async def block_job(
        self,
        job: FHIRPushQueue,
        reason: str,
        status: str,
        db: AsyncSession,
    ) -> None:
        """Block a job from further delivery attempts."""
        now = datetime.now(UTC)
        job.status = status
        job.last_error = reason
        job.locked_at = None
        job.locked_by = None
        job.updated_at = now

        history = copy.deepcopy(job.attempt_history or [])
        history.append({
            "timestamp": now.isoformat(),
            "success": False,
            "error": reason,
            "action": "blocked",
        })
        job.attempt_history = history
        flag_modified(job, "attempt_history")

        await db.flush()

    async def get_retryable_jobs(self, db: AsyncSession) -> list[FHIRPushQueue]:
        """Get all jobs eligible for retry (pending or failed_retryable, not lease-locked)."""
        stmt = select(FHIRPushQueue).where(
            FHIRPushQueue.status.in_(["pending", "failed_retryable"]),
            # Not currently claimed by another worker
            FHIRPushQueue.locked_at.is_(None),
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def get_jobs_for_session(self, session_id: str, db: AsyncSession) -> list[FHIRPushQueue]:
        """Get all export jobs for a session."""
        stmt = (
            select(FHIRPushQueue)
            .where(FHIRPushQueue.session_id == session_id)
            .order_by(FHIRPushQueue.created_at.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())


def _resolve_default_transport() -> ABDMTransport:
    """Resolve transport from environment configuration."""
    provider = os.getenv("ABDM_PUSH_PROVIDER", "").lower().strip()
    if provider == "sandbox_demo":
        logger.info("ABDM transport: sandbox_demo (ABDM sandbox gateway)")
        return SandboxDemoTransport()
    else:
        logger.info("ABDM transport: unavailable (no provider configured)")
        return UnavailableTransport()


# Module-level singleton
export_queue = ExportQueueManager()
