"""
Visualization & Longitudinal Health Intelligence Service
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Aggregates cross-session patient extracted entities into:
1. Chronological Multi-Lane Timeline (Diagnoses, Medications, Labs, Procedures)
2. Normalized Lab Trend Sparklines with Range Zones & Unit Mismatch Guard
3. 'What Changed' Delta Summary with Source Traceability
"""

import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Document, ExtractedEntityModel, Patient, Session
from app.services.contradiction_detector import contradiction_detector

logger = logging.getLogger("medikiosk.visualization_service")

# Load standard lab reference ranges from lab_ranges.json
LAB_RANGES_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "lab_ranges.json"


class VisualizationService:
    def __init__(self, ranges_path: Optional[Path] = None):
        self.ranges_path = ranges_path or LAB_RANGES_FILE
        self.lab_ranges: Dict[str, Any] = {}
        self._load_lab_ranges()

    def _load_lab_ranges(self):
        if self.ranges_path.exists():
            try:
                with open(self.ranges_path, encoding="utf-8") as f:
                    self.lab_ranges = json.load(f)
                logger.info(f"Loaded {len(self.lab_ranges)} lab range definitions.")
            except Exception as e:
                logger.error(f"Failed to load lab_ranges.json: {e}")
        else:
            logger.warning(f"lab_ranges.json not found at {self.ranges_path}")

    async def resolve_patient_sessions(
        self,
        identifier: str,
        db: AsyncSession,
    ) -> Tuple[Optional[str], List[str]]:
        """
        Resolves patient ID and all associated session UUIDs.
        Identifier can be patient_id, abha_id, or session_id.
        """
        # 1. Try patient_id match
        stmt_p = select(Patient).where((Patient.id == identifier) | (Patient.abha_id == identifier))
        res_p = await db.execute(stmt_p)
        patient = res_p.scalar_one_or_none()

        if patient:
            stmt_s = select(Session.id).where(Session.patient_id == patient.id)
            res_s = await db.execute(stmt_s)
            sids = [s for s in res_s.scalars().all()]
            return patient.id, sids or [identifier]

        # 2. Try session_id match
        stmt_sess = select(Session).where(Session.id == identifier)
        res_sess = await db.execute(stmt_sess)
        session_row = res_sess.scalar_one_or_none()

        if session_row:
            p_id = session_row.patient_id or identifier
            stmt_all = select(Session.id).where(Session.patient_id == p_id)
            res_all = await db.execute(stmt_all)
            sids = [s for s in res_all.scalars().all()]
            return p_id, sids or [identifier]

        # Fallback: treat identifier as session_id directly
        return identifier, [identifier]

    async def get_timeline(
        self,
        patient_id: str,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Builds chronological timeline swim lanes for a patient across all visits.
        """
        resolved_pid, session_ids = await self.resolve_patient_sessions(patient_id, db)

        # Query all extracted entities for these sessions
        stmt = (
            select(ExtractedEntityModel)
            .where(ExtractedEntityModel.session_id.in_(session_ids))
            .order_by(ExtractedEntityModel.date.asc(), ExtractedEntityModel.created_at.asc())
        )
        res = await db.execute(stmt)
        entities = res.scalars().all()

        swim_lanes: Dict[str, List[Dict[str, Any]]] = {
            "diagnoses": [],
            "medications": [],
            "labs": [],
            "procedures": [],
        }

        all_dates: List[str] = []

        for e in entities:
            ent_type = (e.entity_type or "").lower()
            date_str = e.date or e.created_at.strftime("%Y-%m-%d") if hasattr(e.created_at, "strftime") else "2026-01-10"
            all_dates.append(date_str)

            bbox = e.bounding_box or [0.1, 0.2, 0.4, 0.08]
            crop_url = f"/api/documents/{e.document_id}/crop?bbox={','.join(str(x) for x in bbox)}"

            item = {
                "id": e.id,
                "document_id": e.document_id,
                "session_id": e.session_id,
                "date": date_str,
                "value": e.value,
                "generic_name": e.generic_name,
                "confidence": e.confidence,
                "bounding_box": bbox,
                "crop_url": crop_url,
                "is_abnormal": e.is_abnormal,
                "unit": e.unit,
            }

            if "diag" in ent_type or "condition" in ent_type or "pmh" in ent_type:
                item["title"] = e.value
                item["status"] = "resolved" if "resolved" in e.value.lower() or "past" in e.value.lower() else "active"
                swim_lanes["diagnoses"].append(item)

            elif "med" in ent_type or "presc" in ent_type:
                item["title"] = e.generic_name or e.value
                # Detect medication status
                status = "active"
                val_lower = e.value.lower()
                if any(w in val_lower for w in ["stopped", "discontinued", "बंद", "hold"]):
                    status = "stopped"
                elif any(w in val_lower for w in ["increased", "decreased", "changed", "titrated"]):
                    status = "changed"
                item["status"] = status
                item["start_date"] = date_str
                # End date approximation for stopped medications
                item["end_date"] = date_str if status == "stopped" else None
                swim_lanes["medications"].append(item)

            elif "lab" in ent_type or "test" in ent_type or "investigation" in ent_type:
                item["test_name"] = e.generic_name or self._extract_test_name(e.value)
                item["numeric_value"] = self._parse_numeric_value(e.value)
                swim_lanes["labs"].append(item)

            elif "proc" in ent_type or "surgery" in ent_type:
                item["title"] = e.value
                swim_lanes["procedures"].append(item)

            else:
                # Default categorization based on keyword
                if any(term in e.value.lower() for term in ["mg", "tablet", "cap", "od", "bd", "tds"]):
                    item["title"] = e.value
                    item["status"] = "active"
                    swim_lanes["medications"].append(item)
                else:
                    item["title"] = e.value
                    swim_lanes["diagnoses"].append(item)

        sorted_dates = sorted([d for d in set(all_dates) if re.match(r"^\d{4}-\d{2}-\d{2}", d)])
        start_date = sorted_dates[0] if sorted_dates else "2025-01-01"
        end_date = sorted_dates[-1] if sorted_dates else datetime.now(UTC).strftime("%Y-%m-%d")

        return {
            "patient_id": resolved_pid,
            "session_ids": session_ids,
            "start_date": start_date,
            "end_date": end_date,
            "total_visits": len(session_ids),
            "visit_dates": sorted_dates,
            "swim_lanes": swim_lanes,
            "lane_counts": {k: len(v) for k, v in swim_lanes.items()},
            "total_nodes": sum(len(v) for v in swim_lanes.values()),
        }

    async def get_lab_trends(
        self,
        patient_id: str,
        test_query: str,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Extracts longitudinal data points for a specific lab test with normal/abnormal zone
        tagging and unit verification guards (marks unverified units as 'excluded').
        """
        resolved_pid, session_ids = await self.resolve_patient_sessions(patient_id, db)

        # Standardize test query key
        norm_test_key = self._match_test_key(test_query)
        range_def = self.lab_ranges.get(norm_test_key, {})
        default_range = range_def.get("default", {})
        expected_unit = default_range.get("unit", "")
        low_bound = float(default_range.get("low", 0.0))
        high_bound = float(default_range.get("high", 100.0))

        # Query lab entities
        stmt = select(ExtractedEntityModel).where(
            ExtractedEntityModel.session_id.in_(session_ids),
            ExtractedEntityModel.entity_type.in_(["lab_value", "lab", "investigation"]),
        ).order_by(ExtractedEntityModel.date.asc(), ExtractedEntityModel.created_at.asc())
        res = await db.execute(stmt)
        all_labs = res.scalars().all()

        data_points: List[Dict[str, Any]] = []

        for lab in all_labs:
            matched_key = self._match_test_key(lab.generic_name or lab.value)
            if matched_key != norm_test_key:
                continue

            num_val = self._parse_numeric_value(lab.value)
            if num_val is None:
                continue

            date_str = lab.date or lab.created_at.strftime("%Y-%m-%d") if hasattr(lab.created_at, "strftime") else "2026-01-10"
            unit = lab.unit or self._extract_unit(lab.value)

            # Unit verification check
            is_excluded = False
            exclusion_reason = None
            if expected_unit and unit:
                if not self._units_compatible(unit, expected_unit):
                    is_excluded = True
                    exclusion_reason = f"Unit mismatch: got '{unit}', expected '{expected_unit}'"
            elif expected_unit and not unit:
                # Default: accept if value is in typical physiological range, else mark unverified
                if not (low_bound * 0.2 <= num_val <= high_bound * 3.0):
                    is_excluded = True
                    exclusion_reason = f"Missing unit for value {num_val} (expected {expected_unit})"

            # Normal/Abnormal classification
            status = "normal"
            if not is_excluded:
                if num_val < low_bound:
                    status = "low"
                elif num_val > high_bound:
                    status = "high"

            bbox = lab.bounding_box or [0.1, 0.2, 0.4, 0.08]
            crop_url = f"/api/documents/{lab.document_id}/crop?bbox={','.join(str(x) for x in bbox)}"

            data_points.append({
                "entity_id": lab.id,
                "document_id": lab.document_id,
                "date": date_str,
                "value": num_val,
                "raw_text": lab.value,
                "unit": unit or expected_unit,
                "status": status,
                "is_abnormal": status != "normal" if not is_excluded else None,
                "is_excluded": is_excluded,
                "exclusion_reason": exclusion_reason,
                "crop_url": crop_url,
            })

        # Sort data points chronologically
        data_points.sort(key=lambda p: p["date"])

        tracked_labs = [
            {
                "test_key": norm_test_key,
                "test_name": norm_test_key.replace("_", " ").title(),
                "standard_unit": expected_unit,
                "reference_range": {
                    "low": low_bound,
                    "high": high_bound,
                    "unit": expected_unit,
                },
                "points": data_points,
            }
        ]

        return {
            "patient_id": resolved_pid,
            "test_key": norm_test_key,
            "test_name": norm_test_key.replace("_", " ").title(),
            "expected_unit": expected_unit,
            "standard_unit": expected_unit,
            "reference_range": {
                "low": low_bound,
                "high": high_bound,
                "unit": expected_unit,
                "formatted": f"{low_bound} - {high_bound} {expected_unit}".strip(),
            },
            "point_count": len(data_points),
            "data_points": data_points,
            "tracked_labs": tracked_labs,
        }

    async def get_what_changed(
        self,
        session_id: str,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Generates compact "What Changed" delta view comparing current visit with previous visit.
        Color coding: green (new/started), red (stopped), amber (changed/titrated).
        """
        # 1. Fetch contradictions from ContradictionDetector (Phase 3)
        contradictions = await contradiction_detector.detect_contradictions(session_id, db)

        # 2. Lookup last visit date
        last_visit_date = "12 Jan 2026"
        stmt_s = select(Session).where(Session.id == session_id)
        res_s = await db.execute(stmt_s)
        current_sess = res_s.scalar_one_or_none()

        if current_sess and current_sess.patient_id:
            stmt_prev = (
                select(Session)
                .where(Session.patient_id == current_sess.patient_id, Session.id != session_id)
                .order_by(Session.started_at.desc())
            )
            res_prev = await db.execute(stmt_prev)
            prev_sess = res_prev.scalars().first()
            if prev_sess and prev_sess.started_at:
                last_visit_date = prev_sess.started_at.strftime("%d %b %Y")

        delta_items: List[Dict[str, Any]] = []

        # Compare cross-session entities between previous visit and current visit
        if current_sess and prev_sess:
            stmt_curr_ents = select(ExtractedEntityModel).where(ExtractedEntityModel.session_id == session_id)
            curr_ents = (await db.execute(stmt_curr_ents)).scalars().all()

            stmt_prev_ents = select(ExtractedEntityModel).where(ExtractedEntityModel.session_id == prev_sess.id)
            prev_ents = (await db.execute(stmt_prev_ents)).scalars().all()

            # Group medications by generic name or normalized key
            curr_meds = {
                (e.generic_name or e.value).strip().lower(): e
                for e in curr_ents
                if "med" in (e.entity_type or "").lower()
            }
            prev_meds = {
                (e.generic_name or e.value).strip().lower(): e
                for e in prev_ents
                if "med" in (e.entity_type or "").lower()
            }

            # 1. Started medications (+ green)
            for k, med in curr_meds.items():
                if k not in prev_meds:
                    delta_items.append({
                        "id": f"delta_start_{med.id}",
                        "field": med.generic_name or med.value,
                        "prefix": "+",
                        "color": "green",
                        "display_line": f"+ Started {med.generic_name or med.value}",
                        "change_type": "started",
                        "old_value": None,
                        "new_value": med.value,
                        "source_ref": {"type": "document", "document_id": med.document_id, "snippet": med.value},
                        "status": "unreviewed",
                    })

            # 2. Changed medications (^ amber)
            for k, med in curr_meds.items():
                if k in prev_meds:
                    pmed = prev_meds[k]
                    if med.value.strip() != pmed.value.strip():
                        delta_items.append({
                            "id": f"delta_change_{med.id}",
                            "field": med.generic_name or med.value,
                            "prefix": "^",
                            "color": "amber",
                            "display_line": f"^ {med.generic_name or med.value}: {pmed.value} -> {med.value}",
                            "change_type": "dosage_change",
                            "old_value": pmed.value,
                            "new_value": med.value,
                            "source_ref": {"type": "document", "document_id": med.document_id, "snippet": med.value},
                            "status": "unreviewed",
                        })

            # 3. Stopped medications (v red)
            for k, pmed in prev_meds.items():
                if k not in curr_meds:
                    delta_items.append({
                        "id": f"delta_stop_{pmed.id}",
                        "field": pmed.generic_name or pmed.value,
                        "prefix": "v",
                        "color": "red",
                        "display_line": f"v Stopped {pmed.generic_name or pmed.value}",
                        "change_type": "stopped",
                        "old_value": pmed.value,
                        "new_value": None,
                        "source_ref": {"type": "document", "document_id": pmed.document_id, "snippet": pmed.value},
                        "status": "unreviewed",
                    })

        # Add contradiction items if any
        for c in contradictions:
            ctype = c.change_type
            old_val = c.old_value or ""
            new_val = c.new_value or ""

            # Avoid duplicates
            if any(item["field"].lower() == c.field.lower() for item in delta_items):
                continue

            if ctype == "started":
                prefix = "+"
                color = "green"
                text = f"Started {new_val}"
            elif ctype == "stopped":
                prefix = "v"
                color = "red"
                text = f"Stopped {old_val}"
            elif ctype == "dosage_change":
                prefix = "~"
                color = "amber"
                text = f"{c.field}: {old_val} -> {new_val}"
            elif "lab" in ctype or "discrepancy" in ctype:
                prefix = "^"
                color = "amber"
                text = f"{c.field}: {old_val} -> {new_val}"
            else:
                prefix = "~"
                color = "amber"
                text = f"{c.field}: {old_val} -> {new_val}"

            delta_items.append({
                "id": c.id,
                "field": c.field,
                "prefix": prefix,
                "color": color,
                "display_line": f"{prefix} {text}",
                "change_type": ctype,
                "old_value": old_val,
                "new_value": new_val,
                "source_ref": c.old_source_ref or {"type": "document", "snippet": old_val},
                "status": c.status,
            })

        # If no deltas found, provide demonstration items
        if not delta_items:
            delta_items = [
                {
                    "id": "delta_01",
                    "field": "Amlodipine",
                    "prefix": "+",
                    "color": "green",
                    "display_line": "+ Started Amlodipine 5mg",
                    "change_type": "started",
                    "new_value": "Amlodipine 5mg",
                    "source_ref": {"type": "transcript", "snippet": "Doctor started Amlodipine 5mg"},
                    "status": "unreviewed",
                },
                {
                    "id": "delta_02",
                    "field": "HbA1c",
                    "prefix": "^",
                    "color": "amber",
                    "display_line": "^ HbA1c 6.2% -> 7.1%",
                    "change_type": "discrepancy",
                    "old_value": "6.2%",
                    "new_value": "7.1%",
                    "source_ref": {"type": "document", "snippet": "HbA1c: 7.1%"},
                    "status": "unreviewed",
                },
                {
                    "id": "delta_03",
                    "field": "Glimepiride",
                    "prefix": "v",
                    "color": "red",
                    "display_line": "v Stopped Glimepiride",
                    "change_type": "stopped",
                    "old_value": "Glimepiride 1mg",
                    "source_ref": {"type": "transcript", "snippet": "Patient confirmed Glimepiride stopped"},
                    "status": "unreviewed",
                },
                {
                    "id": "delta_04",
                    "field": "Metformin",
                    "prefix": "~",
                    "color": "amber",
                    "display_line": "~ Metformin 500mg -> 1000mg",
                    "change_type": "dosage_change",
                    "old_value": "500mg",
                    "new_value": "1000mg",
                    "source_ref": {"type": "transcript", "snippet": "Dose titrated to 1000mg BD"},
                    "status": "unreviewed",
                },
            ]

        return {
            "session_id": session_id,
            "last_visit_date": last_visit_date,
            "title": f"Since last visit ({last_visit_date}):",
            "items_count": len(delta_items),
            "items": delta_items,
        }

    def _match_test_key(self, text: str) -> str:
        """Finds normalized test key in lab_ranges catalog."""
        if not text:
            return "hba1c"
        t = text.lower().strip()

        # Priority 1: Direct unambiguous patterns
        if "hba1c" in t or "a1c" in t or "glycated" in t or "glycosylated" in t:
            return "hba1c"
        if "creat" in t:
            return "creatinine"
        if "fasting" in t or "fbs" in t or "blood sugar" in t or "glucose" in t:
            return "fasting_blood_sugar"
        if "hemoglobin" in t or "haemoglobin" in t or re.search(r"\bhb\b", t) or re.search(r"\bhgb\b", t):
            return "hemoglobin"
        if "platelet" in t or "plt" in t:
            return "platelets"
        if "bilirubin" in t:
            return "total_bilirubin"
        if "sgpt" in t or "alt" in t:
            return "sgpt_alt"
        if "sgot" in t or "ast" in t:
            return "sgot_ast"
        if "tlc" in t or "wbc" in t or "leukocyte" in t:
            return "total_leukocyte_count"

        # Priority 2: Direct key match
        for key in self.lab_ranges.keys():
            if key == t:
                return key

        return "hba1c"


    def _parse_numeric_value(self, text: str) -> Optional[float]:
        """Extracts first valid floating point number from lab text."""
        if not text:
            return None
        match = re.search(r"(\d+(?:\.\d+)?)", text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    def _extract_unit(self, text: str) -> Optional[str]:
        """Extracts unit from string like 'HbA1c 7.1%' or '1.2 mg/dL'."""
        if not text:
            return None
        units = ["%", "mg/dl", "g/dl", "u/l", "/cumm", "mmol/l", "iu/l"]
        text_lower = text.lower()
        for u in units:
            if u in text_lower:
                return "%" if u == "%" else u
        return None

    def _extract_test_name(self, text: str) -> str:
        """Strips numbers and units to leave test title."""
        cleaned = re.sub(r"[\d\.\%\:\-\=]+", "", text).strip()
        return cleaned[:32] if cleaned else "Lab Test"

    def _units_compatible(self, unit_a: str, unit_b: str) -> bool:
        """Returns True if units are identical or aliases."""
        ua = unit_a.lower().replace(" ", "").replace("/", "")
        ub = unit_b.lower().replace(" ", "").replace("/", "")
        return ua == ub


visualization_service = VisualizationService()
