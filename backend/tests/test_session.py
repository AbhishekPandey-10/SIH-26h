"""
Unit tests for ABDM Sandbox Service & Session Lifecycle
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""

import pytest
from fastapi.testclient import TestClient

from app.services.abdm import (
    request_otp,
    verify_abha,
    verify_otp,
)


from app.config import settings


@pytest.mark.asyncio
async def test_abdm_verify_known_abha_ids():
    """Verify all pre-seeded test ABHA IDs return known demographics."""
    for abha_id in ["rajesh.kumar@abdm", "sunita.devi@abdm", "amit.sharma@abdm", "priya.patel@abdm"]:
        patient = await verify_abha(abha_id)
        assert patient.abha_id == abha_id
        assert patient.name != ""
        assert patient.gender in ("M", "F", "O")
        assert patient.is_verified is True


@pytest.mark.asyncio
async def test_abdm_otp_flow():
    """Verify request_otp and verify_otp produce an authenticated session."""
    txn_id = await request_otp("9876543210")
    assert txn_id.startswith("txn_")

    session = await verify_otp(txn_id, "123456", "rajesh.kumar@abdm")
    assert session.session_id.startswith("sess_")
    assert session.auth_token.startswith("abdm_jwt_")
    assert session.patient.name == "Rajesh Kumar"


@pytest.mark.asyncio
async def test_abdm_invalid_otp():
    """Verify incorrect OTP is rejected."""
    txn_id = await request_otp("9876543210")
    with pytest.raises(ValueError):
        await verify_otp(txn_id, "000000")


def test_session_rest_endpoints(client: TestClient):
    """Verify session API routes with kiosk authentication and consent lifecycle."""
    kiosk_headers = {"Authorization": f"Bearer {settings.KIOSK_API_KEY}"}

    # 1. Unauthenticated start is rejected
    res_unauth = client.post("/api/session/start", json={"language": "hi", "is_caregiver": False})
    assert res_unauth.status_code == 401

    # 2. Authenticated kiosk starts session
    res_start = client.post("/api/session/start", json={"language": "hi", "is_caregiver": False}, headers=kiosk_headers)
    assert res_start.status_code == 200
    data_start = res_start.json()
    assert "session_id" in data_start
    assert data_start["status"] == "active"
    sess_id = data_start["session_id"]
    session_token = data_start.get("session_token") or f"session_{sess_id}"
    session_headers = {"Authorization": f"Bearer {session_token}"}

    # 3. Verify ABHA endpoint
    res_abha = client.post("/api/session/verify-abha?abha_id=rajesh.kumar@abdm", headers=session_headers)
    assert res_abha.status_code == 200
    assert res_abha.json()["name"] == "Rajesh Kumar"

    # 4. Request OTP endpoint
    res_otp_req = client.post("/api/session/request-otp", json={"identifier": "rajesh.kumar@abdm"}, headers=session_headers)
    assert res_otp_req.status_code == 200
    txn_id = res_otp_req.json()["txn_id"]

    # 5. Verify OTP endpoint
    res_otp_ver = client.post(
        "/api/session/verify-otp",
        json={
            "txn_id": txn_id,
            "otp": "123456",
            "abha_id": "rajesh.kumar@abdm",
        },
        headers=session_headers,
    )
    assert res_otp_ver.status_code == 200
    session_data = res_otp_ver.json()
    assert session_data["patient"]["name"] == "Rajesh Kumar"

    # 6. Unconsented FHIR retrieval is rejected (HTTP 403)
    res_fhir_unconsented = client.get(f"/api/session/{sess_id}/fhir?abha_id=rajesh.kumar@abdm", headers=session_headers)
    assert res_fhir_unconsented.status_code == 403

    # 7. Record consent for share_doctor
    res_consent = client.post(
        "/api/session/consent",
        json={
            "session_id": sess_id,
            "consents": [{"action": "share_doctor", "granted": True}],
        },
        headers=session_headers,
    )
    assert res_consent.status_code == 200

    # 8. Consented FHIR retrieval succeeds
    res_fhir = client.get(f"/api/session/{sess_id}/fhir?abha_id=rajesh.kumar@abdm", headers=session_headers)
    assert res_fhir.status_code == 200
    fhir_bundles = res_fhir.json()
    assert isinstance(fhir_bundles, list)
    assert len(fhir_bundles) > 0
