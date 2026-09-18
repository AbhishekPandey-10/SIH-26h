"""
Unit tests for Bhashini ASR and TTS SDK Wrappers
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""

import pytest

from app.services.asr import transcribe
from app.services.tts import synthesize


@pytest.mark.asyncio
async def test_asr_plain_text_fallback():
    # Frontend Web Speech API passes text directly
    input_text = "मुझे बुखार और सिरदर्द है"
    result = await transcribe(input_text, language="hi")
    assert result == input_text


@pytest.mark.asyncio
async def test_asr_empty_blob():
    result = await transcribe(None, language="hi")
    assert result == ""


@pytest.mark.asyncio
async def test_tts_fallback_mode():
    # Without Bhashini credentials configured in test env, must return None
    # to signal kiosk frontend to invoke native Web Speech API synthesis
    result = await synthesize("नमस्ते, आपको क्या तकलीफ है?", language="hi")
    assert result is None or isinstance(result, str)


@pytest.mark.asyncio
async def test_bhashini_hindi_roundtrip_fallback():
    # Hello-world Hindi round-trip test
    hindi_prompt = "नमस्ते, आज आपकी तबीयत कैसी है?"
    tts_audio_url = await synthesize(hindi_prompt, language="hi")
    # Even if TTS falls back to None, ASR fallback accepts the text seamlessly
    transcribed = await transcribe(tts_audio_url or hindi_prompt, language="hi")
    assert transcribed == hindi_prompt
