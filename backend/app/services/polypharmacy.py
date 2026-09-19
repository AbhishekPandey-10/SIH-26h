"""
Polypharmacy & Drug-Drug Interaction Detection Service (Harmonized Shim)
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Delegates to canonical PolypharmacyDetector to maintain a single source of truth,
eliminate duplicate logic, and remove all demo/fallback clinical fabrication.
"""

import logging
from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.polypharmacy_detector import (
    PolypharmacyReport,
    polypharmacy_detector,
)
from app.shared.schemas import PolypharmacyAlert

logger = logging.getLogger("medikiosk.polypharmacy")


class PolypharmacyService:
    """
    Service wrapper around PolypharmacyDetector providing backwards compatibility
    with PolypharmacyAlert return types.
    """

    def __init__(self):
        self.detector = polypharmacy_detector

    @property
    def brand_map(self) -> Dict[str, Dict[str, Any]]:
        return self.detector.brand_map

    @property
    def interaction_rules(self) -> List[Dict[str, Any]]:
        return self.detector.interactions

    def normalize_medication(self, raw_name: str) -> Dict[str, str]:
        """
        Normalizes medication name to brand, generic, and raw format.
        """
        molecules = self.detector.normalize_drug(raw_name)
        if molecules:
            gen, disp = molecules[0]
            return {
                "raw": raw_name,
                "brand": disp,
                "generic": gen,
            }
        return {
            "raw": raw_name,
            "brand": raw_name,
            "generic": raw_name.lower(),
        }

    async def detect_polypharmacy_alerts(
        self,
        session_id: str,
        db: AsyncSession,
    ) -> List[PolypharmacyAlert]:
        """
        Detects duplicate molecules and dangerous interactions.
        Zero runtime fabrication: returns empty list if no medications exist in DB.
        """
        report: PolypharmacyReport = await self.detector.detect_polypharmacy(session_id, db)
        return self._report_to_alerts(report)

    def analyze_medication_list(self, med_strings: List[str]) -> List[PolypharmacyAlert]:
        """
        Analyzes a list of medication names and returns canonical PolypharmacyAlert models.
        """
        report: PolypharmacyReport = self.detector.analyze_medication_list(med_strings)
        return self._report_to_alerts(report)

    def _report_to_alerts(self, report: PolypharmacyReport) -> List[PolypharmacyAlert]:
        alerts: List[PolypharmacyAlert] = []
        for d in report.duplicates:
            m1 = d.matched_medications[0] if d.matched_medications else d.generic
            m2 = d.matched_medications[1] if len(d.matched_medications) > 1 else d.generic
            alerts.append(
                PolypharmacyAlert(
                    type="brand_generic_duplicate",
                    drug_a=m1,
                    drug_b=m2,
                    severity=d.severity,
                    message=d.message,
                )
            )
        for i in report.interactions:
            m1 = i.matched_medications[0] if i.matched_medications else i.drug_a
            m2 = i.matched_medications[1] if len(i.matched_medications) > 1 else i.drug_b
            alerts.append(
                PolypharmacyAlert(
                    type="drug_interaction",
                    drug_a=m1,
                    drug_b=m2,
                    severity=i.severity,
                    message=i.message,
                )
            )
        return alerts


polypharmacy_service = PolypharmacyService()
