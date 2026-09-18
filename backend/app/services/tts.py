"""
Bhashini TTS Service Wrapper
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Synthesizes speech in Indian languages via Bhashini ULCA pipeline API.
Fallback returns None (null) so the kiosk frontend automatically uses native Web Speech synthesis.
"""

import logging
import os

import httpx

logger = logging.getLogger("medikiosk.tts")

BHASHINI_USER_ID = os.getenv("BHASHINI_USER_ID", "")
BHASHINI_API_KEY = os.getenv("BHASHINI_API_KEY", "")
BHASHINI_INFERENCE_KEY = os.getenv("BHASHINI_INFERENCE_KEY", "")
BHASHINI_PIPELINE_ENDPOINT = os.getenv(
    "BHASHINI_PIPELINE_ENDPOINT",
    "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"
)


async def synthesize(text: str, language: str = "hi", gender: str = "female") -> str | None:
    """
    Synthesizes speech for the provided text in the target language.

    Args:
        text: Clinical question or prompt text to be spoken.
        language: Target ISO language code ('hi', 'ta', 'te', 'bn', etc.).
        gender: Voice gender preference ('female' or 'male').

    Returns:
        audio_url: Base64 data URI string (`data:audio/wav;base64,...`) or cloud URL.
        Returns None (null) on failure or when unconfigured, triggering frontend Web Speech fallback.
    """
    if not text or not text.strip():
        return None

    # Fallback: if credentials are not configured, return None so frontend uses Web Speech synthesis
    if not (BHASHINI_USER_ID and BHASHINI_API_KEY):
        logger.info("Bhashini credentials not set; returning None for frontend Web Speech synthesis.")
        return None

    try:
        payload = {
            "pipelineTasks": [
                {
                    "taskType": "tts",
                    "config": {
                        "language": {
                            "sourceLanguage": language
                        },
                        "serviceId": "ai4bharat/indic-tts-coqui-indo_aryan-gpu",
                        "gender": gender,
                        "samplingRate": 22050
                    }
                }
            ],
            "inputData": {
                "input": [
                    {
                        "source": text
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
                audio_content = (
                    data.get("pipelineResponse", [{}])[0]
                    .get("audio", [{}])[0]
                    .get("audioContent", "")
                )
                if audio_content:
                    return f"data:audio/wav;base64,{audio_content}"
                return None
            else:
                logger.warning(f"Bhashini TTS returned HTTP {response.status_code}: {response.text}")
                return None
    except Exception as e:
        logger.error(f"Error during Bhashini TTS synthesis: {e}")
        return None
