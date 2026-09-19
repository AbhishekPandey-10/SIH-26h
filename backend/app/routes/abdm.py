"""
ABDM Auto-Fetch Gateway Integration & Document Extraction Pipeline
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
Dev 1 ABDM Gateway Client
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db
from app.db.models import Document, ExtractedEntityModel, Patient, Session
from app.dependencies import check_effective_consent
from app.services.abdm import SANDBOX_PATIENTS
from app.services.document_processor import document_processor
from app.services.session_manager import session_manager

logger = logging.getLogger("medikiosk.routes.abdm")
router = APIRouter(prefix="/api/abdm", tags=["ABDM Gateway"])


class ABDMFetchRequest(BaseModel):
    abha_id: str = Field(..., description="Patient ABHA ID (e.g., rahul.sharma@abdm or 91-1234-5678-9012)")
    session_id: str = Field(..., description="Active kiosk session identifier")


class ABDMFetchResponse(BaseModel):
    status: str
    abha_id: str
    session_id: str
    records_retrieved: int
    records: List[Dict[str, Any]]
    extracted_entities_count: int


# Pre-seeded sandbox medical records for authorized sandbox patient
PATIENT_SANDBOX_RECORDS: Dict[str, List[Dict[str, Any]]] = {
    "rajesh.kumar@abdm": [
        {
            "doc_id_prefix": "abdm_presc",
            "file_type": "prescription",
            "title": "Cardiology OPD Prescription - AIIMS New Delhi",
            "date": "2026-03-10",
            "entities": [
                {
                    "entity_type": "medication",
                    "value": "Tab Telmisartan 40mg OD morning",
                    "generic_name": "Telmisartan",
                    "confidence": 0.96,
                    "bounding_box": [0.12, 0.35, 0.48, 0.08]
                },
                {
                    "entity_type": "medication",
                    "value": "Tab Atorvastatin 20mg HS night",
                    "generic_name": "Atorvastatin",
                    "confidence": 0.95,
                    "bounding_box": [0.12, 0.45, 0.45, 0.08]
                },
                {
                    "entity_type": "diagnosis",
                    "value": "Essential Hypertension & Dyslipidemia",
                    "generic_name": "Hypertension",
                    "confidence": 0.93,
                    "bounding_box": [0.15, 0.22, 0.60, 0.07]
                }
            ]
        },
        {
            "doc_id_prefix": "abdm_lab",
            "file_type": "lab",
            "title": "Biochemistry Lab Report - Dr. Lal PathLabs",
            "date": "2026-04-15",
            "entities": [
                {
                    "entity_type": "lab_value",
                    "value": "HbA1c: 7.4%",
                    "generic_name": "Glycated Hemoglobin",
                    "unit": "%",
                    "reference_range": "< 5.7%",
                    "is_abnormal": True,
                    "confidence": 0.98,
                    "bounding_box": [0.10, 0.50, 0.55, 0.08]
                },
                {
                    "entity_type": "lab_value",
                    "value": "Serum Creatinine: 1.1 mg/dL",
                    "generic_name": "Creatinine",
                    "unit": "mg/dL",
                    "reference_range": "0.7 - 1.3 mg/dL",
                    "is_abnormal": False,
                    "confidence": 0.97,
                    "bounding_box": [0.10, 0.62, 0.55, 0.08]
                }
            ]
        }
    ]
}


@router.post("/fetch-records", response_model=ABDMFetchResponse)
async def fetch_abdm_records_endpoint(
    req: ABDMFetchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    POST /api/abdm/fetch-records
    Retrieves health records linked to patient's ABHA ID from the ABDM sandbox gateway
    and stores retrieved records for the active session.
    Requires active session, explicit store_abdm consent, and a valid registered ABHA identity.
    """
    logger.info(f"Initiating ABDM auto-fetch for ABHA: {req.abha_id}, Session: {req.session_id}")

    # 1. Assert session active
    await session_manager.assert_session_active(req.session_id, db)

    # 2. Assert effective consent for 'store_abdm'
    await check_effective_consent(req.session_id, "store_abdm", db)

    # 3. Validate ABHA ID against registered sandbox patients
    clean_id = req.abha_id.strip().lower()
    matched_patient = None
    if clean_id in SANDBOX_PATIENTS:
        matched_patient = SANDBOX_PATIENTS[clean_id]
    else:
        for p in SANDBOX_PATIENTS.values():
            if p.abha_number == req.abha_id.strip() or p.abha_id.lower() == clean_id:
                matched_patient = p
                break

    if not matched_patient:
        logger.warning(f"ABDM fetch rejected: unknown ABHA ID '{req.abha_id}'")
        raise HTTPException(
            status_code=404,
            detail=f"Patient identity '{req.abha_id}' not found in ABDM Sandbox registry.",
        )

    # Ensure upload directory exists
    upload_dir = Path(settings.UPLOAD_DIR).resolve() / "documents" / req.session_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Fetch records for matched patient
    patient_records = PATIENT_SANDBOX_RECORDS.get(matched_patient.abha_id, [])

    total_extracted = 0
    records_meta = []

    for record_data in patient_records:
        doc_id = f"{record_data['doc_id_prefix']}_{uuid.uuid4().hex[:8]}"
        filename = f"{doc_id}.txt"
        file_path = upload_dir / filename

        # Write text record file for document storage
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"ABDM Sandbox Record: {record_data['title']}\nDate: {record_data['date']}\nABHA: {matched_patient.abha_id}\n")

        # Create Document row
        doc = Document(
            id=doc_id,
            session_id=req.session_id,
            file_path=str(file_path),
            file_type=record_data["file_type"],
            page_number=1,
            status="extracted",
            uploaded_at=datetime.now(UTC),
        )
        db.add(doc)

        # Ingest extracted entities directly into ExtractedEntityModel table
        for ent in record_data["entities"]:
            db_ent = ExtractedEntityModel(
                id=f"ent_{uuid.uuid4().hex[:12]}",
                document_id=doc_id,
                session_id=req.session_id,
                entity_type=ent["entity_type"],
                value=ent["value"],
                generic_name=ent.get("generic_name"),
                date=record_data["date"],
                bounding_box=ent.get("bounding_box"),
                confidence=ent.get("confidence", 0.95),
                unit=ent.get("unit"),
                reference_range=ent.get("reference_range"),
                is_abnormal=ent.get("is_abnormal"),
                created_at=datetime.now(UTC),
            )
            db.add(db_ent)
            total_extracted += 1

        records_meta.append({
            "document_id": doc_id,
            "title": record_data["title"],
            "date": record_data["date"],
            "type": record_data["file_type"],
            "entity_count": len(record_data["entities"]),
        })

    await db.commit()
    logger.info(f"ABDM auto-fetch retrieved {len(records_meta)} records with {total_extracted} extracted entities for session {req.session_id}")

    return ABDMFetchResponse(
        status="success",
        abha_id=req.abha_id,
        session_id=req.session_id,
        records_retrieved=len(records_meta),
        records=records_meta,
        extracted_entities_count=total_extracted,
    )
