"""
Unit tests for Sample Clinical Documents Dataset
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""

import json
from pathlib import Path

SAMPLE_DOCS_DIR = Path(__file__).resolve().parent.parent / "data" / "sample_docs"


def test_sample_documents_count():
    """Verify at least 15 sample documents exist."""
    json_files = list(SAMPLE_DOCS_DIR.glob("*.json"))
    txt_files = list(SAMPLE_DOCS_DIR.glob("*.txt"))

    assert len(json_files) >= 15, f"Expected at least 15 sample docs, found {len(json_files)}"
    assert len(json_files) == len(txt_files), "Each text document must have a matching ground-truth JSON"


def test_document_types_coverage():
    """Verify all required clinical document categories are represented."""
    json_files = list(SAMPLE_DOCS_DIR.glob("*.json"))
    doc_types = set()

    for jf in json_files:
        with open(jf, encoding="utf-8") as f:
            data = json.load(f)
            doc_types.add(data.get("document_type"))

    assert "prescription" in doc_types
    assert "lab_report" in doc_types
    assert "discharge_summary" in doc_types
    assert "radiology_report" in doc_types


def test_ground_truth_entities_structure():
    """Verify ground truth format and normalized bounding-box coordinates."""
    json_files = list(SAMPLE_DOCS_DIR.glob("*.json"))

    total_entities = 0
    for jf in json_files:
        with open(jf, encoding="utf-8") as f:
            data = json.load(f)

        assert "document_id" in data
        assert "document_type" in data
        assert "entities" in data
        assert isinstance(data["entities"], list)
        assert len(data["entities"]) > 0, f"Document {jf.name} must have at least one extracted entity"

        for ent in data["entities"]:
            total_entities += 1
            assert "type" in ent
            assert "value" in ent
            assert "confidence" in ent
            assert 0.0 <= ent["confidence"] <= 1.0

            if "bbox" in ent and ent["bbox"] is not None:
                bbox = ent["bbox"]
                assert len(bbox) == 4, "Bounding box must be [x, y, w, h]"
                x, y, w, h = bbox
                assert 0.0 <= x <= 1.0
                assert 0.0 <= y <= 1.0
                assert 0.0 <= w <= 1.0
                assert 0.0 <= h <= 1.0

    print(f"Validated {len(json_files)} documents with {total_entities} annotated clinical entities.")
