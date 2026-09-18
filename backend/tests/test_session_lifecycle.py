"""
Dev 2 Phase 1: Session Lifecycle, Identity, Consent Audit & Privacy Wipe Tests
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db.database import async_session_factory
from app.db.models import ConsentAudit
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_session_start_contract_for_dev1(client: AsyncClient):
    """
    INTEGRATION CHECKPOINT #1:
    Verify POST /api/session/start returns the exact shape Dev 1 expects:
    { "session_id": "uuid", "patient_name": "...", "language": "hi", "abha_id": "..." }
    """
    payload = {
        "abha_id": "rajesh.kumar@abdm",
        "language": "hi",
        "is_caregiver": False,
    }
    response = await client.post("/api/session/start", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "session_id" in data
    assert data["session_id"] != ""
    assert data["patient_name"] == "Rajesh Kumar"
    assert data["language"] == "hi"
    assert data["abha_id"] == "rajesh.kumar@abdm"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_verify_abha_formatting_and_validation(client: AsyncClient):
    """
    Verify ABHA ID verification accepts both 14-digit format and @abdm addresses.
    Rejects invalid formats.
    """
    # 1. Valid @abdm address
    res = await client.post("/api/session/verify-abha", json={"abha_id": "sunita.devi@abdm"})
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Sunita Devi"
    assert data["gender"] == "F"

    # 2. Valid 14-digit ABHA number
    res2 = await client.post("/api/session/verify-abha", json={"abha_id": "91-1024-5829-1482"})
    assert res2.status_code == 200
    assert res2.json()["name"] == "Rajesh Kumar"

    # 3. Invalid ABHA format (e.g. random 4 letters)
    res_invalid = await client.post("/api/session/verify-abha", json={"abha_id": "invalid"})
    assert res_invalid.status_code == 400
    assert "Invalid ABHA format" in res_invalid.json()["detail"]


@pytest.mark.asyncio
async def test_aadhaar_otp_fallback_flow(client: AsyncClient):
    """
    Test 'I don't have an ABHA ID' fallback:
    Aadhaar input (12 digits) -> request OTP -> verify OTP -> unlinked temporary session.
    """
    # 1. Invalid Aadhaar length
    bad_aadhaar = await client.post("/api/session/aadhaar-otp", json={"aadhaar_number": "12345"})
    assert bad_aadhaar.status_code == 400

    # 2. Valid 12-digit Aadhaar
    otp_res = await client.post("/api/session/aadhaar-otp", json={"aadhaar_number": "5432 1098 7654"})
    assert otp_res.status_code == 200
    txn_id = otp_res.json()["txn_id"]
    assert txn_id.startswith("txn_")

    # 3. Verify with Sandbox OTP
    verify_res = await client.post(
        "/api/session/verify-aadhaar-otp",
        json={"txn_id": txn_id, "otp": "123456", "aadhaar_number": "543210987654"},
    )
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert verify_data["is_temporary"] is True
    assert verify_data["label"] == "Session created without ABHA linkage"
    assert verify_data["aadhaar_masked"] == "XXXX-XXXX-7654"


@pytest.mark.asyncio
async def test_consent_audit_append_only_and_immutability(client: AsyncClient):
    """
    Test recording granular 3-step digital consent to consent_audit,
    and verify that UPDATE or DELETE operations trigger a ValueError (immutable audit log).
    """
    # 1. Start a session
    sess_res = await client.post("/api/session/start", json={"language": "en"})
    session_id = sess_res.json()["session_id"]

    # 2. Record consent
    consent_payload = {
        "session_id": session_id,
        "consents": [
            {"action": "share_doctor", "granted": True},
            {"action": "store_abdm", "granted": False},
            {"action": "anonymized_research", "granted": False},
        ],
        "voice_confirmation_ref": "audio_transcript_affirmative_haan_01",
    }
    res = await client.post("/api/session/consent", json=consent_payload)
    assert res.status_code == 200
    assert res.json()["status"] == "recorded"
    assert res.json()["count"] == 3
    assert res.json()["has_voice_evidence"] is True

    # 3. Verify in Database & test immutability constraint
    async with async_session_factory() as db:
        stmt = select(ConsentAudit).where(ConsentAudit.session_id == session_id)
        result = await db.execute(stmt)
        entries = result.scalars().all()
        assert len(entries) == 3

        # Test Append-Only: Attempt UPDATE
        first_entry = entries[0]
        first_entry.granted = False
        with pytest.raises(ValueError, match="append-only"):
            await db.flush()

        await db.rollback()

        # Test Append-Only: Attempt DELETE
        result2 = await db.execute(stmt)
        entry_to_del = result2.scalars().first()
        await db.delete(entry_to_del)
        with pytest.raises(ValueError, match="append-only"):
            await db.flush()


@pytest.mark.asyncio
async def test_session_end_and_privacy_wipe(client: AsyncClient):
    """
    Verify POST /api/session/end marks session completed,
    and purges backend transient memory.
    """
    # 1. Start session
    sess = await client.post("/api/session/start", json={"patient_name": "Test Patient", "language": "hi"})
    sess_id = sess.json()["session_id"]

    # 2. Check active status
    status1 = await client.get(f"/api/session/{sess_id}/status")
    assert status1.status_code == 200
    assert status1.json()["status"] == "active"

    # 3. End session
    end_res = await client.post("/api/session/end", json={"session_id": sess_id})
    assert end_res.status_code == 200
    assert end_res.json()["status"] == "wiped"

    # 4. Verify DB status updated to completed
    status2 = await client.get(f"/api/session/{sess_id}/status")
    assert status2.status_code == 200
    assert status2.json()["status"] == "completed"
    assert status2.json()["ended_at"] is not None
