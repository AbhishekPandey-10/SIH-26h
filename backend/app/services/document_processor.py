"""
Multimodal Document OCR & Clinical Entity Extraction Pipeline
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Processes scanned prescriptions, lab slips, and discharge summaries using
Google Gemini 2.0 Flash Multimodal Vision. Extracts structured entities with
normalized bounding-box coordinates [x, y, w, h] and evaluates lab abnormalities.
"""

import json
import logging
import math
import os
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Document, ExtractedEntityModel
from app.services.gemini_retry import gemini_call_with_retry
from app.services.lab_flagging import lab_flagger
from app.shared.schemas import EntityType

logger = logging.getLogger("medikiosk.doc_processor")

PROMPT_GEMINI_OCR = """Extract all medical entities from this Indian medical document image.

For EACH entity, provide:
- type: "diagnosis" | "medication" | "lab_value" | "allergy" | "procedure" | "vital"
- value: the extracted text
- generic_name: (for medications) the generic/molecule name if identifiable
- date: date associated with this entity (DD/MM/YYYY or YYYY-MM-DD format), if visible
- confidence: 0.0 to 1.0
- bounding_box: [x, y, width, height] as NORMALIZED coordinates (0.0 to 1.0) relative to the image dimensions
- unit: (for lab values) the unit of measurement
- reference_range: (for lab values) the normal range if shown on the document

For medications, ALWAYS try to identify both the brand name and generic name.
Example: "Glycomet 500mg" -> value: "Glycomet 500mg", generic_name: "Metformin"

Output as JSON array ONLY. Do not enclose in markdown ticks if possible, or return a clean JSON array."""


def normalize_indian_date(raw_date: str | None) -> str | None:
    """
    Parse and normalize Indian dates (strictly day-first: DD/MM/YYYY) to YYYY-MM-DD.
    Enforces strict calendar validation (rejects invalid leap days, invalid months/days).
    Returns normalized YYYY-MM-DD string, or None if invalid/unparseable.
    """
    if not raw_date or not isinstance(raw_date, str):
        return None

    clean = raw_date.strip()
    if not clean or clean.lower() in ("none", "null"):
        return None

    if clean.lower() in ("unknown", "date unknown"):
        return clean

    # 1. Direct YYYY-MM-DD check with calendar validation
    if re.match(r"^\d{4}-\d{2}-\d{2}$", clean):
        try:
            parts = clean.split("-")
            dt = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
            return f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}"
        except (ValueError, TypeError):
            return None

    # 2. ISO timestamp with timezone (e.g. 2026-03-15T14:30:00Z or +05:30)
    if "T" in clean:
        try:
            iso_clean = clean.replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso_clean)
            return f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}"
        except (ValueError, TypeError):
            return None

    # 3. DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY (Strict day-first Indian convention)
    match_dmy = re.match(r"^(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})$", clean)
    if match_dmy:
        d_str, m_str, y_str = match_dmy.group(1), match_dmy.group(2), match_dmy.group(3)
        try:
            day, month, year = int(d_str), int(m_str), int(y_str)
            dt = datetime(year, month, day)
            return f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}"
        except (ValueError, TypeError):
            return None

    # 4. Textual month variants: DD Mon YYYY, DD-Mon-YYYY (e.g. 15 Mar 2025, 15-March-2025)
    for fmt in ("%d %b %Y", "%d %B %Y", "%d-%b-%Y", "%d-%B-%Y", "%d/%b/%Y", "%d/%B/%Y"):
        try:
            dt = datetime.strptime(clean, fmt)
            return f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}"
        except (ValueError, TypeError):
            continue

    return None


