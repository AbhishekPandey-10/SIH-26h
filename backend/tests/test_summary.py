"""
Comprehensive Unit & Integration Tests for Clinical Summary, FHIR, and Ask-Back (Phase 2)
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.database import async_session_factory
from app.db.models import (
    ClinicalSummary,
    ExtractedEntityModel,
    InterviewTranscript,
)
from app.main import app
from app.services.fhir_builder import fhir_builder
from app.services.summary_generator import summary_generator
from app.shared.schemas import SummaryField, SummarySource


@pytest.mark.asyncio
async def test_summary_generation_from_transcripts_and_entities():
    session_id = f"test_sum_{uuid.uuid4().hex[:8]}"

    async with async_session_factory() as db:
        # 1. Seed transcript turns
        t1 = InterviewTranscript(
            session_id=session_id,
            turn_number=1,
            question_id="q_cc_01",
            question_text="आज अस्पताल किस तकलीफ के कारण आना पड़ा?",
            answer_text="सीने में 2 दिन से तेज दर्द और भारीपन है (Chest pain for 2 days)",
            language="hi",
            node_name="chief_complaint",
            speaker="patient",
            text="सीने में 2 दिन से तेज दर्द और भारीपन है",
        )
        t2 = InterviewTranscript(
            session_id=session_id,
            turn_number=2,
            question_id="q_pmh_01",
            question_text="क्या आपको पहले से कोई बीमारी है?",
            answer_text="उच्च रक्तचाप और मधुमेह (Hypertension and Diabetes)",
            language="hi",
            node_name="pmh",
            speaker="patient",
            text="उच्च रक्तचाप और मधुमेह",
        )
        db.add_all([t1, t2])

        # 2. Seed extracted document entities
        e1 = ExtractedEntityModel(
            id=f"ent_diag_dm_{session_id}",
            document_id="doc_prev_opd_01",
            session_id=session_id,
            entity_type="diagnosis",
            value="Type 2 Diabetes Mellitus",
            date="2025-01-10",
            bounding_box=[0.1, 0.2, 0.4, 0.05],
            confidence=0.98,
        )
        e2 = ExtractedEntityModel(
            id=f"ent_med_metformin_{session_id}",
            document_id="doc_prev_opd_01",
            session_id=session_id,
            entity_type="medication",
            value="Tab Metformin 500mg BD",
            generic_name="Metformin",
            date="2025-01-10",
            bounding_box=[0.1, 0.3, 0.5, 0.06],
            confidence=0.99,
        )
        db.add_all([e1, e2])
        await db.commit()

        # 3. Generate summary
        fields = await summary_generator.generate_summary(session_id, db)

        # Assertions on fields
        assert len(fields) >= 2
        sections = [f.section for f in fields]
        assert "chief_complaint" in sections

        # Check source-tagging and citations
        cc_field = next(f for f in fields if f.section == "chief_complaint")
        assert len(cc_field.sources) >= 1
        assert cc_field.sources[0].type == "transcript"
        assert cc_field.sources[0].ref_id == "q_cc_01"
        assert cc_field.verification == "patient_reported"

        # Check document-extracted field
        med_field = next((f for f in fields if f.section == "medications"), None)
        if med_field:
            doc_source = next((s for s in med_field.sources if s.type == "document"), None)
            if doc_source:
                assert doc_source.ref_id.startswith("ent_")
                assert doc_source.bbox_crop_url is not None
                assert "/api/documents/" in doc_source.bbox_crop_url
                assert med_field.verification == "document_extracted"

        # Verify DB persistence of summary
        stmt = select(ClinicalSummary).where(ClinicalSummary.session_id == session_id)
        res = await db.execute(stmt)
        summary_record = res.scalar_one_or_none()
        assert summary_record is not None
        assert summary_record.fields_json is not None
        assert len(summary_record.fields_json) == len(fields)


def test_source_tagging_validation_downgrades_hallucinations():
    # Hallucinated source reference (ref_id not in transcripts or entities)
    raw_fields = [
        {
            "field_id": "sf_test_hallucinated",
            "section": "pmh",
            "content": "Patient has asthma (hallucinated citation)",
            "sources": [
                {
                    "type": "transcript",
                    "ref_id": "q_hallucinated_999",  # Does NOT exist
                    "snippet": "I have asthma",
                }
            ],
            "verification": "patient_reported",
        }
    ]

    # Transcripts with only q_cc_01
    valid_transcript = InterviewTranscript(
        id=str(uuid.uuid4()),
        session_id="s1",
        turn_number=1,
        question_id="q_cc_01",
        question_text="What is your complaint?",
        answer_text="Knee pain",
        language="en",
        speaker="patient",
        text="Knee pain",
    )

    validated = summary_generator._validate_and_tag_sources(
        raw_fields=raw_fields,
        transcripts=[valid_transcript],
        entities=[],
    )

    assert len(validated) == 1
    # Verification MUST be downgraded to needs_confirmation
    assert validated[0].verification == "needs_confirmation"


def test_fhir_bundle_generation():
    fields = [
        SummaryField(
            field_id="sf_01",
            section="chief_complaint",
            content="Chest pain for 2 days",
            sources=[SummarySource(type="transcript", ref_id="q_cc_01", snippet="Chest pain")],
            verification="patient_reported",
            changed_since_last=False,
        ),
        SummaryField(
            field_id="sf_02",
            section="medications",
            content="Metformin 500mg twice daily",
            sources=[
                SummarySource(
                    type="document",
                    ref_id="ent_med_01",
                    snippet="Metformin",
                    bbox_crop_url="/api/documents/doc_01/crop?bbox=0.1,0.2,0.3,0.4",
                )
            ],
            verification="document_extracted",
            changed_since_last=False,
        ),
        SummaryField(
            field_id="sf_03",
            section="allergies",
            content="No known drug allergies",
            sources=[SummarySource(type="transcript", ref_id="q_all_01", snippet="None")],
            verification="patient_reported",
            changed_since_last=False,
        ),
    ]

    bundle = fhir_builder.build_bundle(
        session_id="test_fhir_sess_01",
        summary_fields=fields,
        patient_abha_id="rajesh.kumar@abdm",
        encounter_id="enc_001",
    )

    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "document"
    assert len(bundle["entry"]) >= 4

    # Entry 0 MUST be Composition
    composition = bundle["entry"][0]["resource"]
    assert composition["resourceType"] == "Composition"
    assert composition["status"] == "final"
    assert len(composition["section"]) == 3

    # Check referenced Condition, MedicationStatement, AllergyIntolerance, DocumentReference
    resource_types = [e["resource"]["resourceType"] for e in bundle["entry"]]
    assert "Composition" in resource_types
    assert "Condition" in resource_types
    assert "MedicationStatement" in resource_types
    assert "AllergyIntolerance" in resource_types
    assert "DocumentReference" in resource_types


def test_post_summary_generate_endpoint():
    client = TestClient(app)
    response = client.post("/api/summary/generate", json={"session_id": "dev-test-001"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "field_id" in data[0]
    assert "section" in data[0]
    assert "sources" in data[0]
    assert "verification" in data[0]


def test_post_fhir_push_endpoint():
    client = TestClient(app)
    response = client.post(
        "/api/fhir/push",
        json={"session_id": "dev-test-001", "patient_abha_id": "rajesh.kumar@abdm"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    # Either successful sandbox push or stored in queue for retry
    if data["success"]:
        assert data["abdm_ref"] is not None
    else:
        assert data["queue_id"] is not None
        assert "retry" in data.get("message", "").lower()


def test_ask_back_flow():
    client = TestClient(app)
    session_id = "test_ask_back_sess_01"

    # Call ask-back endpoint
    response = client.post(
        "/api/interview/ask-back",
        json={
            "session_id": session_id,
            "field_id": "sf_hpi_01",
            "question_text": "क्या आपको सीने में दर्द के साथ पसीना भी आ रहा है? (Any sweating with chest pain?)",
            "answer_text": "हाँ, हल्का पसीना आता है जब दर्द तेज होता है।",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["field_id"] == "sf_hpi_01"
    assert data["changed_since_last"] is True
    assert len(data["sources"]) >= 1
    assert data["sources"][0]["ref_id"].startswith("q_ask_back_")
