"""
End-to-End Integration Checkpoint #2 Test
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Validates the full pipeline:
ABHA session start -> Consent -> Interview WebSocket -> Extracted document entities ->
Summary Generation -> Doctor Field Edit -> FHIR R4 Preview -> ABDM Push.
"""

import uuid
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.database import async_session_factory
from app.db.models import ClinicalSummary, ConsentAudit, ExtractedEntityModel, Session
from app.main import app


def test_real_end_to_end_flow():
    client = TestClient(app)

    # 1. Start real session with ABHA ID
    start_resp = client.post(
        "/api/session/start",
        json={
            "abha_id": "rajesh.kumar@abdm",
            "patient_name": "Rajesh Kumar",
            "language": "hi",
        },
    )
    assert start_resp.status_code == 200
    session_data = start_resp.json()
    session_id = session_data["session_id"]
    assert session_id is not None
    assert session_data["patient_name"] == "Rajesh Kumar"

    # 2. Grant 3-step digital consent
    consent_resp = client.post(
        "/api/session/consent",
        json={
            "session_id": session_id,
            "consents": [
                {"action": "share_doctor", "granted": True},
                {"action": "store_abdm", "granted": True},
                {"action": "anonymized_research", "granted": False},
            ],
            "voice_confirmation_ref": "audio_consent_01.wav",
        },
    )
    assert consent_resp.status_code == 200

    # 3. Connect to Interview WebSocket and perform interview turns
    with client.websocket_connect(f"/ws/interview?session_id={session_id}") as ws:
        q1 = ws.receive_json()
        assert q1["section"] == "chief_complaint"

        # Turn 1: Patient answers with chest pain
        ws.send_json({
            "session_id": session_id,
            "answer": "सीने में भारीपन और हल्का दर्द है",
            "verbatim_voice": "seene me bhari pan hai",
        })
        q2 = ws.receive_json()
        assert q2["section"] in ("socrates", "pmh")

        # Turn 2: Patient answers with past history
        ws.send_json({
            "session_id": session_id,
            "answer": "मुझे 5 साल से शुगर की बीमारी है",
        })
        q3 = ws.receive_json()
        assert q3 is not None

    # 4. Dev 2 document ingestion: attach extracted entity
    test_ent_id = f"ent_e2e_{uuid.uuid4().hex[:8]}"
    client_ent = ExtractedEntityModel(
        id=test_ent_id,
        document_id="doc_prev_presc_01",
        session_id=session_id,
        entity_type="medication",
        value="Tab Metformin 500mg BD",
        generic_name="Metformin",
        date="2025-01-10",
        bounding_box=[0.1, 0.2, 0.4, 0.05],
        confidence=0.96,
    )

    import asyncio
    async def add_entity():
        async with async_session_factory() as db:
            db.add(client_ent)
            await db.commit()
    asyncio.run(add_entity())

    # 5. Doctor UI calls Summary Generation
    summary_resp = client.post(
        "/api/summary/generate",
        json={"session_id": session_id},
    )
    assert summary_resp.status_code == 200
    summary_fields = summary_resp.json()
    assert isinstance(summary_fields, list)
    assert len(summary_fields) >= 1

    # Verify citation sources and verification tags
    field_to_edit = summary_fields[0]
    assert "field_id" in field_to_edit
    assert "verification" in field_to_edit

    # 6. Doctor inline edit of summary field
    edit_resp = client.put(
        f"/api/summary/{session_id}/field/{field_to_edit['field_id']}",
        json={
            "content": "Patient reports retrosternal tightness with known DM2 on Metformin.",
            "doctor_notes": "Retrosternal chest discomfort confirmed during consultation.",
        },
    )
    assert edit_resp.status_code == 200
    edited_field = edit_resp.json()
    assert edited_field["verification"] == "doctor_edited"
    assert "retrosternal" in edited_field["content"].lower()

    # 7. Doctor previews FHIR R4 Bundle
    fhir_preview_resp = client.get(
        f"/api/fhir/preview/{session_id}?patient_abha_id=rajesh.kumar@abdm"
    )
    assert fhir_preview_resp.status_code == 200
    bundle = fhir_preview_resp.json()
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "document"
    assert bundle["entry"][0]["resource"]["resourceType"] == "Composition"

    # 8. Doctor pushes to ABDM
    push_resp = client.post(
        "/api/fhir/push",
        json={
            "session_id": session_id,
            "patient_abha_id": "rajesh.kumar@abdm",
        },
    )
    assert push_resp.status_code == 200
    push_data = push_resp.json()
    assert push_data["success"] is True or push_data.get("queue_id") is not None

    # 9. Verify DB integrity
    async def verify_db():
        async with async_session_factory() as db:
            # Consent audit records exist and immutable
            stmt_c = select(ConsentAudit).where(ConsentAudit.session_id == session_id)
            consents = (await db.execute(stmt_c)).scalars().all()
            assert len(consents) == 3

            # ClinicalSummary was updated to doctor_verified
            stmt_s = select(ClinicalSummary).where(ClinicalSummary.session_id == session_id)
            summary_record = (await db.execute(stmt_s)).scalar_one_or_none()
            assert summary_record is not None
            assert summary_record.status == "doctor_verified"
    asyncio.run(verify_db())