class DocumentProcessor:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
        self.model_name = settings.GEMINI_MODEL or "gemini-2.0-flash"
        self._client = None

    def _get_client(self):
        if not self.api_key:
            return None
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Unable to initialize Gemini client: {e}")
                return None
        return self._client

    async def process_document(
        self,
        document_id: str,
        db: AsyncSession,
        progress_callback=None,
    ) -> List[ExtractedEntityModel]:
        """
        Processes a Document record: runs OCR, evaluates lab values, stores entities in DB,
        and updates Document.status.

        Guarantees:
        - Transactional idempotency: deletes previously extracted entities for this document.
        - Zero fabrication: missing or failed OCR produces zero invented facts.
        - Canonical EntityType validation and strict bbox validation ([0, 1] or None).
        - Error rollback: on failure, sets status='error' without leaving partial clinical entities.
        """
        stmt = select(Document).where(Document.id == document_id)
        res = await db.execute(stmt)
        doc = res.scalar_one_or_none()
        if not doc:
            raise ValueError(f"Document {document_id} not found")

        # Set processing status
        doc.status = "processing"
        await db.commit()

        if progress_callback:
            await progress_callback(doc.session_id, document_id, "processing", 0.25)

        raw_entities: List[Dict[str, Any]] = []

        try:
            image_path = Path(doc.file_path)
            if not image_path.exists():
                raise FileNotFoundError(f"Image file not found at {doc.file_path}")

            if progress_callback:
                await progress_callback(doc.session_id, document_id, "extracting", 0.50)

            # Invoke Gemini Vision
            client = self._get_client()
            raw_entities = await self._call_gemini_vision(client, image_path)

            if progress_callback:
                await progress_callback(doc.session_id, document_id, "extracting", 0.75)

            # Transactional replacement: delete any existing entities for this document
            await db.execute(
                delete(ExtractedEntityModel).where(ExtractedEntityModel.document_id == doc.id)
            )

            # Parse, evaluate, and save validated entities
            saved_entities: List[ExtractedEntityModel] = []
            for item in raw_entities:
                val = str(item.get("value", "")).strip()
                if not val:
                    continue

                raw_etype = str(item.get("type", "medication")).lower().strip()
                if raw_etype in ("vital_sign", "vitals"):
                    raw_etype = "vital"
                # Strip unwanted suffixes
                raw_etype = raw_etype.split(":")[0].replace("_low_confidence", "")

                # Validate against canonical EntityType
                valid_types = {e.value for e in EntityType}
                etype = raw_etype if raw_etype in valid_types else EntityType.MEDICATION.value

                unit = item.get("unit")
                ref_range = item.get("reference_range")
                is_abnormal = None

                # Evaluate lab values against Indian clinical reference ranges
                if etype == EntityType.LAB_VALUE.value:
                    flag, detected_range = lab_flagger.evaluate_lab_value(
                        test_name=val,
                        value_text=val,
                        unit=unit,
                    )
                    is_abnormal = flag
                    if detected_range and not ref_range:
                        ref_range = detected_range

                # Strict bounding-box validation: must be 4 finite floats in [0, 1]
                bbox = item.get("bounding_box") or item.get("bbox")
                normalized_bbox = None
                if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
                    try:
                        coords = [float(c) for c in bbox]
                        if all(math.isfinite(c) and 0.0 <= c <= 1.0 for c in coords):
                            x, y, w, h = coords
                            if x + w <= 1.001 and y + h <= 1.001:
                                normalized_bbox = [round(c, 4) for c in coords]
                    except (ValueError, TypeError):
                        normalized_bbox = None

                # Strict calendar date normalization
                norm_date = normalize_indian_date(item.get("date"))

                # Finite confidence validation in [0.0, 1.0]
                try:
                    conf = float(item.get("confidence", 1.0))
                    if not math.isfinite(conf):
                        conf = 0.0
                    else:
                        conf = max(0.0, min(1.0, conf))
                except (ValueError, TypeError):
                    conf = 1.0

                entity_model = ExtractedEntityModel(
                    id=f"ent_{uuid.uuid4().hex[:12]}",
                    document_id=doc.id,
                    session_id=doc.session_id,
                    entity_type=etype,
                    value=val,
                    generic_name=item.get("generic_name") or item.get("generic"),
                    date=norm_date,
                    bounding_box=normalized_bbox,
                    confidence=conf,
                    unit=unit,
                    reference_range=ref_range,
                    is_abnormal=is_abnormal,
                    created_at=datetime.now(UTC),
                )
                db.add(entity_model)
                saved_entities.append(entity_model)

            doc.status = "extracted"
            await db.commit()

            if progress_callback:
                await progress_callback(doc.session_id, document_id, "done", 1.0)

            logger.info(f"Successfully extracted {len(saved_entities)} entities for document {document_id}")
            return saved_entities

        except Exception as e:
            logger.error(f"Failed to process document {document_id}: {e}", exc_info=True)
            await db.rollback()

            # Persist explicit error status in clean transaction
            stmt_err = select(Document).where(Document.id == document_id)
            res_err = await db.execute(stmt_err)
            doc_err = res_err.scalar_one_or_none()
            if doc_err:
                doc_err.status = "error"
                await db.commit()

            if progress_callback and doc:
                await progress_callback(doc.session_id, document_id, "error", 0.0)
            raise

    async def _call_gemini_vision(self, client: Any, image_path: Path) -> List[Dict[str, Any]]:
        """Invokes Gemini Multimodal Vision to extract medical entities."""
        if not client:
            raise RuntimeError("OCR vision provider is not configured or unavailable")

        with Image.open(image_path):
            pass  # Verifies image is readable

        response = gemini_call_with_retry(
            client, self.model_name,
            [PROMPT_GEMINI_OCR, image_path.read_bytes()],
        )
        if response is None:
            return []

        text = response.text.strip()
        if not text:
            return []

        # Clean markdown json fences if present
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "entities" in parsed:
            return parsed["entities"]
        return []


document_processor = DocumentProcessor()
