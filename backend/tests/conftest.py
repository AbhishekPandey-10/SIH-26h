"""
Pytest shared fixtures for MediKiosk backend
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Reusable FastAPI test client."""
    with TestClient(app) as c:
        yield c
