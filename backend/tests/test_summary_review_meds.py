"""
Comprehensive Regression Suite for Assignment 5:
Summaries, Citations, Doctor Review, Contradictions, and Medication Intelligence
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.database import async_session_factory
from app.db.models import (
    ClinicalSummary,
    ConsentAudit,
    ExtractedEntityModel,
    InterviewTranscript,
    Session,
    SummaryResolution,
)
from app.main import app
from app.services.contradiction_detector import contradiction_detector
from app.services.polypharmacy_detector import polypharmacy_detector
from app.services.summary_generator import summary_generator
from app.shared.schemas import SummaryField, SummarySource, SummarySection

client = TestClient(app)
staff_headers = {"Authorization": "Bearer staff_doc_opd_01"}


@pytest.mark.asyncio
async def test_empty_encounter_zero_fabrication():
    """
    Empty encounters must produce ZERO sample disease, prescriptions, deltas,
    or forged document provenance. No sample entities may be seeded into the database.
    """
    session_id = f"test_empty_{uuid.uuid4().hex[:8]}"

    async with async_session_factory() as db:
        sess = Session(id=session_id, status="active", language="en")
        db.add(sess)
        await db.flush()
        db.add(ConsentAudit(session_id=session_id, action="share_doctor", granted=True))
        await db.commit()

    async with async_session_factory() as db:
        fields = await summary_generator.generate_summary(session_id, db)

        # Verify no sample entities were seeded into extracted_entities
        stmt_e = select(ExtractedEntityModel).where(ExtractedEntityModel.session_id == session_id)
        res_e = await db.execute(stmt_e)
        entities = res_e.scalars().all()
        assert len(entities) == 0, "No sample entities should be seeded into extracted_entities table"

        # Verify no fabricated clinical claims
        content_text = " ".join(f.content for f in fields).lower()
        assert "diabetes" not in content_text
        assert "metformin" not in content_text
        assert "amlodipine" not in content_text
        assert "doc_prev_presc_01" not in content_text

        # If changes section exists, it must explicitly state no changes observed, not invent a delta
        changes_f = next((f for f in fields if f.section == "changes_since_last_visit"), None)
        if changes_f:
            assert "no clinical changes observed" in changes_f.content.lower()


@pytest.mark.asyncio
async def test_citation_validation_integrity_and_no_sample_crops():
    """
    1. An empty transcript set cannot validate arbitrary transcript ref IDs.
    2. Nonexistent document ref IDs cannot acquire sample crop (/api/documents/doc_prev_presc_01/crop),
       confidence 0.92, or 'document_extracted' verification.
    3. Hallucinated or source-less claims must be downgraded to 'needs_confirmation'.
    """
    # Test 1: Empty transcripts validating arbitrary transcript ref
    raw_fields = [
        {
            "field_id": "sf_1",
            "section": "hpi",
            "content": "Patient reports severe migraine",
            "sources": [{"type": "transcript", "ref_id": "q_hallucinated_01", "snippet": "migraine"}],
            "verification": "patient_reported",
        },
        {
            "field_id": "sf_2",
            "section": "medications",
            "content": "Amlodipine 5mg prescribed",
            "sources": [{"type": "document", "ref_id": "ent_nonexistent_99", "snippet": "Amlodipine"}],
            "verification": "document_extracted",
        },
        {
            "field_id": "sf_3",
            "section": "allergies",
            "content": "Patient denies penicillin allergy",
            "sources": [],
            "verification": "patient_reported",
        }
    ]

    validated = summary_generator._validate_and_tag_sources(
        raw_fields=raw_fields,
        transcripts=[],  # Empty transcript ground truth
        entities=[],     # Empty entity ground truth
    )

    assert len(validated) == 3

    # Field 1: transcript ref not found -> verification MUST be downgraded
    assert validated[0].verification == "needs_confirmation"
    assert len(validated[0].sources) == 0

    # Field 2: document ref not found -> MUST NOT synthesize doc_prev_presc_01, confidence 0.92
    assert validated[1].verification == "needs_confirmation"
    assert len(validated[1].sources) == 0

    # Field 3: source-less claim -> MUST NOT remain patient_reported or document_extracted
    assert validated[2].verification == "needs_confirmation"


@pytest.mark.asyncio
async def test_unscoped_citation_lookup_blocked():
    """
    An unscoped citation lookup with a reusable question_id must not return
    another session's transcript turn (cross-session data isolation).
    """
    sess_a = f"sess_a_{uuid.uuid4().hex[:8]}"
    sess_b = f"sess_b_{uuid.uuid4().hex[:8]}"

    async with async_session_factory() as db:
        db.add(Session(id=sess_a, status="active", language="en"))
        db.add(Session(id=sess_b, status="active", language="en"))
        await db.flush()

        t_a = InterviewTranscript(
            id=f"tr_a_{uuid.uuid4().hex[:8]}",
            session_id=sess_a,
            turn_number=1,
            question_id="q_cc_01",
            question_text="What brings you here?",
            answer_text="Knee pain in Session A",
            language="en",
            speaker="patient",
            text="Knee pain in Session A",
        )
        t_b = InterviewTranscript(
            id=f"tr_b_{uuid.uuid4().hex[:8]}",
            session_id=sess_b,
            turn_number=1,
            question_id="q_cc_01",
            question_text="What brings you here?",
            answer_text="Chest pain in Session B",
            language="en",
            speaker="patient",
            text="Chest pain in Session B",
        )
        db.add_all([t_a, t_b])
        await db.commit()

    # Query with session_id scoping: returns the correct encounter
    res_a = client.get(f"/api/interview/transcript/q_cc_01?session_id={sess_a}")
    assert res_a.status_code == 200
    assert res_a.json()["session_id"] == sess_a
    assert "Session A" in res_a.json()["answer_text"]

    res_b = client.get(f"/api/interview/transcript/q_cc_01?session_id={sess_b}")
    assert res_b.status_code == 200
    assert res_b.json()["session_id"] == sess_b
    assert "Session B" in res_b.json()["answer_text"]

    # Query without session_id for ambiguous question_id: must return 400 Bad Request to prevent cross-session leakage
    res_unscoped = client.get("/api/interview/transcript/q_cc_01")
    assert res_unscoped.status_code == 400
    assert "session_id is required" in res_unscoped.json()["detail"]


@pytest.mark.asyncio
async def test_put_and_resolution_survive_fresh_db_session_and_restart():
    """
    Verifies that PUT summary field and POST resolve updates survive a completely fresh
    database session (bulletproof nested JSON persistence via deep copy and flag_modified).
    Verifies that a single field edit transitions summary to 'in_review', NOT 'doctor_verified'.
    """
    session_id = f"test_persist_{uuid.uuid4().hex[:8]}"

    async with async_session_factory() as db:
        db.add(Session(id=session_id, status="active", language="en"))
        await db.flush()
        db.add(ConsentAudit(session_id=session_id, action="share_doctor", granted=True))
        await db.flush()

        initial_fields = [
            SummaryField(
                field_id="sf_test_edit",
                section="hpi",
                content="Original unedited text",
                sources=[],
                verification="patient_reported",
            ).model_dump(mode="json"),
            SummaryField(
                field_id="sf_test_conflict",
                section="medications",
                content="Original conflict text",
                sources=[],
                verification="conflicting",
                document_value="Metformin 500mg",
                patient_value="Metformin 1000mg",
            ).model_dump(mode="json"),
        ]

        summary = ClinicalSummary(
            id=f"sum_{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            version=1,
            lens="allopathic",
            chief_complaint="Chest pain",
            fields_json=initial_fields,
            status="draft",
        )
        db.add(summary)
        await db.commit()

    # 1. Doctor PUT field edit
    put_resp = client.put(
        f"/api/summary/{session_id}/field/sf_test_edit",
        json={"content": "Doctor edited content verifying persistence", "doctor_notes": "Reviewed carefully"},
        headers=staff_headers,
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["content"] == "Doctor edited content verifying persistence"
    assert put_resp.json()["verification"] == "doctor_edited"

    # 2. Query via fresh DB session to ensure SQL UPDATE was executed
    async with async_session_factory() as fresh_db:
        stmt = select(ClinicalSummary).where(ClinicalSummary.session_id == session_id)
        res = await fresh_db.execute(stmt)
        persisted_sum = res.scalar_one()

        # Field must be updated in database
        edited_field = next(f for f in persisted_sum.fields_json if f["field_id"] == "sf_test_edit")
        assert edited_field["content"] == "Doctor edited content verifying persistence"
        assert edited_field["verification"] == "doctor_edited"

        # Summary status MUST NOT be 'doctor_verified' from a single field edit!
        assert persisted_sum.status == "in_review"

    # 3. GET /api/summary/{session_id} must return the edited text
    get_resp = client.get(f"/api/summary/{session_id}", headers=staff_headers)
    assert get_resp.status_code == 200
    get_fields = get_resp.json()
    get_edited = next(f for f in get_fields if f["field_id"] == "sf_test_edit")
    assert get_edited["content"] == "Doctor edited content verifying persistence"

    # 4. Doctor resolve conflicting field
    resolve_resp = client.post(
        f"/api/summary/{session_id}/resolve/sf_test_conflict",
        json={
            "resolution_choice": "use_patient",
            "resolved_value": "Metformin 1000mg confirmed by clinician",
            "doctor_note": "Patient confirmed increased dose",
        },
        headers=staff_headers,
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["content"] == "Metformin 1000mg confirmed by clinician"

    # 5. Verify SummaryResolution record exists in fresh session
    async with async_session_factory() as fresh_db2:
        stmt_res = select(SummaryResolution).where(
            SummaryResolution.session_id == session_id,
            SummaryResolution.field_id == "sf_test_conflict",
        )
        res_res = await fresh_db2.execute(stmt_res)
        resolutions = res_res.scalars().all()
        assert len(resolutions) == 1
        assert resolutions[0].resolved_value == "Metformin 1000mg confirmed by clinician"
        assert resolutions[0].resolution_choice == "use_patient"
        assert resolutions[0].doctor_id == "doc_opd_01"


@pytest.mark.asyncio
async def test_explicit_doctor_verification_and_immutable_versions():
    """
    1. Explicit physician sign-off marks summary as 'doctor_verified'.
    2. Subsequent regeneration/lens switch creates a new draft version,
       preserving the prior verified version immutably.
    """
    session_id = f"test_verif_{uuid.uuid4().hex[:8]}"

    async with async_session_factory() as db:
        db.add(Session(id=session_id, status="active", language="en"))
        await db.flush()
        db.add(ConsentAudit(session_id=session_id, action="share_doctor", granted=True))
        await db.flush()

        initial_sum = ClinicalSummary(
            id=f"sum_v1_{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            version=1,
            lens="allopathic",
            chief_complaint="Chest pain",
            fields_json=[{"field_id": "f1", "section": "hpi", "content": "Initial text", "sources": [], "verification": "patient_reported"}],
            status="draft",
        )
        db.add(initial_sum)
        await db.commit()

    # 1. Doctor sign-off
    verif_resp = client.post(
        f"/api/summary/{session_id}/verify",
        json={"doctor_notes": "Case verified by Dr. Sharma"},
        headers=staff_headers,
    )
    assert verif_resp.status_code == 200
    assert verif_resp.json()["status"] == "doctor_verified"
    assert verif_resp.json()["version"] == 1

    # 2. Call generate summary again (regeneration)
    gen_resp = client.post(
        "/api/summary/generate",
        json={"session_id": session_id, "lens": "allopathic"},
        headers=staff_headers,
    )
    assert gen_resp.status_code == 200

    # 3. Check DB records in fresh session
    async with async_session_factory() as fresh_db:
        stmt = (
            select(ClinicalSummary)
            .where(ClinicalSummary.session_id == session_id)
            .order_by(ClinicalSummary.version.asc())
        )
        res = await fresh_db.execute(stmt)
        all_versions = res.scalars().all()

        assert len(all_versions) == 2, "Regeneration must preserve prior verified summary and create a new draft version"
        assert all_versions[0].version == 1
        assert all_versions[0].status == "doctor_verified"
        assert all_versions[1].version == 2
        assert all_versions[1].status == "draft"


@pytest.mark.asyncio
async def test_read_only_get_endpoint_never_regenerates():
    """
    GET /api/summary/{session_id} must be strictly read-only and return 404
    when no summary exists rather than mutating database state.
    """
    session_id = f"test_read_only_{uuid.uuid4().hex[:8]}"

    async with async_session_factory() as db:
        db.add(Session(id=session_id, status="active", language="en"))
        await db.flush()
        db.add(ConsentAudit(session_id=session_id, action="share_doctor", granted=True))
        await db.commit()

    # GET must return 404 Not Found
    resp = client.get(f"/api/summary/{session_id}", headers=staff_headers)
    assert resp.status_code == 404
    assert "No clinical summary found" in resp.json()["detail"]

    # Check DB to ensure no summary was created
    async with async_session_factory() as fresh_db:
        stmt = select(ClinicalSummary).where(ClinicalSummary.session_id == session_id)
        res = await fresh_db.execute(stmt)
        assert res.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_preservation_of_four_plus_medications_and_conflicts():
    """
    Preserves 4+ medications without [:3] truncation, and handles conflicts
    without discarding the remaining medication list.
    """
    session_id = f"test_4meds_{uuid.uuid4().hex[:8]}"

    async with async_session_factory() as db:
        db.add(Session(id=session_id, status="active", language="en"))
        await db.flush()
        db.add(ConsentAudit(session_id=session_id, action="share_doctor", granted=True))

        # 5 distinct document medications
        meds = [
            ("Tab Metformin 500mg BD", "Metformin"),
            ("Tab Telmisartan 40mg OD", "Telmisartan"),
            ("Tab Atorvastatin 20mg HS", "Atorvastatin"),
            ("Tab Pantoprazole 40mg OD", "Pantoprazole"),
            ("Tab Amlodipine 5mg OD", "Amlodipine"),
        ]
        for idx, (val, gen) in enumerate(meds):
            db.add(
                ExtractedEntityModel(
                    id=f"ent_med_{idx+1}_{session_id}",
                    document_id="doc_presc_multi",
                    session_id=session_id,
                    entity_type="medication",
                    value=val,
                    generic_name=gen,
                    confidence=0.98,
                )
            )

        # Patient reports dosage change for Metformin
        db.add(
            InterviewTranscript(
                session_id=session_id,
                turn_number=1,
                question_id="q_med_01",
                question_text="Are you taking your medications?",
                answer_text="Doctor increased Metformin to 1000mg last week",
                language="en",
                node_name="medications",
                speaker="patient",
                text="Doctor increased Metformin to 1000mg last week",
            )
        )
        await db.commit()

    async with async_session_factory() as db:
        fields = await summary_generator.generate_summary(session_id, db)

        med_fields = [f for f in fields if f.section == SummarySection.MEDICATIONS.value]

        # ALL 5 medications must be retained
        assert len(med_fields) >= 5, f"Expected 5 medications retained, got {len(med_fields)}"

        # Verify conflict branch was created for Metformin
        conflict_field = next((f for f in med_fields if f.verification == "conflicting"), None)
        assert conflict_field is not None
        assert "1000" in conflict_field.content

        # Verify other 4 medications are preserved with document_extracted status
        doc_extracted = [f for f in med_fields if f.verification == "document_extracted"]
        assert len(doc_extracted) == 4


def test_polypharmacy_single_entity_not_duplicate():
    """
    A single medication mention (with generic and brand) must NOT produce
    a false duplicate alert.
    """
    # Single entity
    meds = ["Tab Dolo 650mg BD"]
    report = polypharmacy_detector.analyze_medication_list(meds)
    assert len(report.duplicates) == 0, "Single therapy mention must never trigger duplicate alert"

    # Two distinct brands sharing same generic (Paracetamol)
    dup_meds = ["Tab Dolo 650mg BD", "Tab Calpol 500mg SOS"]
    dup_report = polypharmacy_detector.analyze_medication_list(dup_meds)
    assert len(dup_report.duplicates) == 1
    assert dup_report.duplicates[0].generic == "paracetamol"


@pytest.mark.asyncio
async def test_polypharmacy_atenolol_not_negated_by_no():
    """
    Word boundary negation must preserve legitimate drugs like 'atenolol'.
    """
    meds = ["Tab Atenolol 50mg OD", "Tab Amlodipine 5mg OD"]
    report = polypharmacy_detector.analyze_medication_list(meds)
    assert any("atenolol" in m.lower() for m in report.medications_detected)
    assert any("amlodipine" in m.lower() for m in report.medications_detected)

    # Test interview transcript with atenolol
    session_id = f"test_atenolol_{uuid.uuid4().hex[:8]}"
    async with async_session_factory() as db:
        db.add(Session(id=session_id, status="active", language="en"))
        await db.flush()
        db.add(
            InterviewTranscript(
                session_id=session_id,
                turn_number=1,
                question_id="q_med_01",
                question_text="Current medications?",
                answer_text="I take atenolol 50mg daily",
                language="en",
                node_name="medications",
                speaker="patient",
                text="I take atenolol 50mg daily",
            )
        )
        await db.commit()

    async with async_session_factory() as db:
        rep = await polypharmacy_detector.detect_polypharmacy(session_id, db)
        assert any("atenolol" in m.lower() for m in rep.medications_detected)


def test_polypharmacy_combination_drugs_and_interactions():
    """
    Combination drugs ('Metformin + Glimepiride') are parsed into constituent molecules.
    Dangerous interactions (Warfarin + Aspirin) trigger high-severity alert.
    """
    combo = ["Tab Metformin 500mg + Glimepiride 1mg"]
    combo_report = polypharmacy_detector.analyze_medication_list(combo)
    assert len(combo_report.medications_detected) == 2
    detected_lower = [m.lower() for m in combo_report.medications_detected]
    assert any("metformin" in m for m in detected_lower)
    assert any("glimepiride" in m for m in detected_lower)

    # Interaction check
    inter_meds = ["Tab Warfarin 5mg OD", "Tab Ecosprin 75mg OD"]
    inter_report = polypharmacy_detector.analyze_medication_list(inter_meds)
    assert len(inter_report.interactions) >= 1
    assert any("bleeding" in i.message.lower() for i in inter_report.interactions)
    assert inter_report.status == "completed_with_alerts"


def test_null_generic_and_unavailable_data_safety():
    """
    Null generic values must not crash with AttributeError.
    Empty answers must return 0 contradictions without fabrications.
    """
    hist_entities = [
        {
            "entity_id": "e1",
            "type": "medication",
            "value": "Herbal Kwath 20ml",
            "generic": None,  # Explicit None
            "date": "2025-01-10",
            "confidence": 0.9,
        }
    ]

    # Deterministic fallback compare must not crash
    contradictions = contradiction_detector._fallback_compare(
        current_answers=[],
        historical_entities=hist_entities,
    )
    assert len(contradictions) == 0, "No changes should be invented for empty current answers"


@pytest.mark.asyncio
async def test_contradiction_persistence_and_stable_identity():
    """
    Contradictions have deterministic IDs and doctor actions survive database reloads.
    """
    session_id = f"test_contra_persist_{uuid.uuid4().hex[:8]}"

    async with async_session_factory() as db:
        db.add(Session(id=session_id, status="active", language="en"))
        await db.flush()

        db.add(
            ExtractedEntityModel(
                id=f"ent_met_{session_id}",
                document_id="doc_prev",
                session_id=session_id,
                entity_type="medication",
                value="Metformin 500mg BD",
                generic_name="Metformin",
                confidence=0.95,
            )
        )
        db.add(
            InterviewTranscript(
                session_id=session_id,
                turn_number=1,
                question_id="q_med_metformin",
                question_text="What dose of Metformin?",
                answer_text="I now take Metformin 1000mg double dose",
                language="en",
                node_name="medications",
                speaker="patient",
                text="I now take Metformin 1000mg double dose",
            )
        )
        await db.commit()

    async with async_session_factory() as db:
        items1 = await contradiction_detector.detect_contradictions(session_id, db)
        assert len(items1) >= 1
        cid1 = items1[0].id
        assert items1[0].status == "unreviewed"

        # Deterministic ID: rerun detection
        items2 = await contradiction_detector.detect_contradictions(session_id, db)
        assert items2[0].id == cid1, "Contradiction ID must be deterministic across calls"

    # Doctor confirms contradiction
    action_resp = client.post(
        f"/api/intelligence/contradictions/{session_id}/action",
        json={"contradiction_id": cid1, "action": "confirm"},
    )
    assert action_resp.status_code == 200
    assert action_resp.json()["status"] == "acknowledged"

    # Query with a brand new database session to ensure status is loaded from SummaryResolution
    async with async_session_factory() as fresh_db:
        # Clear in-memory cache to simulate full server restart
        contradiction_detector._action_store.pop(session_id, None)

        reloaded_items = await contradiction_detector.detect_contradictions(session_id, fresh_db)
        assert len(reloaded_items) >= 1
        assert reloaded_items[0].status == "confirmed", "Doctor confirmed status must persist across process restart"


@pytest.mark.asyncio
async def test_ask_back_reply_updates_targeted_field():
    """
    Ask-back reply updates only the targeted field in ClinicalSummary with the actual answer.
    """
    session_id = f"test_ask_back_reply_{uuid.uuid4().hex[:8]}"

    async with async_session_factory() as db:
        db.add(Session(id=session_id, status="active", language="en"))
        await db.flush()
        db.add(ConsentAudit(session_id=session_id, action="share_doctor", granted=True))
        await db.flush()

        sum_model = ClinicalSummary(
            id=f"sum_{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            version=1,
            lens="allopathic",
            fields_json=[
                {"field_id": "sf_hpi_01", "section": "hpi", "content": "Chest pain without details", "sources": [], "verification": "patient_reported"},
                {"field_id": "sf_pmh_01", "section": "pmh", "content": "Hypertension", "sources": [], "verification": "patient_reported"},
            ],
            status="draft",
        )
        db.add(sum_model)
        await db.commit()

    # Patient replies to ask-back clarification
    reply_resp = client.post(
        "/api/interview/ask-back/reply",
        json={
            "session_id": session_id,
            "field_id": "sf_hpi_01",
            "answer_text": "Pain radiates to left shoulder and jaw",
            "language": "en",
        },
    )
    assert reply_resp.status_code == 200
    assert "left shoulder and jaw" in reply_resp.json()["content"]

    # Verify that in fresh DB session, ONLY sf_hpi_01 was updated
    async with async_session_factory() as fresh_db:
        stmt = select(ClinicalSummary).where(ClinicalSummary.session_id == session_id)
        res = await fresh_db.execute(stmt)
        updated_sum = res.scalar_one()

        hpi_field = next(f for f in updated_sum.fields_json if f["field_id"] == "sf_hpi_01")
        pmh_field = next(f for f in updated_sum.fields_json if f["field_id"] == "sf_pmh_01")

        assert "left shoulder and jaw" in hpi_field["content"]
        assert pmh_field["content"] == "Hypertension", "Other fields must remain untouched"
