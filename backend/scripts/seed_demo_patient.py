"""
C1. Seed Demo Patient — Rajesh Kumar
PS ID26047 — Final Phase Demo Prep

Inserts the demo patient into the database with:
- Patient record (male, 58yo, ABHA rajesh.kumar@abdm)
- Two historical session records
- Document records + extracted entities for both visits
- Deliberately seeds the Metformin 500mg contradiction trigger
"""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete

from app.db.database import async_session_factory, init_db
from app.db.models import (
    Document,
    ExtractedEntityModel,
    Patient,
    Session,
)


async def seed_demo_patient():
    """Seed Rajesh Kumar with 2 historical visits."""
    await init_db()

    async with async_session_factory() as db:
        # 0. Clean up any existing demo records for idempotency
        demo_session_ids = ["demo_visit1_rx", "demo_visit2_lab"]
        demo_doc_ids = ["demo_doc_rx_001", "demo_doc_lab_001"]
        await db.execute(delete(ExtractedEntityModel).where(ExtractedEntityModel.session_id.in_(demo_session_ids)))
        await db.execute(delete(Document).where(Document.id.in_(demo_doc_ids)))
        await db.execute(delete(Session).where(Session.id.in_(demo_session_ids)))
        await db.execute(delete(Patient).where(Patient.abha_id == "rajesh.kumar@abdm"))
        await db.commit()

        # 1. Create Patient
        patient = Patient(
            id="demo_rajesh_001",
            abha_id="rajesh.kumar@abdm",
            abha_number="91-1024-5829-1482",
            name="Rajesh Kumar",
            gender="M",
            dob="1968-05-14",
            mobile="9876543210",
            address="House 42, Pocket B, Mayur Vihar Phase II",
            district="East Delhi",
            state="Delhi",
        )
        db.add(patient)

        # 2. Historical Visit 1 — 3 months ago: Prescription
        visit1_id = "demo_visit1_rx"
        visit1_session = Session(
            id=visit1_id,
            patient_id="demo_rajesh_001",
            language="hi",
            status="completed",
            interview_mode="allopathic",
            started_at=datetime.now(UTC) - timedelta(days=90),
            ended_at=datetime.now(UTC) - timedelta(days=90),
        )
        db.add(visit1_session)

        visit1_doc = Document(
            id="demo_doc_rx_001",
            session_id=visit1_id,
            file_path="data/sample_docs/doc_01_prescription_printed.txt",
            file_type="prescription",
            status="extracted",
        )
        db.add(visit1_doc)

        # Extracted entities from Visit 1 prescription
        visit1_entities = [
            ExtractedEntityModel(
                id="demo_ent_met500",
                document_id="demo_doc_rx_001",
                session_id=visit1_id,
                entity_type="medication",
                value="Tab. Glycomet GP 1 (Metformin 500mg + Glimepiride 1mg)",
                generic_name="Metformin",
                date="2026-06-15",
                bounding_box=[0.08, 0.35, 0.65, 0.06],
                confidence=0.99,
            ),
            ExtractedEntityModel(
                id="demo_ent_ecosprin",
                document_id="demo_doc_rx_001",
                session_id=visit1_id,
                entity_type="medication",
                value="Tab. Ecosprin 75 (Aspirin 75mg)",
                generic_name="Aspirin",
                date="2026-06-15",
                bounding_box=[0.08, 0.43, 0.55, 0.06],
                confidence=0.98,
            ),
            ExtractedEntityModel(
                id="demo_ent_telma",
                document_id="demo_doc_rx_001",
                session_id=visit1_id,
                entity_type="medication",
                value="Tab. Telma 40 (Telmisartan 40mg)",
                generic_name="Telmisartan",
                date="2026-06-15",
                bounding_box=[0.08, 0.51, 0.55, 0.06],
                confidence=0.99,
            ),
        ]
        for e in visit1_entities:
            db.add(e)

        # 3. Historical Visit 2 — 1 month ago: Lab Report
        visit2_id = "demo_visit2_lab"
        visit2_session = Session(
            id=visit2_id,
            patient_id="demo_rajesh_001",
            language="hi",
            status="completed",
            interview_mode="allopathic",
            started_at=datetime.now(UTC) - timedelta(days=30),
            ended_at=datetime.now(UTC) - timedelta(days=30),
        )
        db.add(visit2_session)

        visit2_doc = Document(
            id="demo_doc_lab_001",
            session_id=visit2_id,
            file_path="data/sample_docs/doc_12_lab_hba1c.txt",
            file_type="lab",
            status="extracted",
        )
        db.add(visit2_doc)

        visit2_entities = [
            ExtractedEntityModel(
                id="demo_ent_hba1c",
                document_id="demo_doc_lab_001",
                session_id=visit2_id,
                entity_type="lab_value",
                value="HbA1c: 6.8%",
                generic_name="HbA1c",
                date="2026-08-15",
                bounding_box=[0.55, 0.20, 0.35, 0.06],
                confidence=0.98,
                unit="%",
                reference_range="< 5.7%",
                is_abnormal=True,
            ),
            ExtractedEntityModel(
                id="demo_ent_sgpt",
                document_id="demo_doc_lab_001",
                session_id=visit2_id,
                entity_type="lab_value",
                value="SGPT (ALT): 28 U/L",
                generic_name="SGPT",
                date="2026-08-15",
                bounding_box=[0.55, 0.30, 0.35, 0.06],
                confidence=0.97,
                unit="U/L",
                reference_range="7-56 U/L",
                is_abnormal=False,
            ),
            ExtractedEntityModel(
                id="demo_ent_hb",
                document_id="demo_doc_lab_001",
                session_id=visit2_id,
                entity_type="lab_value",
                value="Hemoglobin: 9.2 g/dL",
                generic_name="Hemoglobin",
                date="2026-08-15",
                bounding_box=[0.55, 0.40, 0.35, 0.06],
                confidence=0.99,
                unit="g/dL",
                reference_range="13.0-17.0 g/dL",
                is_abnormal=True,
            ),
        ]
        for e in visit2_entities:
            db.add(e)

        try:
            await db.commit()
            print("[OK] Demo patient 'Rajesh Kumar' seeded successfully!")
            print(f"   Patient ID: demo_rajesh_001")
            print(f"   Visit 1 (Rx): {visit1_id} -- Metformin 500mg, Ecosprin 75mg, Telmisartan 40mg")
            print(f"   Visit 2 (Lab): {visit2_id} -- HbA1c 6.8%, SGPT 28, Hb 9.2")
            print(f"   Contradiction trigger: Metformin 500mg -> patient says 1000mg")
            print(f"   Red flag trigger: chest pain (seene mein dard)")
        except Exception as e:
            print(f"[!] Seed failed: {e}")
            await db.rollback()


if __name__ == "__main__":
    asyncio.run(seed_demo_patient())
