"""
End-to-End Integration Checkpoint #3 Test
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Validates all 4 integration checkpoint criteria executed together:
1. Click-to-Source Wiring: summary citations -> transcript Q&A and document crop/image endpoints.
2. Red-Flag Escalation End-to-End: kiosk trigger -> pause -> staff alert -> dismiss -> resume.
3. Smart Recall: pre-existing scanned document entity -> adaptive skip/confirm verification prompt.
4. Polypharmacy & Contradiction Radar: drug duplicate/interaction alerts, contradiction detection,
   compact "Changes since last visit" section, and conflicting field doctor resolution logged to summary_resolutions.
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.database import async_session_factory
from app.db.models import (
    ClinicalSummary,
    Document,
    ExtractedEntityModel,
    InterviewTranscript,
    RedFlagEventModel,
    Session,
    SummaryResolution,
)
from app.main import app


def test_integration_checkpoint_3_all_four_flows():
    client = TestClient(app)
    session_id = f"test-cp3-{uuid.uuid4().hex[:8]}"

    # --------------------------------------------------------------------------
    # 0. Setup test session and pre-scanned documents for Smart Recall & Provenance
    # --------------------------------------------------------------------------
    start_resp = client.post(
        "/api/session/start",
        json={
            "session_id": session_id,
            "abha_id": "rajesh.cp3@abdm",
            "patient_name": "Rajesh Kumar",
            "language": "hi",
        },
    )
    assert start_resp.status_code == 200

    doc_id = f"doc_cp3_{uuid.uuid4().hex[:6]}"
    ent_id = f"ent_cp3_med_{uuid.uuid4().hex[:6]}"

    import asyncio
    async def seed_db():
        async with async_session_factory() as db:
            # Seed scanned document
            db.add(Document(
                id=doc_id,
                session_id=session_id,
                file_path="tests/test_data/sample_doc.jpg",
                file_type="prescription",
                page_number=1,
                status="extracted",
            ))
            # Seed high-confidence medication entity (for Smart Recall: Metformin 500mg)
            db.add(ExtractedEntityModel(
                id=ent_id,
                document_id=doc_id,
                session_id=session_id,
                entity_type="medication",
                value="Tab Metformin 500mg BD",
                generic_name="Metformin",
                date="2025-01-10",
                bounding_box=[0.12, 0.34, 0.45, 0.08],
                confidence=0.96,
            ))
            # Seed second historical entity for contradiction detection (Glimepiride 1mg)
            db.add(ExtractedEntityModel(
                id=f"ent_cp3_glim_{uuid.uuid4().hex[:6]}",
                document_id=doc_id,
                session_id=session_id,
                entity_type="medication",
                value="Tab Glimepiride 1mg OD",
                generic_name="Glimepiride",
                date="2025-01-10",
                bounding_box=[0.12, 0.44, 0.45, 0.08],
                confidence=0.92,
            ))
            await db.commit()

    asyncio.run(seed_db())

    # --------------------------------------------------------------------------
    # 1. TEST ITEM 3: Smart Recall (Scan Old Doc -> Start Interview -> Verify Confirm Behavior)
    # --------------------------------------------------------------------------
    # Connect to Interview WebSocket
    with client.websocket_connect(f"/ws/interview?session_id={session_id}") as ws:
        q1 = ws.receive_json()
        assert q1["section"] == "chief_complaint"

        # Turn 1: Patient answers with chest complaint
        ws.send_json({
            "session_id": session_id,
            "answer": "सीने में भारीपन है",
            "verbatim_voice": "seene me bhari pan hai",
        })
        q2 = ws.receive_json()
        assert q2["section"] in ("socrates", "pmh")

        # Turn 2: Advance to PMH/Medications
        ws.send_json({
            "session_id": session_id,
            "answer": "5 साल से शुगर है",
        })
        q3 = ws.receive_json()

        # Check that when medications/pmh is reached or evaluated,
        # Smart Recall adapts the question to confirm known fact
        # Turn 3: Patient states dosage change for contradiction radar
        ws.send_json({
            "session_id": session_id,
            "answer": "डॉक्टर ने Metformin 1000mg कर दी है और Glimepiride बंद कर दी है",
            "verbatim_voice": "metformin 1000mg kar di aur glimepiride band kar di",
        })
        q4 = ws.receive_json()
        assert q4 is not None

    # Verify Smart Recall service directly:
    from app.services.smart_recall import smart_recall_service
    from app.shared.schemas import NextQuestion

    async def test_smart_recall_adaptation():
        async with async_session_factory() as db:
            ctx = await smart_recall_service.load_patient_extracted_context(session_id, db)
            assert len(ctx) >= 2
            assert any(e["generic_name"] == "Metformin" for e in ctx)

            generic_q = NextQuestion(
                question_id="q_med_01",
                text="क्या आप कोई नियमित दवाई ले रहे हैं?",
                input_type="voice_touch",
                section="medications",
                progress_pct=50.0,
            )
            adapted = smart_recall_service.adapt_question_with_recall("medications", generic_q, ctx, language="hi")
            # Verify that generic question was replaced by Smart Recall confirmation prompt
            assert adapted.metadata.get("is_smart_recall") is True
            assert "Metformin" in adapted.text
            assert adapted.input_type == "yes_no"
    asyncio.run(test_smart_recall_adaptation())

    # --------------------------------------------------------------------------
    # 2. TEST ITEM 2: Red-Flag Escalation (Kiosk Pause -> Staff Alert -> Dismiss -> Resume)
    # --------------------------------------------------------------------------
    # Trigger red flag via WebSocket
    with client.websocket_connect(f"/ws/interview?session_id={session_id}") as ws:
        _ = ws.receive_json()
        # High acuity trigger
        ws.send_json({
            "session_id": session_id,
            "answer": "सीने में बहुत तेज दर्द है और सांस फूल रही है (chest pain with breathlessness)",
        })
        alert_event = ws.receive_json()
        assert alert_event.get("event") == "red_flag_triggered" or alert_event.get("is_red_flag_warning") is True
        red_flag_data = alert_event.get("data") or alert_event.get("red_flag_details")
        assert red_flag_data is not None
        assert red_flag_data["category"] == "cardiac"
        event_id = red_flag_data.get("event_id") or red_flag_data.get("id")

        # Emergency hold question
        hold_q = ws.receive_json()
        assert hold_q.get("section") == "emergency_hold" or hold_q.get("is_red_flag_warning") is True

        # Staff dismisses red flag via REST
        dismiss_resp = client.post(
            f"/api/red-flag/{event_id}/dismiss",
            json={
                "dismissed_by": "triage_nurse_priya",
                "reason": "ECG performed at triage; non-STEMI cleared; patient stable.",
            },
        )
        assert dismiss_resp.status_code == 200
        dismiss_data = dismiss_resp.json()
        assert dismiss_data["status"] == "dismissed"
        assert dismiss_data["dismissed_by"] == "triage_nurse_priya"

        # Kiosk receives resume notification
        resume_event = ws.receive_json()
        assert resume_event.get("event") == "interview_resume"

    # Verify in DB
    async def verify_red_flag_db():
        async with async_session_factory() as db:
            stmt = select(RedFlagEventModel).where(RedFlagEventModel.id == event_id)
            ev = (await db.execute(stmt)).scalar_one_or_none()
            assert ev is not None
            assert ev.is_dismissed is True
            assert ev.dismissed_by == "triage_nurse_priya"
    asyncio.run(verify_red_flag_db())

    # --------------------------------------------------------------------------
    # 3. TEST ITEM 1: Click-to-Source Wiring (Summary Fields -> Citation Resolution)
    # --------------------------------------------------------------------------
    # Doctor generates summary
    summary_resp = client.post(
        "/api/summary/generate",
        json={"session_id": session_id},
    )
    assert summary_resp.status_code == 200
    summary_fields = summary_resp.json()
    assert len(summary_fields) >= 1

    # Verify at least one field has sources
    fields_with_sources = [f for f in summary_fields if f.get("sources")]
    assert len(fields_with_sources) >= 1

    sample_src = fields_with_sources[0]["sources"][0]
    assert "type" in sample_src
    assert "ref_id" in sample_src

    # Test Transcript Q&A endpoint: GET /api/interview/transcript/{ref_id}
    tr_resp = client.get(f"/api/interview/transcript/{sample_src['ref_id']}")
    assert tr_resp.status_code == 200
    tr_data = tr_resp.json()
    assert "question_text" in tr_data
    assert "answer_text" in tr_data

    # Test Document Crop endpoint: GET /api/documents/{doc_id}/crop?bbox=...
    crop_resp = client.get(f"/api/documents/{doc_id}/crop?bbox=0.12,0.34,0.45,0.08")
    assert crop_resp.status_code == 200
    assert crop_resp.headers.get("content-type") == "image/jpeg"
    assert len(crop_resp.content) > 0

    # Test Document Image endpoint: GET /api/documents/{doc_id}/image
    img_resp = client.get(f"/api/documents/{doc_id}/image")
    assert img_resp.status_code == 200

    # Test Entity Details endpoint: GET /api/documents/entity/{entity_id}
    ent_resp = client.get(f"/api/documents/entity/{ent_id}")
    assert ent_resp.status_code == 200
    ent_data = ent_resp.json()
    assert ent_data["value"] == "Tab Metformin 500mg BD"
    assert ent_data["bounding_box"] == [0.12, 0.34, 0.45, 0.08]

    # --------------------------------------------------------------------------
    # 4. TEST ITEM 4: Polypharmacy & Contradiction Radar & Doctor Resolution
    # --------------------------------------------------------------------------
    # Polypharmacy API: POST /api/intelligence/polypharmacy
    poly_resp = client.post(
        "/api/intelligence/polypharmacy",
        json={"session_id": session_id},
    )
    assert poly_resp.status_code == 200
    poly_data = poly_resp.json()
    assert "alerts" in poly_data
    assert isinstance(poly_data["alerts"], list)

    # Contradiction Detection API: POST /api/intelligence/contradictions
    contra_resp = client.post(
        "/api/intelligence/contradictions",
        json={"session_id": session_id},
    )
    assert contra_resp.status_code == 200
    contra_data = contra_resp.json()
    assert contra_data["count"] >= 1
    assert "delta_summary" in contra_data
    assert len(contra_data["contradictions"]) >= 1

    first_contra = contra_data["contradictions"][0]
    assert "field" in first_contra
    assert "old_value" in first_contra
    assert "new_value" in first_contra
    assert "change_type" in first_contra

    # Doctor actions on contradiction card: confirm change
    action_resp = client.post(
        f"/api/intelligence/contradictions/{session_id}/action",
        json={"contradiction_id": first_contra["id"], "action": "confirm"},
    )
    assert action_resp.status_code == 200
    assert action_resp.json()["status"] == "acknowledged"

    # "Changes since last visit" section in summary JSON
    changes_section = next((f for f in summary_fields if f.get("section") == "changes_since_last_visit"), None)
    assert changes_section is not None
    assert changes_section["changed_since_last"] is True
    assert len(changes_section["content"]) > 0

    # Conflicting field resolution: POST /api/summary/{session_id}/resolve/{field_id}
    field_to_resolve = summary_fields[0]
    resolve_resp = client.post(
        f"/api/summary/{session_id}/resolve/{field_to_resolve['field_id']}",
        json={
            "resolution_choice": "use_patient",
            "resolved_value": "Patient verbally confirmed dosage increased to 1000mg OD.",
            "doctor_id": "dr_sharma_104",
            "doctor_note": "Confirmed with patient: blood glucose control required titration.",
        },
    )
    assert resolve_resp.status_code == 200
    resolved_field = resolve_resp.json()
    assert resolved_field["verification"] == "doctor_edited"
    assert "1000mg" in resolved_field["content"]

    # Verify resolution logged in DB table `summary_resolutions`
    async def verify_resolution_db():
        async with async_session_factory() as db:
            stmt = select(SummaryResolution).where(
                SummaryResolution.session_id == session_id,
                SummaryResolution.field_id == field_to_resolve["field_id"],
            )
            res_log = (await db.execute(stmt)).scalar_one_or_none()
            assert res_log is not None
            assert res_log.doctor_id == "dr_sharma_104"
            assert res_log.resolution_choice == "use_patient"
            assert "1000mg" in res_log.resolved_value
    asyncio.run(verify_resolution_db())
