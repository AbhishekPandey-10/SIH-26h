"""
FHIR R4 Bundle Builder for ABDM Compliance
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Maps SummaryField[] -> Standardized FHIR R4 Bundle (Composition + Condition +
MedicationStatement + AllergyIntolerance + DocumentReference).
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from app.shared.schemas import SummaryField

logger = logging.getLogger("medikiosk.fhir_builder")


class FHIRBuilder:
    """
    Builds ABDM-compliant FHIR R4 Document Bundles.
    """

    def build_bundle(
        self,
        session_id: str,
        summary_fields: list[SummaryField],
        patient_abha_id: str = "rajesh.kumar@abdm",
        encounter_id: str | None = None,
    ) -> dict[str, Any]:
        enc_id = encounter_id or f"enc_{session_id}"
        timestamp_str = datetime.now(UTC).isoformat()

        bundle_id = f"bundle-{uuid.uuid4().hex[:12]}"
        composition_id = f"comp-{uuid.uuid4().hex[:8]}"

        entries: list[dict[str, Any]] = []
        sections_composition: list[dict[str, Any]] = []
        doc_refs_seen: set[str] = set()

        # Build individual clinical entries referenced by Composition
        for sf in summary_fields:
            section_key = sf.section.lower()
            field_entries_refs: list[dict[str, str]] = []

            # 1. Condition for Chief Complaint, HPI, PMH, ROS
            if section_key in ["chief_complaint", "hpi", "pmh", "ros"]:
                cond_id = f"cond-{uuid.uuid4().hex[:8]}"
                ver_code = "confirmed" if sf.verification in ["patient_reported", "document_extracted"] else "provisional"
                condition_resource = {
                    "resourceType": "Condition",
                    "id": cond_id,
                    "clinicalStatus": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                                "code": "active",
                                "display": "Active",
                            }
                        ]
                    },
                    "verificationStatus": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                                "code": ver_code,
                                "display": ver_code.title(),
                            }
                        ]
                    },
                    "code": {"text": sf.content},
                    "subject": {"reference": f"Patient/{patient_abha_id}"},
                }
                entries.append({"fullUrl": f"urn:uuid:{cond_id}", "resource": condition_resource})
                field_entries_refs.append({"reference": f"urn:uuid:{cond_id}"})

            # 2. MedicationStatement for medications
            elif section_key == "medications":
                med_id = f"med-{uuid.uuid4().hex[:8]}"
                med_resource = {
                    "resourceType": "MedicationStatement",
                    "id": med_id,
                    "status": "active",
                    "medicationCodeableConcept": {"text": sf.content},
                    "subject": {"reference": f"Patient/{patient_abha_id}"},
                    "dateAsserted": timestamp_str,
                }
                entries.append({"fullUrl": f"urn:uuid:{med_id}", "resource": med_resource})
                field_entries_refs.append({"reference": f"urn:uuid:{med_id}"})

            # 3. AllergyIntolerance for allergies
            elif section_key == "allergies":
                allergy_id = f"all-{uuid.uuid4().hex[:8]}"
                allergy_resource = {
                    "resourceType": "AllergyIntolerance",
                    "id": allergy_id,
                    "clinicalStatus": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                                "code": "active",
                                "display": "Active",
                            }
                        ]
                    },
                    "verificationStatus": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                                "code": "confirmed",
                            }
                        ]
                    },
                    "code": {"text": sf.content},
                    "patient": {"reference": f"Patient/{patient_abha_id}"},
                }
                entries.append({"fullUrl": f"urn:uuid:{allergy_id}", "resource": allergy_resource})
                field_entries_refs.append({"reference": f"urn:uuid:{allergy_id}"})

            # Document references from sources
            for src in sf.sources:
                if src.type == "document" and src.ref_id not in doc_refs_seen:
                    doc_refs_seen.add(src.ref_id)
                    doc_id = f"docref-{uuid.uuid4().hex[:8]}"
                    doc_resource = {
                        "resourceType": "DocumentReference",
                        "id": doc_id,
                        "status": "current",
                        "description": f"Scanned OPD document entity {src.ref_id}",
                        "subject": {"reference": f"Patient/{patient_abha_id}"},
                        "content": [
                            {
                                "attachment": {
                                    "contentType": "image/jpeg",
                                    "url": src.bbox_crop_url or f"/api/documents/{src.ref_id}",
                                }
                            }
                        ],
                    }
                    entries.append({"fullUrl": f"urn:uuid:{doc_id}", "resource": doc_resource})
                    field_entries_refs.append({"reference": f"urn:uuid:{doc_id}"})

            # Append section to Composition
            sections_composition.append({
                "title": sf.section.replace("_", " ").title(),
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": self._section_to_loinc(sf.section),
                            "display": sf.section.replace("_", " ").title(),
                        }
                    ]
                },
                "text": {
                    "status": "generated",
                    "div": f'<div xmlns="http://www.w3.org/1999/xhtml">{sf.content} (Verification: {sf.verification})</div>',
                },
                "entry": field_entries_refs,
            })

        # Top-level Composition resource
        composition_resource = {
            "resourceType": "Composition",
            "id": composition_id,
            "status": "final",
            "type": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "371530004",
                        "display": "Clinical consultation report",
                    }
                ]
            },
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "34133-9",
                            "display": "Summary of episode note",
                        }
                    ]
                }
            ],
            "subject": {"reference": f"Patient/{patient_abha_id}"},
            "encounter": {"reference": f"Encounter/{enc_id}"},
            "date": timestamp_str,
            "author": [{"display": "MediKiosk AI Intake Engine"}],
            "title": "MediKiosk OPD Clinical Intake Record",
            "section": sections_composition,
        }

        # Composition MUST be the first entry in an FHIR Document Bundle
        final_entries = [{"fullUrl": f"urn:uuid:{composition_id}", "resource": composition_resource}] + entries

        bundle = {
            "resourceType": "Bundle",
            "id": bundle_id,
            "meta": {
                "versionId": "1",
                "lastUpdated": timestamp_str,
                "profile": ["https://nrces.in/ndhm/fhir/r4/StructureDefinition/OPConsultRecord"],
            },
            "identifier": {
                "system": "https://medikiosk.in/bundle",
                "value": f"bundle-{session_id}",
            },
            "type": "document",
            "timestamp": timestamp_str,
            "entry": final_entries,
        }

        logger.info(f"Built FHIR R4 document bundle {bundle_id} with {len(final_entries)} entries for session {session_id}")
        return bundle

    def _section_to_loinc(self, section: str) -> str:
        loinc_map = {
            "chief_complaint": "10154-3",
            "hpi": "10164-2",
            "pmh": "11348-0",
            "medications": "10160-0",
            "allergies": "48765-2",
            "family_hx": "10157-6",
            "personal_hx": "11366-2",
            "ros": "10187-3",
        }
        return loinc_map.get(section.lower(), "42349-1")


fhir_builder = FHIRBuilder()
