"""
FHIR R4 Bundle Builder for ABDM Compliance
PS ID26047 — Assignment 6

Builds FHIR R4 Document Bundles from reviewed ClinicalSummary data.

Design invariants:
- No default identities: patient_abha_id and patient_id are required.
- Composition status reflects actual review state (preliminary vs final).
- Alert prose, stopped medications, and unresolved conflicts are NOT emitted
  as active MedicationStatements.
- Narrative XHTML is properly escaped.
- References use urn:uuid: consistently (ABHA address is never used as resource ID).
"""

import html
import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from app.shared.schemas import SummaryField

logger = logging.getLogger("medikiosk.fhir_builder")

# Patterns that indicate non-medication prose that should NOT become MedicationStatements
_ALERT_PATTERNS = re.compile(
    r"(?i)(?:"
    r"alert[:\s]|⚠|conflict[:\s]|"
    r"polypharmacy|interaction|contraindic|duplicate|"
    r"warning[:\s]|caution[:\s]|"
    r"no\s+(?:known|current)\s+medications?"
    r")"
)

# Section key → LOINC code mapping (ABDM / NRCES profile compliant)
_LOINC_MAP: dict[str, str] = {
    "chief_complaint": "10154-3",
    "hpi": "10164-2",
    "pmh": "11348-0",
    "past_history": "11348-0",
    "medications": "10160-0",
    "current_medications": "10160-0",
    "allergies": "48765-2",
    "family_hx": "10157-6",
    "personal_hx": "11366-2",
    "family_personal": "10157-6",
    "ros": "10187-3",
    "vitals_labs": "8716-3",
    "red_flags": "74018-3",
    "plan_assessment": "51847-2",
    "changes_since_last_visit": "11506-3",
    # Ayurvedic sections
    "prakriti_dosha": "42349-1",
    "agni_digestive_fire": "42349-1",
    "dhatu_tissue_health": "42349-1",
    "chikitsa_recommendations": "42349-1",
}


def _escape_xhtml(text: str) -> str:
    """Escape content for safe embedding in XHTML div elements."""
    return html.escape(text, quote=True)


def _is_alert_prose(content: str) -> bool:
    """Check if medication field content is alert/conflict prose rather than actual medication data."""
    return bool(_ALERT_PATTERNS.search(content))


def _determine_medication_status(content: str) -> str:
    """
    Determine FHIR MedicationStatement status from content.
    Returns 'active', 'stopped', or 'unknown'.
    Does NOT return a status for alert prose (caller should skip those).
    """
    content_lower = content.lower()
    if any(kw in content_lower for kw in ("stopped", "discontinued", "no longer taking")):
        return "stopped"
    if any(kw in content_lower for kw in ("previously", "former", "past")):
        return "stopped"
    return "active"


