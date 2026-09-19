"""
MediKiosk FastAPI Application Entrypoint
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
from app.db.database import get_schema_error, init_db, is_schema_ready, verify_schema_ready
from app.routes.abdm import router as abdm_router
from app.routes.ayush import router as ayush_router
from app.routes.consent import router as consent_router
from app.routes.documents import router as documents_router
from app.routes.documents import ws_router as scan_ws_router
from app.routes.fhir import router as fhir_router
from app.routes.intelligence import router as intelligence_router
from app.routes.interview import router as interview_router
from app.routes.patient import router as patient_router
from app.routes.red_flag import router as red_flag_router
from app.routes.session import router as session_router
from app.routes.summary import router as summary_router
from app.routes.visualization import router as visualization_router
from app.services.asr import transcribe
from app.services.tts import synthesize

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("medikiosk.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting MediKiosk Backend (env: {settings.ENVIRONMENT}, kiosk: {settings.KIOSK_ID})")
    try:
        await verify_schema_ready()
        logger.info("Database schema verified successfully.")
    except Exception as e:
        logger.critical(f"Database schema verification failed: {e}. App is running in degraded/unhealthy state.")
    yield
    logger.info("Shutting down MediKiosk Backend")


app = FastAPI(
    title="MediKiosk Clinical History-Taking Engine",
    description="Adaptive multilingual voice+touch clinical intake kiosk for Indian OPDs (Dev 1 Backend)",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routes
app.include_router(interview_router)
app.include_router(session_router)
app.include_router(consent_router)
app.include_router(summary_router)
app.include_router(fhir_router)
app.include_router(documents_router)
app.include_router(scan_ws_router)
app.include_router(intelligence_router)
app.include_router(red_flag_router)
app.include_router(patient_router)
app.include_router(visualization_router)
app.include_router(ayush_router)
app.include_router(abdm_router)


@app.get("/health", tags=["System"])
@app.get("/api/health", tags=["System"])
async def health_check(response: Response) -> dict[str, Any]:
    """Health / Liveness check endpoint for container orchestrators and Kiosk PWA."""
    from app.services.red_flag_detector import detector as red_flag_detector

    schema_ok = is_schema_ready()
    if not schema_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "healthy" if schema_ok else "unhealthy",
        "schema_ready": schema_ok,
        "schema_error": get_schema_error(),
        "safety_degraded": red_flag_detector.is_degraded,
        "service": "medikiosk-backend",
        "environment": settings.ENVIRONMENT,
        "kiosk_id": settings.KIOSK_ID,
        "default_language": settings.DEFAULT_LANGUAGE,
        "gemini_provisioned": bool(settings.GEMINI_API_KEY),
        "bhashini_provisioned": bool(settings.BHASHINI_USER_ID and settings.BHASHINI_API_KEY),
    }


@app.get("/ready", tags=["System"])
@app.get("/api/ready", tags=["System"])
async def readiness_check(response: Response) -> dict[str, Any]:
    """
    Readiness probe: validates database readiness, schema parity, and production security posture.
    Refuses traffic if running in production with demo secrets, degraded safety rules, or unverified schema.
    """
    from app.services.red_flag_detector import detector as red_flag_detector

    schema_ok = is_schema_ready()
    is_prod = settings.ENVIRONMENT.lower() in ("production", "prod")

    insecure_reasons: list[str] = []
    if not schema_ok:
        insecure_reasons.append(f"Database schema not ready: {get_schema_error()}")

    if red_flag_detector.is_degraded and is_prod:
        insecure_reasons.append("Emergency safety rule set degraded (fallback rules active in production)")

    if is_prod:
        if settings.STAFF_API_KEY == "dev_staff_secret":
            insecure_reasons.append("Production environment using default STAFF_API_KEY")
        if settings.KIOSK_API_KEY == "dev_kiosk_secret":
            insecure_reasons.append("Production environment using default KIOSK_API_KEY")
        if settings.ALLOW_DEMO_OTP:
            insecure_reasons.append("ALLOW_DEMO_OTP is enabled in production")

    if insecure_reasons:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "environment": settings.ENVIRONMENT,
            "safety_degraded": red_flag_detector.is_degraded,
            "errors": insecure_reasons,
        }

    return {
        "status": "ready",
        "environment": settings.ENVIRONMENT,
        "schema_ready": True,
        "safety_degraded": red_flag_detector.is_degraded,
        "kiosk_id": settings.KIOSK_ID,
    }



class GeminiTestResponse(BaseModel):
    status: str
    provisioned: bool
    model: str
    prompt: str
    response: str | None = None
    error: str | None = None


@app.get("/api/test/gemini", response_model=GeminiTestResponse, tags=["Diagnostics"])
async def test_gemini(prompt: str = Query("Reply in 1 sentence: What is MediKiosk?")):
    """
    Test connectivity to Gemini API.
    If GEMINI_API_KEY is provisioned, makes a live call to the Gemini model.
    """
    api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    if not api_key:
        return GeminiTestResponse(
            status="unconfigured",
            provisioned=False,
            model=settings.GEMINI_MODEL,
            prompt=prompt,
            response=None,
            error="GEMINI_API_KEY is not set. Please set it in .env or environment variables."
        )

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
        )
        return GeminiTestResponse(
            status="success",
            provisioned=True,
            model=settings.GEMINI_MODEL,
            prompt=prompt,
            response=response.text,
            error=None
        )
    except Exception as e:
        logger.error(f"Gemini API test call failed: {e}")
        return GeminiTestResponse(
            status="error",
            provisioned=True,
            model=settings.GEMINI_MODEL,
            prompt=prompt,
            response=None,
            error=str(e)
        )


class BhashiniTestRequest(BaseModel):
    text: str = "नमस्ते, आपको क्या तकलीफ है?"
    language: str = "hi"


@app.post("/api/test/bhashini", tags=["Diagnostics"])
async def test_bhashini(req: BhashiniTestRequest):
    """
    Test Bhashini TTS synthesis and ASR transcription round-trip.
    Falls back gracefully if credentials are not configured.
    """
    audio_url = await synthesize(req.text, req.language)
    transcribed = await transcribe(audio_url or req.text, req.language)

    return {
        "input_text": req.text,
        "language": req.language,
        "bhashini_provisioned": bool(settings.BHASHINI_USER_ID and settings.BHASHINI_API_KEY),
        "tts_result": audio_url,
        "tts_fallback_active": audio_url is None,
        "transcription_result": transcribed,
    }


# ==============================================================================
# Optional Unified Hosting: Serve pre-built React frontend if dist exists
# ==============================================================================
from pathlib import Path
from fastapi.staticfiles import StaticFiles

_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if not _frontend_dist.exists():
    _frontend_dist = Path("/app/frontend/dist")

if _frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="static_frontend")
    logger.info(f"Mounted static frontend distribution from {_frontend_dist}")
