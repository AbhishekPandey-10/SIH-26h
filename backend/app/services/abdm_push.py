"""
ABDM FHIR Bundle Push Service with Resilience & Queueing
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""

import logging
import os
import uuid
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import FHIRPushQueue

logger = logging.getLogger("medikiosk.abdm_push")


class ABDMPushService:
    def __init__(self):
        self.sandbox_url = getattr(settings, "ABDM_SANDBOX_URL", "https://dev.abdm.gov.in")
        self.client_id = os.getenv("ABDM_CLIENT_ID", "MEDIKIOSK_SANDBOX_CLIENT")
        self.client_secret = os.getenv("ABDM_CLIENT_SECRET", "MEDIKIOSK_SANDBOX_SECRET")

    async def push_bundle(
        self,
        session_id: str,
        bundle: dict[str, Any],
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        Pushes FHIR bundle to ABDM sandbox gateway.
        Handles timeout and network failures gracefully by queueing into fhir_push_queue.
        """
        endpoint = f"{self.sandbox_url}/v0.5/health-information/notify"
        headers = {
            "Content-Type": "application/json",
            "X-CM-ID": "sbx",
            "Authorization": f"Bearer mock_abdm_token_{uuid.uuid4().hex[:8]}",
        }

        # Attempt push to sandbox
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                # We attempt the request with a short timeout
                response = await client.post(endpoint, json=bundle, headers=headers)
                if response.status_code in [200, 201, 202]:
                    abdm_ref = f"ABDM-REF-{uuid.uuid4().hex[:10].upper()}"
                    logger.info(f"Successfully pushed FHIR bundle to ABDM. Ref: {abdm_ref}")
                    return {
                        "success": True,
                        "abdm_ref": abdm_ref,
                        "status": "pushed",
                    }
                else:
                    raise httpx.HTTPStatusError(
                        f"ABDM gateway returned HTTP {response.status_code}: {response.text}",
                        request=response.request,
                        response=response,
                    )

        except Exception as e:
            error_msg = str(e)
            logger.warning(f"ABDM push failed ({error_msg}); queueing bundle into fhir_push_queue for retry.")

            # Resilient fallback: store in fhir_push_queue for retry
            queue_entry = FHIRPushQueue(
                id=f"fpq_{uuid.uuid4().hex[:12]}",
                session_id=session_id,
                bundle_json=bundle,
                status="failed",
                retry_count=1,
                last_error=error_msg,
            )
            db.add(queue_entry)
            await db.commit()

            return {
                "success": False,
                "error": error_msg,
                "queue_id": queue_entry.id,
                "message": "Push failed; bundle stored in retry queue.",
            }


abdm_push_service = ABDMPushService()
