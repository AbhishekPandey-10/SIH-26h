"""
Assignment 6 — Consent-Bound FHIR Export and Durable Delivery Acceptance Test Suite
PS ID26047 — Final Phase Hardening

20 Rigorous Acceptance Tests:
 1. No consent -> export rejected (403)
 2. Consent refused -> export rejected (403)
 3. Consent revoked after initial grant -> export rejected (403)
 4. No affirmation (summary unverified) -> export rejected (422)
 5. Wrong role (kiosk / session token trying to export) -> rejected (403)
 6. Unlinked identity (session without patient) -> rejected (422)
 7. Patient without ABHA -> rejected (422)
 8. Stale summary version -> retry blocked (blocked_stale_version)
 9. Client-supplied bundle ignored; server builds from reviewed DB records
10. Preview uses exact persisted clinician-corrected version
11. Export uses exact persisted version; preview and snapshot consistent
12. Conflicts/alerts NOT emitted as active medications
13. XHTML narrative properly escaped
14. Repeated failures increase attempts on ONE job (not queue length)
15. Concurrent claims cannot duplicate delivery (lease locking)
16. Repeated client submissions use idempotency (same job returned)
17. Network timeout after send marks unknown delivery (ambiguous delivery)
18. Revocation before retry blocks queued export (blocked_consent_revoked)
19. Privacy cleanup on session end purges undelivered jobs when unconsented
20. Injected transport used; default is UnavailableTransport
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.config import settings
from app.db.database import async_session_factory
from app.db.models import (
    ClinicalSummary,
    ConsentAudit,
    FHIRPushQueue,
    Patient,
    Session,
)
from app.services.abdm_push import (
    ABDMTransportResult,
    TestTransport,
    UnavailableTransport,
    export_queue,
)
from app.services.fhir_builder import fhir_builder
from app.shared.schemas import SummaryField, SummarySource


# ==============================================================================
# Helper Functions & Test Fixtures
# ==============================================================================

def get_kiosk_headers():
    return {"Authorization": f"Bearer {settings.KIOSK_API_KEY}"}


def get_staff_headers(staff_id: str = "doc_opd_01"):
    return {"Authorization": f"Bearer staff_{staff_id}"}


def get_session_headers(session_id: str):
    return {"Authorization": f"Bearer session_{session_id}"}


async def seed_test_encounter(
    *,
    session_id: str,
    patient_id: str | None = None,
    patient_abha: str | None = "AUTO",
    patient_name: str = "Rajesh Kumar",
    store_abdm_consent: bool | None = True,
    share_doctor_consent: bool | None = True,
    summary_status: str = "doctor_verified",
    summary_version: int = 1,
    custom_fields: list[dict[str, Any]] | None = None,
) -> tuple[Session, Patient | None, ClinicalSummary | None]:
    """Helper to seed an encounter with patient, consents, and clinical summary."""
    resolved_abha = f"patient_{uuid.uuid4().hex[:8]}@sbx" if patient_abha == "AUTO" else patient_abha
    async with async_session_factory() as db:
        # 1. Patient
        patient = None
        if patient_id:
            existing_by_id = await db.get(Patient, patient_id)
            if existing_by_id:
                patient = existing_by_id
            else:
                res = await db.execute(select(Patient).where(Patient.abha_id == resolved_abha))
                existing_by_abha = res.scalars().first()
                if existing_by_abha:
                    patient = existing_by_abha
                    patient_id = patient.id
                else:
                    patient = Patient(
                        id=patient_id,
                        abha_id=resolved_abha,
                        name=patient_name,
                        gender="M",
                        dob="1980-01-01",
                        mobile="9876543210",
                    )
                    db.add(patient)

        # 2. Session
        session = Session(
            id=session_id,
            patient_id=patient_id,
            status="active",
            language="hi",
        )
        db.add(session)
        await db.flush()

        # 3. Consents
        now = datetime.now(UTC)
        if share_doctor_consent is not None:
            db.add(ConsentAudit(
                session_id=session_id,
                action="share_doctor",
                granted=share_doctor_consent,
                timestamp=now - timedelta(seconds=10),
            ))

        if store_abdm_consent is not None:
            db.add(ConsentAudit(
                session_id=session_id,
                action="store_abdm",
                granted=store_abdm_consent,
                timestamp=now - timedelta(seconds=5),
            ))

        # 4. Clinical Summary
        fields = custom_fields or [
            SummaryField(
                field_id="sf_cc_01",
                section="chief_complaint",
                content="Chest pain for 2 days",
                verification="patient_reported",
            ).model_dump(mode="json"),
            SummaryField(
                field_id="sf_med_01",
                section="medications",
                content="Metformin 500mg BD",
                verification="doctor_confirmed",
            ).model_dump(mode="json"),
        ]

        summary = ClinicalSummary(
            id=f"sum_{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            version=summary_version,
            lens="allopathic",
            chief_complaint="Chest pain",
            fields_json=fields,
            status=summary_status,
        )
        db.add(summary)

        await db.commit()
        return session, patient, summary


@pytest.fixture(autouse=True)
def setup_test_transport():
    """Ensure each test runs with an isolated TestTransport by default."""
    test_transport = TestTransport()
    export_queue.transport = test_transport
    yield test_transport
    test_transport.reset()
    export_queue.transport = UnavailableTransport()


# ==============================================================================
# 1. No Consent -> Export Rejected (HTTP 403)
# ==============================================================================

@pytest.mark.asyncio
async def test_export_rejected_without_consent(client: TestClient):
    """
    Export MUST be rejected with HTTP 403 if the patient never granted 'store_abdm' consent.
    """
    sess_id = f"sess_no_consent_{uuid.uuid4().hex[:6]}"
    pat_id = f"pat_{uuid.uuid4().hex[:6]}"

    await seed_test_encounter(
        session_id=sess_id,
        patient_id=pat_id,
        store_abdm_consent=None,  # Never granted
    )

    staff_h = get_staff_headers()
    res = client.post("/api/fhir/export", json={"session_id": sess_id}, headers=staff_h)

    assert res.status_code == 403
    assert "store_abdm" in res.json()["detail"]


# ==============================================================================
# 2. Consent Refused -> Export Rejected (HTTP 403)
# ==============================================================================

@pytest.mark.asyncio
async def test_export_rejected_when_consent_refused(client: TestClient):
    """
    Export MUST be rejected with HTTP 403 if the patient explicitly refused 'store_abdm' consent.
    """
    sess_id = f"sess_refused_{uuid.uuid4().hex[:6]}"
    pat_id = f"pat_{uuid.uuid4().hex[:6]}"

    await seed_test_encounter(
        session_id=sess_id,
        patient_id=pat_id,
        store_abdm_consent=False,  # Refused
    )

    staff_h = get_staff_headers()
    res = client.post("/api/fhir/export", json={"session_id": sess_id}, headers=staff_h)

    assert res.status_code == 403
    assert "store_abdm" in res.json()["detail"]


# ==============================================================================
# 3. Consent Revoked After Grant -> Export Rejected (HTTP 403)
# ==============================================================================

@pytest.mark.asyncio
async def test_export_rejected_when_consent_revoked_after_grant(client: TestClient):
    """
    Export MUST be rejected if patient initially granted consent but later revoked it.
    Append-only audit trail verifies latest state is granted=False.
    """
    sess_id = f"sess_revoked_{uuid.uuid4().hex[:6]}"
    pat_id = f"pat_{uuid.uuid4().hex[:6]}"

    await seed_test_encounter(
        session_id=sess_id,
        patient_id=pat_id,
        store_abdm_consent=True,  # Initially granted
    )

    # Patient revokes store_abdm consent
    async with async_session_factory() as db:
        db.add(ConsentAudit(
            session_id=sess_id,
            action="store_abdm",
            granted=False,  # Revocation entry
            timestamp=datetime.now(UTC),
        ))
        await db.commit()

    staff_h = get_staff_headers()
    res = client.post("/api/fhir/export", json={"session_id": sess_id}, headers=staff_h)

    assert res.status_code == 403
    assert "store_abdm" in res.json()["detail"]


# ==============================================================================
# 4. No Clinician Affirmation -> Export Rejected (HTTP 422)
# ==============================================================================

@pytest.mark.asyncio
async def test_export_rejected_without_clinician_affirmation(client: TestClient):
    """
    Export MUST require doctor_verified summary status before export.
    Draft or preliminary summaries must return HTTP 422.
    """
    sess_id = f"sess_unverified_{uuid.uuid4().hex[:6]}"
    pat_id = f"pat_{uuid.uuid4().hex[:6]}"

    await seed_test_encounter(
        session_id=sess_id,
        patient_id=pat_id,
        summary_status="draft",  # Not doctor_verified!
    )

    staff_h = get_staff_headers()
    res = client.post("/api/fhir/export", json={"session_id": sess_id}, headers=staff_h)

    assert res.status_code == 422
    assert "verified" in res.json()["detail"].lower()


# ==============================================================================
# 5. Wrong Role -> Rejected (HTTP 403)
# ==============================================================================

@pytest.mark.asyncio
async def test_export_rejected_for_wrong_role_kiosk(client: TestClient):
    """
    Kiosk tokens and session tokens must NOT be allowed to export or preview FHIR bundles.
    Only authenticated clinical staff (Role.STAFF) may export or preview.
    """
    sess_id = f"sess_role_{uuid.uuid4().hex[:6]}"
    pat_id = f"pat_{uuid.uuid4().hex[:6]}"

    await seed_test_encounter(session_id=sess_id, patient_id=pat_id)

    kiosk_h = get_kiosk_headers()
    session_h = get_session_headers(sess_id)

    # Kiosk cannot export -> 403
    res_kiosk_export = client.post("/api/fhir/export", json={"session_id": sess_id}, headers=kiosk_h)
    assert res_kiosk_export.status_code == 403

    # Kiosk cannot preview -> 403
    res_kiosk_preview = client.get(f"/api/fhir/preview/{sess_id}", headers=kiosk_h)
    assert res_kiosk_preview.status_code == 403

    # Session token cannot export -> 403
    res_sess_export = client.post("/api/fhir/export", json={"session_id": sess_id}, headers=session_h)
    assert res_sess_export.status_code == 403


# ==============================================================================
# 6. Unlinked Identity (No Patient) -> Rejected (HTTP 422)
# ==============================================================================

@pytest.mark.asyncio
async def test_export_rejected_for_unlinked_session_no_patient(client: TestClient):
    """
    Session without a linked patient record cannot be exported to ABDM.
    """
    sess_id = f"sess_unlinked_{uuid.uuid4().hex[:6]}"

    await seed_test_encounter(
        session_id=sess_id,
        patient_id=None,  # No patient linked
    )

    staff_h = get_staff_headers()
    res = client.post("/api/fhir/export", json={"session_id": sess_id}, headers=staff_h)

    assert res.status_code == 422
    assert "no linked patient" in res.json()["detail"].lower()


# ==============================================================================
# 7. Patient Without ABHA -> Rejected (HTTP 422)
# ==============================================================================

@pytest.mark.asyncio
async def test_export_rejected_for_patient_without_abha(client: TestClient):
    """
    Patient without a verified ABHA address/number cannot be exported to ABDM.
    """
    sess_id = f"sess_no_abha_{uuid.uuid4().hex[:6]}"
    pat_id = f"pat_no_abha_{uuid.uuid4().hex[:6]}"

    await seed_test_encounter(
        session_id=sess_id,
        patient_id=pat_id,
        patient_abha="",  # Empty ABHA
    )

    staff_h = get_staff_headers()
    res = client.post("/api/fhir/export", json={"session_id": sess_id}, headers=staff_h)

    assert res.status_code == 422
    assert "abha" in res.json()["detail"].lower()


# ==============================================================================
# 8. Stale Summary Version -> Blocked in Retry Queue
# ==============================================================================

@pytest.mark.asyncio
async def test_export_stale_summary_version_retry_blocked(
    client: TestClient, setup_test_transport: TestTransport
):
    """
    If a job is queued for summary version 1, but clinician subsequently edits
    the summary to version 2, retry queue must block the old export as stale.
    """
    sess_id = f"sess_stale_{uuid.uuid4().hex[:6]}"
    pat_id = f"pat_{uuid.uuid4().hex[:6]}"

    await seed_test_encounter(
        session_id=sess_id,
        patient_id=pat_id,
        summary_version=1,
    )

    # Queue an initial export job manually for version 1 with status pending
    async with async_session_factory() as db:
        job = FHIRPushQueue(
            id=f"job_stale_{uuid.uuid4().hex[:6]}",
            session_id=sess_id,
            idempotency_key=f"{sess_id}:1",
            patient_abha_id="rajesh.kumar@sbx",
            summary_version=1,
            affirmed_by_doctor_id="doc_opd_01",
            bundle_json={"resourceType": "Bundle"},
            status="pending",
            retry_count=0,
            attempt_history=[],
            consent_verified_at=datetime.now(UTC),
        )
        db.add(job)

        # Update clinical summary to version 2 in DB
        stmt = select(ClinicalSummary).where(ClinicalSummary.session_id == sess_id)
        res = await db.execute(stmt)
        summary = res.scalar_one()
        summary.version = 2
        await db.commit()

    # Trigger retry queue
    staff_h = get_staff_headers()
    retry_res = client.post("/api/fhir/retry-queue", headers=staff_h)
    assert retry_res.status_code == 200

    # Verify job status changed to blocked_stale_version
    async with async_session_factory() as db:
        stmt = select(FHIRPushQueue).where(FHIRPushQueue.idempotency_key == f"{sess_id}:1")
        res = await db.execute(stmt)
        updated_job = res.scalar_one()
        assert updated_job.status == "blocked_stale_version"
        assert "version" in (updated_job.last_error or "").lower()


# ==============================================================================
# 9. Client-Supplied Bundle Ignored; Server Builds From Reviewed Records
# ==============================================================================

@pytest.mark.asyncio
async def test_client_supplied_bundle_ignored(
    client: TestClient, setup_test_transport: TestTransport
):
    """
    Clients cannot inject custom FHIR bundles into the export endpoint.
    The server builds the bundle strictly from database records.
    """
    sess_id = f"sess_inject_{uuid.uuid4().hex[:6]}"
    pat_id = f"pat_{uuid.uuid4().hex[:6]}"

    await seed_test_encounter(
        session_id=sess_id,
        patient_id=pat_id,
        patient_abha=f"actual_{uuid.uuid4().hex[:6]}@abdm",
        custom_fields=[
            SummaryField(
                field_id="sf_legit",
                section="chief_complaint",
                content="Legitimate patient symptom",
                verification="doctor_confirmed",
            ).model_dump(mode="json"),
        ],
    )

    staff_h = get_staff_headers()

    # Attacker attempts to inject fabricated bundle with altered data
    malicious_payload = {
        "session_id": sess_id,
        "bundle": {
            "resourceType": "Bundle",
            "entry": [{"resource": {"resourceType": "Condition", "code": {"text": "HACKED"}}}],
        },
    }

    res = client.post("/api/fhir/export", json=malicious_payload, headers=staff_h)
    assert res.status_code == 200
    assert res.json()["status"] == "delivered"

    # Verify delivered bundle was built by server, not from attacker payload
    assert len(setup_test_transport.calls) == 1
    delivered_bundle = setup_test_transport.calls[0]["bundle"]

    composition = next(
        e["resource"] for e in delivered_bundle["entry"] if e["resource"]["resourceType"] == "Composition"
    )
    # Narrative must contain legitimate content, not "HACKED"
    div_content = composition["section"][0]["text"]["div"]
    assert "Legitimate patient symptom" in div_content
    assert "HACKED" not in str(delivered_bundle)


# ==============================================================================
# 10. Preview Uses Exact Persisted Clinician-Corrected Version
# ==============================================================================

@pytest.mark.asyncio
async def test_preview_uses_exact_persisted_version(client: TestClient):
    """
    Clinician preview returns bundle derived from persisted summary fields.
    Does NOT queue an export or trigger ABDM transport.
    """
    sess_id = f"sess_prev_{uuid.uuid4().hex[:6]}"
    pat_id = f"pat_{uuid.uuid4().hex[:6]}"

    test_abha = f"preview_{uuid.uuid4().hex[:6]}@sbx"
    await seed_test_encounter(
        session_id=sess_id,
        patient_id=pat_id,
        patient_abha=test_abha,
        summary_version=3,
        summary_status="doctor_verified",
        custom_fields=[
            SummaryField(
                field_id="sf_prev_1",
                section="chief_complaint",
                content="Doctor corrected diagnosis: Type 2 Diabetes",
                verification="doctor_confirmed",
            ).model_dump(mode="json"),
        ],
    )

    staff_h = get_staff_headers()
    res = client.get(f"/api/fhir/preview/{sess_id}", headers=staff_h)

    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == sess_id
    assert data["patient_abha_id"] == test_abha
    assert data["summary_version"] == 3
    assert data["is_signed_off"] is True
    assert "Type 2 Diabetes" in str(data["preview_json"])

    # Verify NO jobs were queued in FHIRPushQueue
    async with async_session_factory() as db:
        stmt = select(FHIRPushQueue).where(FHIRPushQueue.session_id == sess_id)
        res_db = await db.execute(stmt)
        assert res_db.scalar_one_or_none() is None


# ==============================================================================
# 11. Export Uses Exact Persisted Version; Preview and Snapshot Consistent
# ==============================================================================

@pytest.mark.asyncio
async def test_preview_and_export_consistency(
    client: TestClient, setup_test_transport: TestTransport
):
    """
    Preview and export must reflect identical resources, summary version,
    and patient references for the same affirmed state.
    """
    sess_id = f"sess_consistent_{uuid.uuid4().hex[:6]}"
    pat_id = f"pat_{uuid.uuid4().hex[:6]}"

    await seed_test_encounter(
        session_id=sess_id,
        patient_id=pat_id,
        patient_abha=f"consistent_{uuid.uuid4().hex[:6]}@sbx",
        summary_version=1,
    )

    staff_h = get_staff_headers()

    # 1. Preview
    prev_res = client.get(f"/api/fhir/preview/{sess_id}", headers=staff_h)
    assert prev_res.status_code == 200
    preview_data = prev_res.json()

    # 2. Export
    export_res = client.post("/api/fhir/export", json={"session_id": sess_id}, headers=staff_h)
    assert export_res.status_code == 200
    export_data = export_res.json()

    assert export_data["summary_version"] == preview_data["summary_version"]
    assert len(setup_test_transport.calls) == 1
    delivered_bundle = setup_test_transport.calls[0]["bundle"]

    assert len(delivered_bundle["entry"]) == preview_data["resource_count"]


# ==============================================================================
# 12. Conflicts and Alerts NOT Emitted as Active Medications
# ==============================================================================

def test_conflicts_and_alerts_not_emitted_as_active_medications():
    """
    Verify fhir_builder clinical mapping:
    - Alert prose (warnings, conflicts, polypharmacy) is NOT emitted as active MedicationStatement.
    - Stopped medications get status="stopped".
    - Active medications get status="active".
    """
    fields = [
        # Normal active med
        SummaryField(
            field_id="m1",
            section="medications",
            content="Metformin 500mg BD with meals",
            verification="doctor_confirmed",
        ),
        # Alert prose (must be excluded from MedicationStatements)
        SummaryField(
            field_id="m2",
            section="medications",
            content="CONFLICT: Patient reported taking 1000mg but prescription shows 500mg",
            verification="conflicting",
        ),
        # Polypharmacy warning prose
        SummaryField(
            field_id="m3",
            section="medications",
            content="Alert: Polypharmacy risk between Aspirin and Clopidogrel",
            verification="system_flagged",
        ),
        # Stopped medication
        SummaryField(
            field_id="m4",
            section="medications",
            content="Atorvastatin 20mg OD (stopped due to myalgia)",
            verification="doctor_confirmed",
        ),
    ]

    bundle = fhir_builder.build_bundle(
        session_id="sess_med_filter",
        summary_fields=fields,
        patient_id="pat_med_01",
        patient_abha_id="pat.med@abdm",
        summary_verified=True,
    )

    med_statements = [
        e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "MedicationStatement"
    ]

    # Only 2 MedicationStatements should be emitted: Metformin (active) and Atorvastatin (stopped)
    # The 2 alert prose items (m2 and m3) must NOT become MedicationStatements!
    assert len(med_statements) == 2

    med_statuses = {m["medicationCodeableConcept"]["text"]: m["status"] for m in med_statements}
    assert med_statuses["Metformin 500mg BD with meals"] == "active"
    assert med_statuses["Atorvastatin 20mg OD (stopped due to myalgia)"] == "stopped"


# ==============================================================================
# 13. XHTML Narrative Properly Escaped
# ==============================================================================

def test_xhtml_narrative_properly_escaped():
    """
    Verify XHTML narrative in Composition escapes HTML/XML special characters.
    Prevents XML parsing errors and XSS vulnerabilities in downstream systems.
    """
    nasty_content = "<script>alert('xss')</script> & \"quotes\" and <tag>"
    fields = [
        SummaryField(
            field_id="f_xss",
            section="chief_complaint",
            content=nasty_content,
            verification="patient_reported",
        ),
    ]

    bundle = fhir_builder.build_bundle(
        session_id="sess_xss",
        summary_fields=fields,
        patient_id="pat_xss_01",
        patient_abha_id="pat.xss@abdm",
        summary_verified=True,
    )

    composition = next(
        e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Composition"
    )
    div_html = composition["section"][0]["text"]["div"]

    # Must NOT contain raw unescaped tags
    assert "<script>" not in div_html
    assert "</script>" not in div_html
    # Must contain properly escaped entities
    assert "&lt;script&gt;" in div_html
    assert "&amp;" in div_html


# ==============================================================================
# 14. Repeated Failures Increase Attempts on ONE Job (Not Queue Multiplication)
# ==============================================================================

@pytest.mark.asyncio
async def test_repeated_failures_increase_attempts_on_one_job(
    client: TestClient, setup_test_transport: TestTransport
):
    """
    When transport encounters failures, retry updates the single existing queue row.
    The number of queue rows NEVER increases.
    """
    sess_id = f"sess_retry_one_{uuid.uuid4().hex[:6]}"
    pat_id = f"pat_{uuid.uuid4().hex[:6]}"

    await seed_test_encounter(session_id=sess_id, patient_id=pat_id)

    # Configure transport to fail with retryable error
    setup_test_transport.configure_result(
        success=False,
        error="Temporary ABDM gateway connection reset",
        is_retryable=True,
    )

    staff_h = get_staff_headers()

    # Initial export attempt (fails)
    res = client.post("/api/fhir/export", json={"session_id": sess_id}, headers=staff_h)
    assert res.status_code == 200
    assert res.json()["status"] == "failed_retryable"

    # Fast-forward backoff by updating the attempt timestamp in DB
    async with async_session_factory() as db:
        stmt = select(FHIRPushQueue).where(FHIRPushQueue.session_id == sess_id)
        res_db = await db.execute(stmt)
        job = res_db.scalar_one()
        assert job.retry_count == 1
        # Set timestamp to 1 hour ago so backoff check passes
        past_time = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        job.attempt_history = [{"timestamp": past_time, "success": False, "error": "test"}]
        await db.commit()

    # Second retry attempt
    retry_res = client.post("/api/fhir/retry-queue", headers=staff_h)
    assert retry_res.status_code == 200

    # Verify exactly ONE job row exists, retry_count incremented to 2
    async with async_session_factory() as db:
        stmt = select(FHIRPushQueue).where(FHIRPushQueue.session_id == sess_id)
        res_db = await db.execute(stmt)
        jobs = res_db.scalars().all()
        assert len(jobs) == 1
        assert jobs[0].retry_count == 2
        assert len(jobs[0].attempt_history) == 2


# ==============================================================================
# 15. Concurrent Claims Cannot Duplicate Delivery (Lease Locking)
# ==============================================================================

@pytest.mark.asyncio
async def test_concurrent_claims_cannot_duplicate_delivery(setup_test_transport: TestTransport):
    """
    Lease locking prevents concurrent workers from dispatching the same job simultaneously.
    """
    sess_id = f"sess_lease_{uuid.uuid4().hex[:6]}"
    pat_id = f"pat_{uuid.uuid4().hex[:6]}"

    await seed_test_encounter(session_id=sess_id, patient_id=pat_id)

    async with async_session_factory() as db:
        # Enqueue job
        enqueue_res = await export_queue.enqueue_export(
            session_id=sess_id,
            patient_abha_id="rajesh.kumar@sbx",
            summary_version=1,
            affirmed_by_doctor_id="doc_opd_01",
            bundle_json={"resourceType": "Bundle"},
            db=db,
        )
        await db.commit()

    async with async_session_factory() as db:
        stmt = select(FHIRPushQueue).where(FHIRPushQueue.id == enqueue_res["job_id"])
        res_db = await db.execute(stmt)
        job = res_db.scalar_one()

        # Simulate Worker 1 claiming the job
        job.status = "claimed"
        job.locked_at = datetime.now(UTC)
        job.locked_by = "worker_1"
        await db.commit()

    # Worker 2 attempts to deliver while Worker 1 holds active lease
    async with async_session_factory() as db:
        stmt = select(FHIRPushQueue).where(FHIRPushQueue.id == enqueue_res["job_id"])
        res_db = await db.execute(stmt)
        job = res_db.scalar_one()

        delivery_result = await export_queue.attempt_delivery(job, db, worker_id="worker_2")
        assert delivery_result["action"] == "skipped"
        assert "not in deliverable state" in delivery_result["reason"]


# ==============================================================================
# 16. Repeated Client Submissions Use Idempotency (Same Job Returned)
# ==============================================================================

@pytest.mark.asyncio
async def test_repeated_client_submissions_use_idempotency(
    client: TestClient, setup_test_transport: TestTransport
):
    """
    Submitting export multiple times for the same encounter version returns
    the existing job without creating duplicates.
    """
    sess_id = f"sess_idemp_{uuid.uuid4().hex[:6]}"
    pat_id = f"pat_{uuid.uuid4().hex[:6]}"

    await seed_test_encounter(session_id=sess_id, patient_id=pat_id, summary_version=1)

    staff_h = get_staff_headers()

    # Submission 1 -> creates new job
    res1 = client.post("/api/fhir/export", json={"session_id": sess_id}, headers=staff_h)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["is_new"] is True
    assert data1["status"] == "delivered"

    # Submission 2 -> returns existing job
    res2 = client.post("/api/fhir/export", json={"session_id": sess_id}, headers=staff_h)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["is_new"] is False
    assert data2["export_id"] == data1["export_id"]
    assert data2["status"] == "delivered"

    # Transport should only have been called ONCE
    assert len(setup_test_transport.calls) == 1

    # Only 1 row in DB
    async with async_session_factory() as db:
        stmt = select(FHIRPushQueue).where(FHIRPushQueue.session_id == sess_id)
        res_db = await db.execute(stmt)
        jobs = res_db.scalars().all()
        assert len(jobs) == 1


# ==============================================================================
# 17. Network Timeout After Send Marks Unknown Delivery
# ==============================================================================

@pytest.mark.asyncio
async def test_network_timeout_after_send_marks_unknown_delivery(
    client: TestClient, setup_test_transport: TestTransport
):
    """
    When transport experiences timeout after the request is sent,
    the job is marked retryable with delivery unknown (ambiguous delivery).
    """
    sess_id = f"sess_timeout_{uuid.uuid4().hex[:6]}"
    pat_id = f"pat_{uuid.uuid4().hex[:6]}"

    await seed_test_encounter(session_id=sess_id, patient_id=pat_id)

    setup_test_transport.configure_result(
        success=False,
        error="HTTP ReadTimeout (timed out after 10.0s)",
        is_retryable=True,
        is_timeout_after_send=True,
    )

    staff_h = get_staff_headers()
    res = client.post("/api/fhir/export", json={"session_id": sess_id}, headers=staff_h)
    assert res.status_code == 200
    assert res.json()["status"] == "failed_retryable"

    async with async_session_factory() as db:
        stmt = select(FHIRPushQueue).where(FHIRPushQueue.session_id == sess_id)
        res_db = await db.execute(stmt)
        job = res_db.scalar_one()
        assert "delivery unknown" in (job.last_error or "").lower()


# ==============================================================================
# 18. Revocation Before Retry Blocks Queued Export
# ==============================================================================

@pytest.mark.asyncio
async def test_revocation_before_retry_blocks_queued_export(
    client: TestClient, setup_test_transport: TestTransport
):
    """
    If consent is revoked while an export is waiting in the retry queue,
    the retry queue must NOT dispatch the bundle and must mark the job blocked.
    """
    sess_id = f"sess_rev_retry_{uuid.uuid4().hex[:6]}"
    pat_id = f"pat_{uuid.uuid4().hex[:6]}"

    await seed_test_encounter(session_id=sess_id, patient_id=pat_id)

    # Initially enqueue a failed job
    setup_test_transport.configure_result(success=False, error="Gateway down", is_retryable=True)

    staff_h = get_staff_headers()
    client.post("/api/fhir/export", json={"session_id": sess_id}, headers=staff_h)

    # Patient subsequently revokes store_abdm consent
    async with async_session_factory() as db:
        db.add(ConsentAudit(
            session_id=sess_id,
            action="store_abdm",
            granted=False,  # Revoked!
            timestamp=datetime.now(UTC),
        ))
        await db.commit()

    # Reset transport call count
    setup_test_transport.reset()

    # Run retry queue
    retry_res = client.post("/api/fhir/retry-queue", headers=staff_h)
    assert retry_res.status_code == 200

    # Transport must NOT have been called!
    assert len(setup_test_transport.calls) == 0

    # Job must be blocked
    async with async_session_factory() as db:
        stmt = select(FHIRPushQueue).where(FHIRPushQueue.session_id == sess_id)
        res_db = await db.execute(stmt)
        job = res_db.scalar_one()
        assert job.status == "blocked_consent_revoked"
        assert "revoked" in (job.last_error or "").lower()


# ==============================================================================
# 19. Privacy Cleanup On Session End Purges Undelivered Jobs
# ==============================================================================

@pytest.mark.asyncio
async def test_privacy_cleanup_purges_queued_exports(
    client: TestClient, setup_test_transport: TestTransport
):
    """
    When session ends without effective consent, the privacy wipe must purge
    all queued FHIR export jobs for that session.
    """
    sess_id = f"sess_wipe_{uuid.uuid4().hex[:6]}"
    pat_id = f"pat_{uuid.uuid4().hex[:6]}"

    await seed_test_encounter(
        session_id=sess_id,
        patient_id=pat_id,
        share_doctor_consent=False,  # Unconsented session end
        store_abdm_consent=False,
    )

    # Seed a queue item
    async with async_session_factory() as db:
        db.add(FHIRPushQueue(
            id=f"job_wipe_{uuid.uuid4().hex[:6]}",
            session_id=sess_id,
            idempotency_key=f"{sess_id}:1",
            patient_abha_id="rajesh.kumar@sbx",
            summary_version=1,
            affirmed_by_doctor_id="doc_opd_01",
            bundle_json={},
            status="pending",
        ))
        await db.commit()

    # End session via session manager (triggers privacy purge)
    from app.services.session_manager import session_manager
    async with async_session_factory() as db:
        outcome = await session_manager.end_session(sess_id, db)
        await db.commit()

    assert outcome["status"] == "wiped"

    # Verify queue row was purged from database
    async with async_session_factory() as db:
        stmt = select(FHIRPushQueue).where(FHIRPushQueue.session_id == sess_id)
        res_db = await db.execute(stmt)
        assert res_db.scalar_one_or_none() is None


# ==============================================================================
# 20. Injected Transport Used; Default is UnavailableTransport
# ==============================================================================

@pytest.mark.asyncio
async def test_default_transport_unavailable_and_injected_transport_works(client: TestClient):
    """
    Verify transport injection:
    - Default transport is UnavailableTransport (no live ABDM requests).
    - Returns 'provider_not_configured' status when provider is not configured.
    """
    # Restore default UnavailableTransport
    export_queue.transport = UnavailableTransport()
    assert export_queue.transport.is_available is False
    assert export_queue.transport.provider_name == "unavailable"

    sess_id = f"sess_unavail_{uuid.uuid4().hex[:6]}"
    pat_id = f"pat_{uuid.uuid4().hex[:6]}"

    await seed_test_encounter(session_id=sess_id, patient_id=pat_id)

    staff_h = get_staff_headers()
    res = client.post("/api/fhir/export", json={"session_id": sess_id}, headers=staff_h)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "provider_not_configured"
    assert "ABDM push provider not configured" in data["error_message"]
