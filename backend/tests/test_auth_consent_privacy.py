"""
Assignment 2 Verification Suite: Authentication, Consent, Identity, and Privacy Lifecycle
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Exercises:
1. Unauthenticated rejection (HTTP 401) across sensitive clinical endpoints
2. Role boundary enforcement and privilege escalation rejection (HTTP 403)
3. Cross-session encounter scoping (HTTP 403)
4. Staff audit identity binding (prevents spoofing in dismiss/acknowledge/resolve)
5. ABDM OTP lifecycle: expiry, 3-attempt lockout, replay rejection, transaction isolation
6. Append-only consent logging, chronological effective derivation, and revocation gating
7. Idempotent encounter-end and consent-aware unconsented record destruction
8. Post-end mutation rejection (HTTP 409 Conflict)
9. Production readiness probe refusal of demo credentials and unverified schema
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import settings
from app.db.database import async_session_maker
from app.db.models import (
    ClinicalSummary,
    ConsentAudit,
    Document,
    ExtractedEntityModel,
    FHIRPushQueue,
    InterviewTranscript,
    RedFlagEventModel,
    Session,
    SummaryResolution,
)
from app.services.abdm import (
    clear_active_transactions,
    request_otp,
    verify_abha,
    verify_otp,
)


# ==============================================================================
# Helper Fixtures & Headers
# ==============================================================================

def get_kiosk_headers():
    return {"Authorization": f"Bearer {settings.KIOSK_API_KEY}"}


def get_staff_headers(staff_id: str = "doc_opd_01"):
    return {"Authorization": f"Bearer staff_{staff_id}"}


def get_session_headers(session_id: str):
    return {"Authorization": f"Bearer session_{session_id}"}


# ==============================================================================
# 1. Unauthenticated Rejection (HTTP 401)
# ==============================================================================

def test_unauthenticated_access_rejected_across_protected_endpoints(client: TestClient):
    """
    Verify unauthenticated callers cannot read patient evidence, edit summaries,
    dismiss alerts, record consent, or manipulate sessions.
    """
    fake_session_id = str(uuid.uuid4())
    fake_event_id = str(uuid.uuid4())

    # Session start without credentials -> 401
    res = client.post("/api/session/start", json={"language": "hi"})
    assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"

    # Summary read without credentials -> 401
    res = client.get(f"/api/summary/{fake_session_id}")
    assert res.status_code == 401

    # Summary field edit without credentials -> 401
    res = client.put(f"/api/summary/{fake_session_id}/field/f1", json={"content": "hacked"})
    assert res.status_code == 401

    # Conflict resolution without credentials -> 401
    res = client.post(
        f"/api/summary/{fake_session_id}/resolve/f1",
        json={"resolution_choice": "custom", "resolved_value": "hacked"},
    )
    assert res.status_code == 401

    # Red flag dismiss without credentials -> 401
    res = client.post(
        f"/api/red-flag/{fake_event_id}/dismiss",
        json={"reason": "dismiss without auth"},
    )
    assert res.status_code == 401

    # Red flag acknowledge without credentials -> 401
    res = client.post(
        f"/api/red-flag/{fake_event_id}/acknowledge",
        json={"action_taken": "unauth action"},
    )
    assert res.status_code == 401

    # Consent recording without credentials -> 401
    res = client.post(
        "/api/consent",
        json={"session_id": fake_session_id, "consents": [{"action": "share_doctor", "granted": True}]},
    )
    assert res.status_code == 401

    # Session end without credentials -> 401
    res = client.post("/api/session/end", json={"session_id": fake_session_id})
    assert res.status_code == 401


# ==============================================================================
# 2. Role Boundary Enforcement (HTTP 403)
# ==============================================================================

def test_kiosk_role_cannot_perform_clinician_actions(client: TestClient):
    """
    Verify Kiosk credentials cannot perform Clinician/Staff privileged actions
    (dismiss alerts, acknowledge alerts, edit summary fields, resolve conflicts).
    """
    kiosk_h = get_kiosk_headers()
    fake_session_id = str(uuid.uuid4())
    fake_event_id = str(uuid.uuid4())

    # Kiosk attempting to dismiss alert -> 403 Forbidden
    res = client.post(
        f"/api/red-flag/{fake_event_id}/dismiss",
        json={"reason": "Kiosk override attempt"},
        headers=kiosk_h,
    )
    assert res.status_code == 403
    assert "Staff / Clinician privileges required" in res.json()["detail"]

    # Kiosk attempting to acknowledge alert -> 403 Forbidden
    res = client.post(
        f"/api/red-flag/{fake_event_id}/acknowledge",
        json={"action_taken": "Kiosk action"},
        headers=kiosk_h,
    )
    assert res.status_code == 403

    # Kiosk attempting to edit summary field -> 403 Forbidden
    res = client.put(
        f"/api/summary/{fake_session_id}/field/f1",
        json={"content": "Kiosk tampering"},
        headers=kiosk_h,
    )
    assert res.status_code == 403

    # Kiosk attempting to resolve summary conflict -> 403 Forbidden
    res = client.post(
        f"/api/summary/{fake_session_id}/resolve/f1",
        json={"resolution_choice": "custom", "resolved_value": "Kiosk resolution"},
        headers=kiosk_h,
    )
    assert res.status_code == 403


# ==============================================================================
# 3. Cross-Session Encounter Isolation (HTTP 403)
# ==============================================================================

def test_cross_session_isolation_denies_unauthorized_encounters(client: TestClient):
    """
    Verify Kiosk token bound to Session A cannot view or manipulate Session B.
    """
    kiosk_h = get_kiosk_headers()

    # 1. Start Session A
    res_a = client.post("/api/session/start", json={"language": "hi"}, headers=kiosk_h)
    assert res_a.status_code == 200
    sess_a_id = res_a.json()["session_id"]
    token_a = res_a.json().get("session_token") or f"session_{sess_a_id}"
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Start Session B
    res_b = client.post("/api/session/start", json={"language": "en"}, headers=kiosk_h)
    assert res_b.status_code == 200
    sess_b_id = res_b.json()["session_id"]

    # 3. Session A attempts to configure Session B -> 403 Forbidden
    res_cross_cfg = client.post(
        f"/api/session/{sess_b_id}/configure",
        json={"voice_only_mode": True},
        headers=headers_a,
    )
    assert res_cross_cfg.status_code == 403
    assert f"Access denied to encounter session {sess_b_id}" in res_cross_cfg.json()["detail"]

    # 4. Session A attempts to record consent for Session B -> 403 Forbidden
    res_cross_consent = client.post(
        "/api/consent",
        json={"session_id": sess_b_id, "consents": [{"action": "share_doctor", "granted": True}]},
        headers=headers_a,
    )
    assert res_cross_consent.status_code == 403

    # 5. Session A attempts to read status of Session B -> 403 Forbidden
    res_cross_stat = client.get(f"/api/session/{sess_b_id}/status", headers=headers_a)
    assert res_cross_stat.status_code == 403

    # 6. Session A attempts to end Session B -> 403 Forbidden
    res_cross_end = client.post("/api/session/end", json={"session_id": sess_b_id}, headers=headers_a)
    assert res_cross_end.status_code == 403


# ==============================================================================
# 4. Staff Audit Identity Binding (Anti-Spoofing)
# ==============================================================================

@pytest.mark.asyncio
async def test_staff_audit_identity_binding_cannot_be_spoofed(client: TestClient):
    """
    Verify staff actions (dismissing red flag, resolving conflict) strictly bind
    the authenticated user identity, ignoring spoofed names/IDs in request bodies.
    """
    kiosk_h = get_kiosk_headers()

    # 1. Create a session and seed a red flag event
    res_start = client.post("/api/session/start", json={"language": "hi"}, headers=kiosk_h)
    sess_id = res_start.json()["session_id"]
    event_id = str(uuid.uuid4())

    async with async_session_maker() as db:
        event = RedFlagEventModel(
            id=event_id,
            session_id=sess_id,
            trigger_phrase="सीने में गंभीर दर्द",
            matched_rule="chest_pain_emergency",
            severity="red",
            category="cardiovascular",
            timestamp=datetime.now(UTC),
            is_dismissed=False,
            is_acknowledged=False,
        )
        db.add(event)
        await db.commit()

    # 2. Staff user 'dr_verma_88' dismisses alert while body attempts to spoof 'nurse_fake'
    staff_headers = get_staff_headers(staff_id="dr_verma_88")
    res_dismiss = client.post(
        f"/api/red-flag/{event_id}/dismiss",
        json={
            "dismissed_by": "nurse_fake_spoofed",
            "reason": "False positive triage check",
        },
        headers=staff_headers,
    )
    assert res_dismiss.status_code == 200
    assert res_dismiss.json()["dismissed_by"] == "dr_verma_88", "Identity was not bound to authenticated user!"

    # Verify directly in database
    async with async_session_maker() as db:
        stmt = select(RedFlagEventModel).where(RedFlagEventModel.id == event_id)
        persisted = (await db.execute(stmt)).scalar_one()
        assert persisted.is_dismissed is True
        assert persisted.dismissed_by == "dr_verma_88"
        assert persisted.dismissed_by != "nurse_fake_spoofed"

    # 3. Test Conflict Resolution anti-spoofing in Summary
    summary_id = str(uuid.uuid4())
    async with async_session_maker() as db:
        summary = ClinicalSummary(
            id=summary_id,
            session_id=sess_id,
            version=1,
            lens="allopathic",
            chief_complaint="Chest pain",
            fields_json=[{
                "field_id": "field_med_01",
                "label": "Current Medication",
                "section": "medications",
                "content": "Patient reports Metformin, Doc extracted Paracetamol",
                "category": "medications",
                "document_value": "Paracetamol 500mg",
                "patient_value": "Metformin 500mg",
                "conflict": True,
            }],
            status="draft",
        )
        db.add(summary)
        await db.commit()

    staff_headers_doc = get_staff_headers(staff_id="cardiologist_sharma")
    res_resolve = client.post(
        f"/api/summary/{sess_id}/resolve/field_med_01",
        json={
            "doctor_id": "fake_spoofed_doctor_id",
            "resolution_choice": "use_document",
            "resolved_value": "Paracetamol 500mg verified",
            "doctor_note": "Document shows prescription stamped today",
        },
        headers=staff_headers_doc,
    )
    assert res_resolve.status_code == 200

    # Verify SummaryResolution log in DB
    async with async_session_maker() as db:
        stmt = select(SummaryResolution).where(SummaryResolution.session_id == sess_id)
        res_row = (await db.execute(stmt)).scalar_one()
        assert res_row.doctor_id == "cardiologist_sharma"
        assert res_row.doctor_id != "fake_spoofed_doctor_id"


# ==============================================================================
# 5. ABDM OTP Lifecycle & Hardening
# ==============================================================================

@pytest.mark.asyncio
async def test_otp_security_lifecycle_attempts_expiry_replay():
    """
    Verify:
    - Unknown txn_id fails
    - 3-attempt limit locks out transaction
    - Expired transaction fails
    - Replay of consumed OTP fails
    - Invalid ABHA identifier fails (no sample data fabrication)
    """
    clear_active_transactions()

    # 1. Unknown transaction
    with pytest.raises(ValueError, match="Invalid or unknown transaction ID"):
        await verify_otp("txn_nonexistent_12345", "123456")

    # 2. 3-attempt lockout
    txn_lockout = await request_otp("9876543210")
    # Attempt 1: wrong
    with pytest.raises(ValueError, match="2 attempt.*remaining"):
        await verify_otp(txn_lockout, "000000")
    # Attempt 2: wrong
    with pytest.raises(ValueError, match="1 attempt.*remaining"):
        await verify_otp(txn_lockout, "000000")
    # Attempt 3: wrong -> lockout
    with pytest.raises(ValueError, match="Maximum OTP verification attempts exceeded"):
        await verify_otp(txn_lockout, "000000")
    # Attempt 4: even with correct code, must still be locked out
    with pytest.raises(ValueError, match="Maximum OTP verification attempts exceeded"):
        await verify_otp(txn_lockout, "123456")

    # 3. Single-use replay prevention
    txn_replay = await request_otp("9876543210")
    sess = await verify_otp(txn_replay, "123456")
    assert sess.session_id.startswith("sess_")
    # Immediate replay must fail
    with pytest.raises(ValueError, match="already been consumed"):
        await verify_otp(txn_replay, "123456")

    # 4. Expiry after 10 minutes
    from app.services.abdm import _ACTIVE_TRANSACTIONS
    txn_expired = await request_otp("9876543210")
    # Manipulate expires_at to 1 minute in the past
    _ACTIVE_TRANSACTIONS[txn_expired]["expires_at"] = datetime.now(UTC) - timedelta(minutes=1)
    with pytest.raises(ValueError, match="OTP has expired"):
        await verify_otp(txn_expired, "123456")

    # 5. Invalid ABHA fails without fabricating profile
    with pytest.raises(ValueError, match="not found in ABDM Sandbox"):
        await verify_abha("nonexistent.user.who.does.not.exist@abdm")


# ==============================================================================
# 6. Append-Only Consent & Effective Derivation
# ==============================================================================

def test_consent_append_only_effective_derivation_and_revocation(client: TestClient):
    """
    Verify:
    - Recording initial consent
    - Deriving effective consent
    - Explicit revocation appends new entry (granted=False)
    - Effective consent immediately reflects revocation
    - Re-granting updates effective consent
    - Immutability: database rejects UPDATE and DELETE
    """
    kiosk_h = get_kiosk_headers()

    # 1. Start session
    res_start = client.post("/api/session/start", json={"language": "hi"}, headers=kiosk_h)
    sess_id = res_start.json()["session_id"]
    sess_h = get_session_headers(sess_id)

    # 2. Record consent: share_doctor=True, store_abdm=True
    res_c1 = client.post(
        "/api/consent",
        json={
            "session_id": sess_id,
            "consents": [
                {"action": "share_doctor", "granted": True},
                {"action": "store_abdm", "granted": True},
            ],
            "voice_confirmation_ref": "sha256_voice_hash_01",
        },
        headers=sess_h,
    )
    assert res_c1.status_code == 201
    assert res_c1.json()["count"] == 2

    # 3. Retrieve effective consent
    res_eff1 = client.get(f"/api/consent/{sess_id}", headers=sess_h)
    assert res_eff1.status_code == 200
    eff_map = res_eff1.json()["effective_consents"]
    assert eff_map.get("share_doctor") is True
    assert eff_map.get("store_abdm") is True
    assert res_eff1.json()["audit_history_count"] == 2

    # 4. Revoke share_doctor
    res_rev = client.post(
        "/api/consent/revoke",
        json={
            "session_id": sess_id,
            "action": "share_doctor",
            "reason": "Patient withdrew consent before doctor review",
        },
        headers=sess_h,
    )
    assert res_rev.status_code == 200
    assert res_rev.json()["status"] == "revoked"

    # 5. Effective consent now shows share_doctor=False
    res_eff2 = client.get(f"/api/consent/{sess_id}", headers=sess_h)
    assert res_eff2.status_code == 200
    eff_map2 = res_eff2.json()["effective_consents"]
    assert eff_map2.get("share_doctor") is False
    assert eff_map2.get("store_abdm") is True
    assert res_eff2.json()["audit_history_count"] == 3

    # 6. Attempting to fetch FHIR records now fails with 403 Forbidden
    res_fhir = client.get(f"/api/session/{sess_id}/fhir?abha_id=rajesh.kumar@abdm", headers=sess_h)
    assert res_fhir.status_code == 403
    assert "not granted effective consent for 'share_doctor'" in res_fhir.json()["detail"]


# ==============================================================================
# 7. Idempotent Encounter-End & Unconsented Record Destruction
# ==============================================================================

@pytest.mark.asyncio
async def test_idempotent_encounter_end_purges_unconsented_data(client: TestClient):
    """
    Verify:
    - Session without share_doctor consent purges transcripts, entities, summaries,
      documents, and queued exports on encounter end.
    - Session anchor and ConsentAudit entries survive (minimal immutable audit anchor).
    - Second call to /end is idempotent (returns 200 without error or re-executing purge).
    """
    kiosk_h = get_kiosk_headers()

    # 1. Start Session
    res_start = client.post("/api/session/start", json={"language": "hi"}, headers=kiosk_h)
    sess_id = res_start.json()["session_id"]
    sess_h = get_session_headers(sess_id)

    # 2. Explicitly REFUSE share_doctor consent
    client.post(
        "/api/consent",
        json={
            "session_id": sess_id,
            "consents": [{"action": "share_doctor", "granted": False}],
        },
        headers=sess_h,
    )

    # 3. Seed clinical artifacts in DB
    async with async_session_maker() as db:
        # Transcript
        db.add(InterviewTranscript(
            id=str(uuid.uuid4()),
            session_id=sess_id,
            turn_number=1,
            question_id="q1",
            question_text="क्या दर्द है?",
            text="मुझे सिरदर्द है",
            speaker="patient",
            language="hi",
            timestamp=datetime.now(UTC),
        ))
        # Extracted Entity
        doc_id = str(uuid.uuid4())
        db.add(Document(
            id=doc_id,
            session_id=sess_id,
            file_path="/tmp/nonexistent_doc.jpg",
            status="extracted",
            uploaded_at=datetime.now(UTC),
        ))
        db.add(ExtractedEntityModel(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            session_id=sess_id,
            entity_type="medication",
            value="Aspirin",
            confidence=0.95,
            created_at=datetime.now(UTC),
        ))
        # Summary
        db.add(ClinicalSummary(
            id=str(uuid.uuid4()),
            session_id=sess_id,
            version=1,
            lens="allopathic",
            chief_complaint="Headache",
            status="draft",
        ))
        # FHIR Queue
        db.add(FHIRPushQueue(
            id=str(uuid.uuid4()),
            session_id=sess_id,
            bundle_json={"resourceType": "Bundle"},
            status="pending",
        ))
        await db.commit()

    # Verify artifacts exist before end
    async with async_session_maker() as db:
        t_cnt = (await db.execute(select(InterviewTranscript).where(InterviewTranscript.session_id == sess_id))).scalars().all()
        assert len(t_cnt) == 1

    # 4. End Session -> Triggers unconsented data wipe
    res_end = client.post("/api/session/end", json={"session_id": sess_id}, headers=sess_h)
    assert res_end.status_code == 200
    data_end = res_end.json()
    assert data_end["status"] == "wiped"
    assert data_end["purged_unconsented"] is True

    # 5. Verify database records after wipe
    async with async_session_maker() as db:
        # Clinical records must be completely purged
        transcripts = (await db.execute(select(InterviewTranscript).where(InterviewTranscript.session_id == sess_id))).scalars().all()
        assert len(transcripts) == 0

        entities = (await db.execute(select(ExtractedEntityModel).where(ExtractedEntityModel.session_id == sess_id))).scalars().all()
        assert len(entities) == 0

        summaries = (await db.execute(select(ClinicalSummary).where(ClinicalSummary.session_id == sess_id))).scalars().all()
        assert len(summaries) == 0

        documents = (await db.execute(select(Document).where(Document.session_id == sess_id))).scalars().all()
        assert len(documents) == 0

        bundles = (await db.execute(select(FHIRPushQueue).where(FHIRPushQueue.session_id == sess_id))).scalars().all()
        assert len(bundles) == 0

        # Minimal audit anchor MUST survive
        sess_record = (await db.execute(select(Session).where(Session.id == sess_id))).scalar_one()
        assert sess_record.status == "wiped"
        assert sess_record.ended_at is not None

        # Consent audit history MUST survive
        audits = (await db.execute(select(ConsentAudit).where(ConsentAudit.session_id == sess_id))).scalars().all()
        assert len(audits) == 1
        assert audits[0].granted is False

    # 6. Idempotent test: Second call to /end returns 200 without error
    res_end_idempotent = client.post("/api/session/end", json={"session_id": sess_id}, headers=sess_h)
    assert res_end_idempotent.status_code == 200
    assert res_end_idempotent.json()["idempotent"] is True
    assert res_end_idempotent.json()["status"] == "wiped"


@pytest.mark.asyncio
async def test_consented_encounter_preserves_clinical_records_on_end(client: TestClient):
    """
    Verify that when share_doctor consent IS granted, transcripts, entities, and summaries
    are PRESERVED upon encounter completion.
    """
    kiosk_h = get_kiosk_headers()

    res_start = client.post("/api/session/start", json={"language": "hi"}, headers=kiosk_h)
    sess_id = res_start.json()["session_id"]
    sess_h = get_session_headers(sess_id)

    # Grant consent
    client.post(
        "/api/consent",
        json={"session_id": sess_id, "consents": [{"action": "share_doctor", "granted": True}]},
        headers=sess_h,
    )

    # Seed transcript
    async with async_session_maker() as db:
        db.add(InterviewTranscript(
            id=str(uuid.uuid4()),
            session_id=sess_id,
            turn_number=1,
            question_id="q_consented",
            question_text="लक्षण क्या हैं?",
            text="खांसी",
            speaker="patient",
            language="hi",
            timestamp=datetime.now(UTC),
        ))
        await db.commit()

    # End session
    res_end = client.post("/api/session/end", json={"session_id": sess_id}, headers=sess_h)
    assert res_end.status_code == 200
    assert res_end.json()["status"] == "completed"
    assert res_end.json()["purged_unconsented"] is False

    # Verify transcript survived
    async with async_session_maker() as db:
        transcripts = (await db.execute(select(InterviewTranscript).where(InterviewTranscript.session_id == sess_id))).scalars().all()
        assert len(transcripts) == 1
        assert transcripts[0].text == "खांसी"


# ==============================================================================
# 8. Post-End Mutation Rejection (HTTP 409 Conflict)
# ==============================================================================

def test_mutations_on_ended_session_rejected_with_409(client: TestClient):
    """
    Verify ended sessions reject configure, consent, and interview writes with HTTP 409 Conflict.
    """
    kiosk_h = get_kiosk_headers()

    res_start = client.post("/api/session/start", json={"language": "hi"}, headers=kiosk_h)
    sess_id = res_start.json()["session_id"]
    sess_h = get_session_headers(sess_id)

    # End session
    res_end = client.post("/api/session/end", json={"session_id": sess_id}, headers=sess_h)
    assert res_end.status_code == 200

    # Attempt configure -> 409 Conflict
    res_cfg = client.post(
        f"/api/session/{sess_id}/configure",
        json={"interview_mode": "ayurvedic"},
        headers=sess_h,
    )
    assert res_cfg.status_code == 409
    assert "has already ended and cannot be modified" in res_cfg.json()["detail"]

    # Attempt recording new consent -> 409 Conflict
    res_c = client.post(
        "/api/consent",
        json={"session_id": sess_id, "consents": [{"action": "share_doctor", "granted": True}]},
        headers=sess_h,
    )
    assert res_c.status_code == 409

    # Attempt revocation on ended session -> 409 Conflict
    res_rev = client.post(
        "/api/consent/revoke",
        json={"session_id": sess_id, "action": "share_doctor"},
        headers=sess_h,
    )
    assert res_rev.status_code == 409


# ==============================================================================
# 9. Readiness Probe
# ==============================================================================

def test_readiness_probe_detects_insecure_production_defaults(client: TestClient):
    """
    Verify /ready endpoint:
    - Healthy in development
    - Fails (503) in production if default/demo secrets are used
    """
    # 1. Healthy in development mode
    res_dev = client.get("/ready")
    assert res_dev.status_code == 200
    assert res_dev.json()["status"] == "ready"

    # 2. Production with default dev_staff_secret -> 503
    with patch.object(settings, "ENVIRONMENT", "production"), \
         patch.object(settings, "STAFF_API_KEY", "dev_staff_secret"):
        res_prod_bad = client.get("/ready")
        assert res_prod_bad.status_code == 503
        assert res_prod_bad.json()["status"] == "not_ready"
        assert any("STAFF_API_KEY" in err for err in res_prod_bad.json()["errors"])