class FHIRBuilder:
    """
    Builds ABDM-compliant FHIR R4 Document Bundles from reviewed clinical data.

    IMPORTANT: This builder does NOT default any patient identity.
    Callers MUST provide resolved, verified patient and encounter identifiers.
    """

    def build_bundle(
        self,
        session_id: str,
        summary_fields: list[SummaryField],
        patient_id: str,
        patient_abha_id: str,
        encounter_id: str | None = None,
        summary_verified: bool = False,
        verified_by: str | None = None,
    ) -> dict[str, Any]:
        """
        Build a FHIR R4 Document Bundle from reviewed summary fields.

        Args:
            session_id: Kiosk encounter session UUID.
            summary_fields: Reviewed and validated SummaryField list.
            patient_id: Internal patient UUID (from patients table).
            patient_abha_id: Verified ABHA address/number.
            encounter_id: Optional encounter UUID; defaults to session_id.
            summary_verified: True if summary has been doctor_verified.
            verified_by: Clinician ID who signed off the summary.

        Returns:
            FHIR R4 Bundle dictionary.
        """
        if not patient_id or not str(patient_id).strip():
            raise ValueError("patient_id is required; cannot build bundle without explicit patient identity")
        if not patient_abha_id or not str(patient_abha_id).strip():
            raise ValueError("patient_abha_id is required; cannot build bundle without explicit patient identity")

        enc_id = encounter_id or session_id
        timestamp_str = datetime.now(UTC).isoformat()

        bundle_id = f"bundle-{uuid.uuid4().hex[:12]}"
        composition_id = str(uuid.uuid4())
        patient_resource_id = str(uuid.uuid4())
        encounter_resource_id = str(uuid.uuid4())

        entries: list[dict[str, Any]] = []
        sections_composition: list[dict[str, Any]] = []
        doc_refs_seen: set[str] = set()

        # Patient resource
        patient_resource = {
            "resourceType": "Patient",
            "id": patient_resource_id,
            "identifier": [
                {
                    "system": "https://healthid.abdm.gov.in",
                    "value": str(patient_abha_id).strip(),
                },
                {
                    "system": "urn:medikiosk:patient-id",
                    "value": str(patient_id).strip(),
                },
            ],
        }
        entries.append({
            "fullUrl": f"urn:uuid:{patient_resource_id}",
            "resource": patient_resource,
        })

        # Encounter resource
        encounter_resource = {
            "resourceType": "Encounter",
            "id": encounter_resource_id,
            "status": "finished",
            "class": {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": "AMB",
                "display": "ambulatory",
            },
            "subject": {"reference": f"urn:uuid:{patient_resource_id}"},
        }
        entries.append({
            "fullUrl": f"urn:uuid:{encounter_resource_id}",
            "resource": encounter_resource,
        })

        patient_ref = f"urn:uuid:{patient_resource_id}"

        # Build individual clinical entries referenced by Composition
        for sf in summary_fields:
            section_key = sf.section.lower() if isinstance(sf.section, str) else sf.section.value.lower()
            field_entries_refs: list[dict[str, str]] = []

            # Determine verification code from field-level verification
            ver_str = sf.verification if isinstance(sf.verification, str) else sf.verification.value
            ver_code = (
                "confirmed"
                if ver_str in ("patient_reported", "document_extracted", "doctor_edited")
                else "provisional"
            )

            # 1. Condition for Chief Complaint, HPI, PMH/past_history, ROS, vitals_labs, red_flags, plan_assessment
            if section_key in (
                "chief_complaint", "hpi", "pmh", "past_history", "ros",
                "vitals_labs", "red_flags", "plan_assessment",
                "changes_since_last_visit",
            ):
                cond_id = str(uuid.uuid4())
                condition_resource = {
                    "resourceType": "Condition",
                    "id": cond_id,
                    "clinicalStatus": {
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                            "code": "active",
                            "display": "Active",
                        }]
                    },
                    "verificationStatus": {
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                            "code": ver_code,
                            "display": ver_code.title(),
                        }]
                    },
                    "code": {"text": sf.content},
                    "subject": {"reference": patient_ref},
                    "encounter": {"reference": f"urn:uuid:{encounter_resource_id}"},
                }
                entries.append({"fullUrl": f"urn:uuid:{cond_id}", "resource": condition_resource})
                field_entries_refs.append({"reference": f"urn:uuid:{cond_id}"})

            # 2. MedicationStatement for medications/current_medications
            elif section_key in ("medications", "current_medications"):
                # Skip alert/conflict prose — do NOT emit as active medication
                if _is_alert_prose(sf.content):
                    logger.info(
                        f"Skipping alert/conflict prose from FHIR medication resource: "
                        f"{sf.content[:80]}..."
                    )
                else:
                    med_id = str(uuid.uuid4())
                    med_status = _determine_medication_status(sf.content)
                    med_resource = {
                        "resourceType": "MedicationStatement",
                        "id": med_id,
                        "status": med_status,
                        "medicationCodeableConcept": {"text": sf.content},
                        "subject": {"reference": patient_ref},
                        "context": {"reference": f"urn:uuid:{encounter_resource_id}"},
                        "dateAsserted": timestamp_str,
                    }
                    entries.append({"fullUrl": f"urn:uuid:{med_id}", "resource": med_resource})
                    field_entries_refs.append({"reference": f"urn:uuid:{med_id}"})

            # 3. AllergyIntolerance for allergies
            elif section_key == "allergies":
                allergy_id = str(uuid.uuid4())
                allergy_resource = {
                    "resourceType": "AllergyIntolerance",
                    "id": allergy_id,
                    "clinicalStatus": {
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                            "code": "active",
                            "display": "Active",
                        }]
                    },
                    "verificationStatus": {
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                            "code": ver_code,
                        }]
                    },
                    "code": {"text": sf.content},
                    "patient": {"reference": patient_ref},
                }
                entries.append({"fullUrl": f"urn:uuid:{allergy_id}", "resource": allergy_resource})
                field_entries_refs.append({"reference": f"urn:uuid:{allergy_id}"})

            # 4. FamilyMemberHistory or Observation for family_personal
            elif section_key in ("family_personal", "family_hx", "personal_hx"):
                obs_id = str(uuid.uuid4())
                obs_resource = {
                    "resourceType": "Observation",
                    "id": obs_id,
                    "status": "final",
                    "code": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": _LOINC_MAP.get(section_key, "42349-1"),
                            "display": section_key.replace("_", " ").title(),
                        }],
                        "text": section_key.replace("_", " ").title(),
                    },
                    "subject": {"reference": patient_ref},
                    "valueString": sf.content,
                }
                entries.append({"fullUrl": f"urn:uuid:{obs_id}", "resource": obs_resource})
                field_entries_refs.append({"reference": f"urn:uuid:{obs_id}"})

            # Document references from sources
            for src in sf.sources:
                src_type = src.type if isinstance(src.type, str) else src.type
                if src_type == "document" and src.ref_id not in doc_refs_seen:
                    doc_refs_seen.add(src.ref_id)
                    doc_id = str(uuid.uuid4())
                    doc_resource = {
                        "resourceType": "DocumentReference",
                        "id": doc_id,
                        "status": "current",
                        "description": f"Scanned OPD document entity {src.ref_id}",
                        "subject": {"reference": patient_ref},
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
            section_title = section_key.replace("_", " ").title()
            loinc_code = _LOINC_MAP.get(section_key, "42349-1")

            escaped_content = _escape_xhtml(sf.content)
            escaped_verification = _escape_xhtml(ver_str)

            sections_composition.append({
                "title": section_title,
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": loinc_code,
                        "display": section_title,
                    }]
                },
                "text": {
                    "status": "generated",
                    "div": f'<div xmlns="http://www.w3.org/1999/xhtml">{escaped_content} (Verification: {escaped_verification})</div>',
                },
                "entry": field_entries_refs,
            })

        # Composition status: final ONLY if doctor has explicitly verified
        composition_status = "final" if summary_verified else "preliminary"

        # Author: include verifying clinician if available
        author = [{"display": "MediKiosk AI Intake Engine"}]
        if verified_by:
            author.append({"display": f"Dr. {verified_by} (Clinician Sign-off)"})

        # Top-level Composition resource
        composition_resource = {
            "resourceType": "Composition",
            "id": composition_id,
            "status": composition_status,
            "type": {
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "371530004",
                    "display": "Clinical consultation report",
                }]
            },
            "category": [{
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "34133-9",
                    "display": "Summary of episode note",
                }]
            }],
            "subject": {"reference": patient_ref},
            "encounter": {"reference": f"urn:uuid:{encounter_resource_id}"},
            "date": timestamp_str,
            "author": author,
            "title": "MediKiosk OPD Clinical Intake Record",
            "section": sections_composition,
        }

        # Composition MUST be the first entry in an FHIR Document Bundle
        final_entries = [
            {"fullUrl": f"urn:uuid:{composition_id}", "resource": composition_resource}
        ] + entries

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
                "value": f"bundle-{enc_id}",
            },
            "type": "document",
            "timestamp": timestamp_str,
            "entry": final_entries,
        }

        logger.info(
            f"Built FHIR R4 document bundle {bundle_id} with {len(final_entries)} entries "
            f"for session {session_id} (composition status: {composition_status})"
        )
        return bundle


fhir_builder = FHIRBuilder()
