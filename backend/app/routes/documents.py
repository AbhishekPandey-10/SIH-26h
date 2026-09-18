"""
Medical Document Ingestion, Multimodal OCR, Crop Service & Scan Status Routes
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""

import json
import logging
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Dict, List

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db
from app.db.models import Document, ExtractedEntityModel
from app.services.crop_service import crop_service
from app.services.document_processor import document_processor, normalize_indian_date

logger = logging.getLogger("medikiosk.routes.documents")

router = APIRouter(prefix="/api/documents", tags=["Document OCR & Extraction"])
ws_router = APIRouter(tags=["Scan Status WebSocket"])


# ------------------------------------------------------------------------------
# WebSocket Scan Status Connection Manager
# ------------------------------------------------------------------------------

class ScanStatusManager:
    """Manages active WebSockets listening for real-time document scan & extraction status."""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
        logger.info(f"WebSocket client subscribed to scan status for session {session_id}")

    def disconnect(self, session_id: str, websocket: WebSocket):
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def broadcast_status(
        self,
        session_id: str,
        document_id: str,
        status: str,
        progress: float | None = None,
        message: str | None = None,
    ):
        """Sends status update event to all subscribers for session_id."""
        payload = {
            "document_id": document_id,
            "status": status,
            "progress": progress,
            "message": message,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        connections = self.active_connections.get(session_id, [])
        dead_connections = []
        for ws in connections:
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:
                dead_connections.append(ws)

        for dead in dead_connections:
            self.disconnect(session_id, dead)


scan_status_manager = ScanStatusManager()


# ------------------------------------------------------------------------------
# WebSocket Endpoint: ws://localhost:8000/ws/scan-status/{session_id}
# ------------------------------------------------------------------------------

@ws_router.websocket("/ws/scan-status/{session_id}")
async def scan_status_websocket(websocket: WebSocket, session_id: str):
    """
    Real-time status stream for document scanning & Gemini OCR processing.
    Events: { document_id, status: 'uploading'|'processing'|'extracting'|'done'|'error', progress: 0.0-1.0 }
    """
    await scan_status_manager.connect(session_id, websocket)
    try:
        while True:
            # Keep connection alive; client can send ping/heartbeat
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"event": "pong"}))
    except WebSocketDisconnect:
        scan_status_manager.disconnect(session_id, websocket)
        logger.info(f"Scan status client disconnected for session {session_id}")


# ------------------------------------------------------------------------------
# REST Endpoints
# ------------------------------------------------------------------------------

class DocumentUploadResponse(BaseModel):
    document_id: str
    status: str
    file_path: str
    page_number: int


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document_endpoint(
    session_id: str = Form(..., description="Active kiosk session identifier"),
    page_number: int = Form(1, description="Page number of the document"),
    file_type: str | None = Form("prescription", description="prescription, lab, discharge, etc."),
    file: UploadFile = File(..., description="Captured image file"),
    db: AsyncSession = Depends(get_db),
):
    """
    POST /api/documents/upload
    Accepts multipart document photo from camera or gallery.
    Saves image to disk and creates a Document ORM row.
    """
    doc_id = str(uuid.uuid4())
    upload_dir = Path(settings.UPLOAD_DIR) / "documents" / session_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    extension = Path(file.filename or "scan.jpg").suffix or ".jpg"
    target_filename = f"{doc_id}_p{page_number}{extension}"
    target_path = upload_dir / target_filename

    try:
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to write uploaded file to disk: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded image file")

    doc = Document(
        id=doc_id,
        session_id=session_id,
        file_path=str(target_path),
        file_type=file_type,
        page_number=page_number,
        status="uploaded",
        uploaded_at=datetime.now(UTC),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Broadcast upload event
    await scan_status_manager.broadcast_status(
        session_id=session_id,
        document_id=doc.id,
        status="uploading",
        progress=0.1,
        message="Document uploaded successfully",
    )

    return DocumentUploadResponse(
        document_id=doc.id,
        status=doc.status,
        file_path=doc.file_path,
        page_number=doc.page_number,
    )


class ProcessDocumentResponse(BaseModel):
    document_id: str
    status: str
    entity_count: int


@router.post("/process/{doc_id}", response_model=ProcessDocumentResponse)
async def process_document_endpoint(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    POST /api/documents/process/{doc_id}
    Triggers Gemini Multimodal OCR and structured entity extraction.
    """
    try:
        entities = await document_processor.process_document(
            document_id=doc_id,
            db=db,
            progress_callback=scan_status_manager.broadcast_status,
        )
        return ProcessDocumentResponse(
            document_id=doc_id,
            status="extracted",
            entity_count=len(entities),
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error during document processing {doc_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@router.get("/{doc_id}/crop")
async def crop_document_endpoint(
    doc_id: str,
    x: float = Query(..., ge=0.0, le=1.0, description="Normalized x coordinate (0.0 - 1.0)"),
    y: float = Query(..., ge=0.0, le=1.0, description="Normalized y coordinate (0.0 - 1.0)"),
    w: float = Query(..., ge=0.0, le=1.0, description="Normalized width (0.0 - 1.0)"),
    h: float = Query(..., ge=0.0, le=1.0, description="Normalized height (0.0 - 1.0)"),
    db: AsyncSession = Depends(get_db),
):
    """
    GET /api/documents/{doc_id}/crop
    Crops image at normalized coordinates with 8% drift padding and caches result.
    Returns image/jpeg bytes.
    """
    stmt = select(Document).where(Document.id == doc_id)
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        # Check if doc_id matches a sample document in sample_docs directory
        sample_img = Path(settings.DATA_DIR) / "sample_docs" / f"{doc_id}.jpg"
        if not sample_img.exists():
            sample_img = Path(settings.DATA_DIR) / "sample_docs" / f"{doc_id}.png"
        if sample_img.exists():
            image_path = sample_img
        else:
            raise HTTPException(status_code=404, detail="Document not found")
    else:
        image_path = Path(doc.file_path)

    try:
        jpeg_bytes = crop_service.crop_document(image_path, x, y, w, h)
        return Response(content=jpeg_bytes, media_type="image/jpeg")
    except Exception as e:
        logger.error(f"Failed to crop image for doc {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Crop failure: {str(e)}")


@router.get("/{doc_id}/file")
async def get_document_file_endpoint(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    GET /api/documents/{doc_id}/file
    Serves original document image for browser rendering and bounding-box overlay.
    """
    stmt = select(Document).where(Document.id == doc_id)
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()

    if doc and Path(doc.file_path).exists():
        return FileResponse(doc.file_path)

    # Check fallback sample documents
    sample_img = Path(settings.DATA_DIR) / "sample_docs" / f"{doc_id}.jpg"
    if not sample_img.exists():
        sample_img = Path(settings.DATA_DIR) / "sample_docs" / f"{doc_id}.png"
    if sample_img.exists():
        return FileResponse(sample_img)

    raise HTTPException(status_code=404, detail="Document image file not found")


@router.get("/entities/{session_id}")
async def get_session_entities_endpoint(
    session_id: str,
    sort: str = Query("chronological", description="Sorting strategy ('chronological' | 'type')"),
    db: AsyncSession = Depends(get_db),
):
    """
    GET /api/documents/entities/{session_id}?sort=chronological
    Returns all extracted entities for a session.
    Chronologically sorts entities by extracted_date across all scanned documents.
    Missing dates sort to the end with 'Date unknown'.
    """
    # Fetch all entities for this session
    stmt_entities = select(ExtractedEntityModel).where(ExtractedEntityModel.session_id == session_id)
    res_entities = await db.execute(stmt_entities)
    entities = list(res_entities.scalars().all())

    # If empty, check if sample entities should be returned
    if not entities:
        # Check if fallback entities exist in sample_docs
        sample_path = Path(settings.DATA_DIR) / "sample_docs" / "doc_01_prescription_printed.json"
        if sample_path.exists():
            try:
                with open(sample_path, encoding="utf-8") as f:
                    s_data = json.load(f)
                    for ent in s_data.get("entities", []):
                        entities.append(
                            ExtractedEntityModel(
                                id=f"ent_mock_{uuid.uuid4().hex[:8]}",
                                document_id=s_data.get("document_id", "doc_01_prescription_printed"),
                                session_id=session_id,
                                entity_type=ent.get("type", "medication"),
                                value=ent.get("value", ""),
                                generic_name=ent.get("generic"),
                                date=ent.get("date"),
                                bounding_box=ent.get("bbox"),
                                confidence=float(ent.get("confidence", 0.95)),
                                unit=ent.get("unit"),
                                reference_range=ent.get("reference_range"),
                                is_abnormal=ent.get("is_abnormal"),
                            )
                        )
            except Exception:
                pass

    # Chronological sort:
    # Entities with valid YYYY-MM-DD sort first (earliest to latest or latest to earliest)
    def sort_key(e: ExtractedEntityModel):
        d = e.date or ""
        # If missing or unknown date, sort to end
        if not d or d.lower() in ("unknown", "date unknown", "none"):
            return (1, "9999-99-99")
        norm = normalize_indian_date(d)
        return (0, norm or d)

    if sort == "chronological":
        entities.sort(key=sort_key)

    # Format output
    entity_dicts = []
    for e in entities:
        display_date = e.date if (e.date and e.date.lower() not in ("none", "")) else "Date unknown"
        entity_dicts.append({
            "id": e.id,
            "document_id": e.document_id,
            "session_id": e.session_id,
            "entity_type": e.entity_type,
            "value": e.value,
            "generic_name": e.generic_name,
            "date": display_date,
            "extracted_date": display_date,
            "bounding_box": e.bounding_box,
            "confidence": e.confidence,
            "unit": e.unit,
            "reference_range": e.reference_range,
            "is_abnormal": e.is_abnormal,
            "crop_url": f"/api/documents/{e.document_id}/crop?x={e.bounding_box[0]}&y={e.bounding_box[1]}&w={e.bounding_box[2]}&h={e.bounding_box[3]}" if e.bounding_box and len(e.bounding_box) == 4 else None,
        })

    # Also group by document
    docs_stmt = select(Document).where(Document.session_id == session_id).order_by(Document.page_number)
    res_docs = await db.execute(docs_stmt)
    docs = list(res_docs.scalars().all())

    grouped_by_doc = {}
    for d in docs:
        doc_ents = [ent for ent in entity_dicts if ent["document_id"] == d.id]
        grouped_by_doc[d.id] = {
            "document_id": d.id,
            "file_type": d.file_type,
            "page_number": d.page_number,
            "status": d.status,
            "file_path": d.file_path,
            "image_url": f"/api/documents/{d.id}/file",
            "entities": doc_ents,
        }

    return {
        "session_id": session_id,
        "count": len(entity_dicts),
        "entities": entity_dicts,
        "grouped_by_document": grouped_by_doc,
    }


@router.get("/{session_id}")
async def list_session_documents_endpoint(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    GET /api/documents/{session_id}
    Returns list of scanned documents for a session with status and entity counts.
    """
    stmt = (
        select(Document, func.count(ExtractedEntityModel.id).label("entity_count"))
        .outerjoin(ExtractedEntityModel, ExtractedEntityModel.document_id == Document.id)
        .where(Document.session_id == session_id)
        .group_by(Document.id)
        .order_by(Document.page_number)
    )
    res = await db.execute(stmt)
    results = res.all()

    doc_list = []
    for doc, count in results:
        doc_list.append({
            "document_id": doc.id,
            "session_id": doc.session_id,
            "page_number": doc.page_number,
            "file_type": doc.file_type,
            "file_path": doc.file_path,
            "image_url": f"/api/documents/{doc.id}/file",
            "status": doc.status,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
            "entity_count": count,
        })
    return doc_list
