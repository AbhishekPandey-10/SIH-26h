"""
MediKiosk FastAPI Application Entrypoint
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
from app.db.database import init_db
from app.routes.documents import router as documents_router
from app.routes.documents import ws_router as scan_ws_router
from app.routes.fhir import router as fhir_router
from app.routes.interview import router as interview_router
from app.routes.session import router as session_router
from app.routes.summary import router as summary_router
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
        await init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.warning(f"Database initialization warning: {e}")
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
app.include_router(summary_router)
app.include_router(fhir_router)
app.include_router(documents_router)
app.include_router(scan_ws_router)


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, Any]:
    """Health check endpoint for container orchestrators and Kiosk PWA."""
    return {
        "status": "healthy",
        "service": "medikiosk-backend",
        "environment": settings.ENVIRONMENT,
        "kiosk_id": settings.KIOSK_ID,
        "default_language": settings.DEFAULT_LANGUAGE,
        "gemini_provisioned": bool(settings.GEMINI_API_KEY),
        "bhashini_provisioned": bool(settings.BHASHINI_USER_ID and settings.BHASHINI_API_KEY),
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
