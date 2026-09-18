"""
Unit tests for API contract Pydantic models
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.shared.schemas import (
    ExtractedEntity,
    FHIRBundlePayload,
    InterviewAnswer,
    NextQuestion,
    RedFlagEvent,
    SummaryField,
    SummarySource,
)


def test_next_question_valid():
    q = NextQuestion(
        question_id="q_cc_01",
        text="नमस्ते, आज आपको क्या समस्या है?",
        input_type="voice_touch",
        section="chief_complaint",
        progress_pct=10.0,
    )
    assert q.question_id == "q_cc_01"
    assert q.progress_pct == 10.0
    assert q.is_red_flag_warning is False
    assert q.audio_url is None

    # Serialization round-trip
    dumped = q.model_dump_json()
    loaded = NextQuestion.model_validate_json(dumped)
    assert loaded.question_id == q.question_id


def test_next_question_with_options_and_alert():
    q = NextQuestion(
        question_id="q_choice_01",
        text="Select your medical history:",
        input_type="choice",
        options=["Diabetes", "Hypertension"],
        section="pmh",
        progress_pct=40.0,
        is_red_flag_warning=True,
        red_flag_details={"severity": "red", "category": "cardiac"}
    )
    assert len(q.options) == 2
    assert q.is_red_flag_warning is True
    assert q.red_flag_details["category"] == "cardiac"


def test_next_question_invalid_input_type():
    with pytest.raises(ValidationError):
        NextQuestion(
            question_id="q_bad",
            text="Invalid",
            input_type="unknown_type",  # Invalid literal
            section="chief_complaint"
        )


def test_interview_answer_valid():
    ans = InterviewAnswer(
        question_id="q_cc_01",
        answer_text="मुझे 2 दिन से सीने में दर्द है",
        language="hi",
    )
    assert ans.question_id == "q_cc_01"
    assert ans.language == "hi"
    assert isinstance(ans.timestamp, datetime)


def test_summary_field_with_citations():
    source = SummarySource(
        type="document",
        ref_id="doc_prescription_001",
        snippet="Tab Glycomet 500mg BD",
        bbox_crop_url="http://localhost:8000/api/documents/crop/doc_prescription_001_bbox1.png"
    )
    field = SummaryField(
        field_id="sf_med_01",
        section="medications",
        content="Patient is taking Metformin (Glycomet) 500mg twice daily",
        sources=[source],
        verification="document_extracted",
        changed_since_last=False
    )
    assert field.verification == "document_extracted"
    assert len(field.sources) == 1
    assert field.sources[0].type == "document"


def test_red_flag_event_valid():
    event = RedFlagEvent(
        event_id="rfe_12345",
        session_id="sess_001",
        trigger_phrase="chest pain with breathlessness",
        matched_rule="RF-CARD-001: chest pain with breathlessness",
        severity="red",
        category="cardiac",
        timestamp=datetime.now(UTC)
    )
    assert event.severity == "red"
    assert event.category == "cardiac"
    assert event.dismissed_by is None


def test_dev2_stubs():
    # Verify ExtractedEntity stub parses without error
    entity = ExtractedEntity(
        entity_id="ent_01",
        type="medication",
        value="Tab Metformin 500mg",
        confidence=0.98,
        bounding_box=[0.1, 0.2, 0.4, 0.05]
    )
    assert entity.entity_id == "ent_01"
    assert entity.bounding_box == [0.1, 0.2, 0.4, 0.05]

    # Verify FHIRBundlePayload stub parses without error
    fhir = FHIRBundlePayload(
        patient_abha_id="91-1234-5678-9012@abdm",
        encounter_id="enc_001",
        consent_ref="consent_artefact_999",
        summary_fields=[]
    )
    assert fhir.patient_abha_id == "91-1234-5678-9012@abdm"
