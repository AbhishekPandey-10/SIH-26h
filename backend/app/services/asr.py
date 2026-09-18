"""
Bhashini ASR Service Wrapper
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Provides speech-to-text conversion for Indian languages via Bhashini ULCA pipeline API.
Supports automatic fallback to plain-text / Web Speech API input.
"""

import base64
import logging
import os

import httpx

logger = logging.getLogger("medikiosk.asr")

# Bhashini ULCA Pipeline config
BHASHINI_USER_ID = os.getenv("BHASHINI_USER_ID", "")
BHASHINI_API_KEY = os.getenv("BHASHINI_API_KEY", "")
BHASHINI_INFERENCE_KEY = os.getenv("BHASHINI_INFERENCE_KEY", "")
BHASHINI_PIPELINE_ENDPOINT = os.getenv(
    "BHASHINI_PIPELINE_ENDPOINT",
    "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"
)


async def transcribe(audio_blob: bytes | str | None, language: str = "hi") -> str:
    """
    Transcribe audio blob into text.

    Args:
        audio_blob: Audio data as bytes, base64 string, or pre-transcribed text string.
        language: Target ISO-639 language code (default 'hi' for Hindi).

    Returns:
        Transcribed string.

    Behavior:
        1. Fallback: If audio_blob is already a plain text string (from frontend Web Speech API),
           it is accepted and returned directly.
        2. Primary: If credentials are configured and audio bytes/base64 are supplied, calls
           Bhashini ASR inference pipeline.
        3. Graceful degradation: If Bhashini fails or credentials are unconfigured, logs a warning
           and returns fallback string or empty string instead of raising an uncaught exception.
    """
    if audio_blob is None:
        return ""

    # Case 1: Fallback path — frontend Web Speech API already transcribed to text
    if isinstance(audio_blob, str):
        # Check if it looks like a base64 audio payload or a plain text transcript
        if not (audio_blob.startswith("data:audio") or len(audio_blob) > 500 and " " not in audio_blob[:50]):
            logger.debug("Transcribe received plain text string directly (Web Speech API fallback)")
            return audio_blob.strip()

    # Case 2: Primary path — Bhashini ASR API call
    if not (BHASHINI_USER_ID and BHASHINI_API_KEY):
        logger.info("Bhashini credentials not set; operating in Web Speech fallback mode.")
        if isinstance(audio_blob, str):
            return audio_blob.strip()
        return ""

    try:
        # Prepare base64 audio payload
        if isinstance(audio_blob, bytes):
            audio_base64 = base64.b64encode(audio_blob).decode("utf-8")
        elif isinstance(audio_blob, str) and audio_blob.startswith("data:audio"):
            # Strip data URI header if present
            audio_base64 = audio_blob.split(",", 1)[-1]
        else:
            audio_base64 = str(audio_blob)

        payload = {
            "pipelineTasks": [
                {
                    "taskType": "asr",
                    "config": {
                        "language": {
                            "sourceLanguage": language
                        },
                        "serviceId": "ai4bharat/conformer-hi-gpu",
                        "audioFormat": "wav",
                        "samplingRate": 16000
                    }
                }
            ],
            "inputData": {
                "audio": [
                    {
                        "audioContent": audio_base64
                    }
                ]
            }
        }

        headers = {
            "Content-Type": "application/json",
            "userID": BHASHINI_USER_ID,
            "ulcaApiKey": BHASHINI_API_KEY
        }
        if BHASHINI_INFERENCE_KEY:
            headers["Authorization"] = BHASHINI_INFERENCE_KEY

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(BHASHINI_PIPELINE_ENDPOINT, json=payload, headers=headers)
            if response.status_code == 200:
                data = response.json()
                transcription = (
                    data.get("pipelineResponse", [{}])[0]
                    .get("output", [{}])[0]
                    .get("source", "")
                )
                logger.info(f"Bhashini ASR transcribed {len(transcription)} chars")
                return transcription.strip()
            else:
                logger.warning(f"Bhashini ASR returned HTTP {response.status_code}: {response.text}")
                return ""
    except Exception as e:
        logger.error(f"Error during Bhashini ASR transcription: {e}")
        # Return fallback
        return ""
