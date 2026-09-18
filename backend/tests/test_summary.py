"""
Unit tests for Clinical Summary service (Dev 1 track)
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""

from app.shared.schemas import SummaryField, SummarySource


def test_summary_field_creation():
    source = SummarySource(
        type="transcript",
        ref_id="turn_01",
        snippet="मुझे 3 दिन से सिरदर्द है"
    )
    field = SummaryField(
        field_id="sf_cc_01",
        section="chief_complaint",
        content="Headache for 3 days",
        sources=[source],
        verification="patient_reported",
        changed_since_last=False
    )
    assert field.field_id == "sf_cc_01"
    assert field.section == "chief_complaint"
    assert field.verification == "patient_reported"
    assert len(field.sources) == 1
