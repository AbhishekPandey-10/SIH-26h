"""
Pytest Shared Configuration and Fixtures
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Synchronous FastAPI test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_gemini():
    """
    Mock fixture for Google GenAI / Gemini responses.
    Allows unit and integration tests to run offline without live API credentials.
    """
    mock_response = MagicMock()
    mock_response.text = (
        '{"question_id": "q_mock_01", "text": "क्या आपको बुखार भी है?", '
        '"input_type": "voice", "options": ["हाँ", "नहीं"], '
        '"metadata": {"socrates_axis": "associated", "category": "hpi"}}'
    )

    mock_client = MagicMock()
    mock_client.aio = MagicMock()
    mock_client.aio.models = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
    mock_client.models = MagicMock()
    mock_client.models.generate_content = MagicMock(return_value=mock_response)

    with patch("google.genai.Client", return_value=mock_client) as patcher:
        yield {
            "client": mock_client,
            "response": mock_response,
            "patcher": patcher,
        }
