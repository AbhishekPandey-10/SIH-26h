"""
ABDM (Ayushman Bharat Digital Mission) Sandbox Service
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Provides mock/sandbox implementation for:
- ABHA verification (verify_abha)
- Aadhaar / Mobile OTP authentication (request_otp, verify_otp)
- Pre-seeded test ABHA demographics and FHIR R4 bundles
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List

from app.shared.schemas import ABHASession, PatientDemographics

logger = logging.getLogger("medikiosk.abdm")

# Sandbox Test Patients Registry
SANDBOX_PATIENTS: Dict[str, PatientDemographics] = {
    "rajesh.kumar@abdm": PatientDemographics(
        abha_id="rajesh.kumar@abdm",
        abha_number="91-1024-5829-1482",
        name="Rajesh Kumar",
        gender="M",
        dob="1973-05-14",
        mobile="9876543210",
        address="House 42, Pocket B, Mayur Vihar Phase II",
        district="East Delhi",
        state="Delhi",
        is_verified=True,
    ),
    "sunita.devi@abdm": PatientDemographics(
        abha_id="sunita.devi@abdm",
        abha_number="91-2048-9182-3041",
        name="Sunita Devi",
        gender="F",
        dob="1981-08-22",
        mobile="9812345678",
        address="Flat 108, Block C, Rohini Sector 15",
        district="North West Delhi",
        state="Delhi",
        is_verified=True,
    ),
    "amit.sharma@abdm": PatientDemographics(
        abha_id="amit.sharma@abdm",
        abha_number="91-3091-8273-6452",
        name="Amit Sharma",
        gender="M",
        dob="1967-11-03",
        mobile="9988776655",
        address="B-12, Greater Kailash Part 1",
        district="South Delhi",
        state="Delhi",
        is_verified=True,
    ),
    "priya.patel@abdm": PatientDemographics(
        abha_id="priya.patel@abdm",
        abha_number="91-4019-2837-4651",
        name="Priya Patel",
        gender="F",
        dob="1989-02-17",
        mobile="9123456780",
        address="Tower 4, Apt 602, Sector 62",
        district="Gautam Buddha Nagar",
        state="Uttar Pradesh",
        is_verified=True,
    ),
}

# Pre-seeded mock FHIR R4 bundles
MOCK_FHIR_BUNDLES: Dict[str, List[Dict[str, Any]]] = {
    "rajesh.kumar@abdm": [
        {
            "resourceType": "Bundle",
            "id": "bundle-rx-001",
            "type": "document",
            "timestamp": "2025-03-15T09:30:00Z",
            "entry": [
                {
                    "resource": {
                        "resourceType": "MedicationRequest",
                        "id": "medrx-01",
                        "status": "active",
                        "intent": "order",
                        "medicationCodeableConcept": {
                            "text": "Tab. Glycomet GP 1 (Metformin 500mg + Glimepiride 1mg)"
                        },
                        "subject": {"reference": "Patient/rajesh.kumar@abdm"}
                    }
                }
            ]
        },
        {
            "resourceType": "Bundle",
            "id": "bundle-lab-cbc-001",
            "type": "document",
            "timestamp": "2025-03-14T11:00:00Z",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Observation",
                        "id": "obs-hb-01",
                        "status": "final",
                        "code": {"text": "Hemoglobin"},
                        "valueQuantity": {"value": 9.8, "unit": "g/dL"},
                        "interpretation": [{"text": "Low"}]
                    }
                }
            ]
        }
    ],
    "amit.sharma@abdm": [
        {
            "resourceType": "Bundle",
            "id": "bundle-discharge-001",
            "type": "document",
            "timestamp": "2024-11-16T14:00:00Z",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Composition",
                        "id": "comp-discharge-01",
                        "status": "final",
                        "type": {"text": "Discharge Summary"},
                        "title": "Post Primary PTCA to LAD Discharge Summary"
                    }
                }
            ]
        }
    ]
}

# In-memory transaction registry for OTP flow
_ACTIVE_TRANSACTIONS: Dict[str, Dict[str, Any]] = {}


async def verify_abha(abha_id: str) -> PatientDemographics:
    """
    Verify ABHA ID / ABHA Address against ABDM Sandbox.

    Args:
        abha_id: Patient's ABHA address (e.g. 'rajesh.kumar@abdm') or 14-digit ABHA number.

    Returns:
        PatientDemographics profile.

    Raises:
        ValueError: If ABHA ID is malformed or invalid.
    """
    if not abha_id or not abha_id.strip():
        raise ValueError("ABHA ID cannot be empty.")

    clean_id = abha_id.strip().lower()

    # Check pre-seeded test patients
    if clean_id in SANDBOX_PATIENTS:
        logger.info(f"ABDM Sandbox: Found registered patient for {clean_id}")
        return SANDBOX_PATIENTS[clean_id]

    # Check by numerical 14-digit format or generate sandbox profile
    for patient in SANDBOX_PATIENTS.values():
        if patient.abha_number and patient.abha_number.replace("-", "") == clean_id.replace("-", ""):
            return patient

    # Allow arbitrary sandbox addresses ending with @abdm or 10-digit/14-digit
    if "@abdm" in clean_id or len(clean_id.replace("-", "")) in (10, 12, 14):
        logger.info(f"ABDM Sandbox: Synthesizing sandbox patient profile for {clean_id}")
        name_part = clean_id.split("@")[0].replace(".", " ").title()
        return PatientDemographics(
            abha_id=clean_id,
            abha_number=f"91-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:4]}",
            name=name_part if name_part else "Sandbox Patient",
            gender="M",
            dob="1980-01-01",
            mobile="9800000000",
            address="AIIMS OPD Waiting Area, New Delhi",
            district="New Delhi",
            state="Delhi",
            is_verified=True
        )

    raise ValueError(f"Invalid ABHA address format: '{abha_id}'. Expected format 'name@abdm' or 14-digit ABHA.")


async def request_otp(aadhaar_or_mobile: str) -> str:
    """
    Simulates triggering an OTP via UIDAI / ABDM Gateway.

    Returns:
        txn_id: Unique transaction ID to pass to verify_otp.
    """
    if not aadhaar_or_mobile or not aadhaar_or_mobile.strip():
        raise ValueError("Identifier cannot be empty.")

    txn_id = f"txn_{uuid.uuid4().hex[:16]}"
    # In sandbox mode, fixed OTP is 123456
    _ACTIVE_TRANSACTIONS[txn_id] = {
        "identifier": aadhaar_or_mobile.strip(),
        "otp": "123456",
        "created_at": datetime.now(UTC),
        "expires_at": datetime.now(UTC) + timedelta(minutes=10)
    }
    logger.info(f"ABDM Sandbox: Generated OTP '123456' for {aadhaar_or_mobile} (txn_id: {txn_id})")
    return txn_id


async def verify_otp(txn_id: str, otp: str, abha_id: str | None = None) -> ABHASession:
    """
    Verify OTP and return an authenticated ABHASession.

    Args:
        txn_id: Transaction ID returned from request_otp.
        otp: 6-digit OTP code ('123456' for sandbox).
        abha_id: Optional ABHA ID. If absent, inferred from transaction identifier.
    """
    txn = _ACTIVE_TRANSACTIONS.get(txn_id)
    # Allow testing without prior request_otp if otp is 123456
    if not txn and otp != "123456":
        raise ValueError("Invalid or expired OTP transaction ID.")

    if txn and txn["otp"] != otp.strip() and otp != "123456":
        raise ValueError("Incorrect OTP entered. Sandbox default is 123456.")

    # Determine patient
    target_abha = abha_id or (txn["identifier"] if txn and "@" in txn["identifier"] else "rajesh.kumar@abdm")
    patient = await verify_abha(target_abha)

    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    auth_token = f"abdm_jwt_{uuid.uuid4().hex}"
    expires_at = datetime.now(UTC) + timedelta(hours=2)

    session = ABHASession(
        session_id=session_id,
        abha_id=patient.abha_id,
        auth_token=auth_token,
        patient=patient,
        expires_at=expires_at
    )
    logger.info(f"ABDM Sandbox: Session established for {patient.name} ({patient.abha_id})")
    return session


def get_mock_fhir_bundles(abha_id: str) -> List[Dict[str, Any]]:
    """Retrieve pre-seeded FHIR R4 documents for patient."""
    clean_id = abha_id.strip().lower()
    return MOCK_FHIR_BUNDLES.get(clean_id, [
        {
            "resourceType": "Bundle",
            "id": f"bundle-generic-{uuid.uuid4().hex[:8]}",
            "type": "document",
            "timestamp": datetime.now(UTC).isoformat(),
            "entry": []
        }
    ])
