"""
Polypharmacy and Drug-Drug Interaction Detector
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Features:
1. Normalizes Indian brand names to generic active molecules using indian_drug_map.json
2. Detects duplicate active ingredients (e.g. Dolo 650 + Calpol 500 -> both Paracetamol)
3. Detects dangerous drug-drug interactions (e.g. Warfarin + Ecosprin -> increased bleeding)
4. Integrates with interview transcripts and extracted document entities
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Tuple

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import ExtractedEntityModel, InterviewTranscript

logger = logging.getLogger("medikiosk.polypharmacy")


class DrugDuplicateAlert(BaseModel):
    generic: str
    matched_medications: List[str]
    message: str
    severity: str = "high"


class DrugInteractionAlert(BaseModel):
    drug_a: str
    drug_b: str
    matched_medications: List[str]
    severity: str = "high"
    note: str
    message: str


class PolypharmacyReport(BaseModel):
    session_id: str
    medications_detected: List[str] = Field(default_factory=list)
    duplicates: List[DrugDuplicateAlert] = Field(default_factory=list)
    interactions: List[DrugInteractionAlert] = Field(default_factory=list)
    alerts: List[dict] = Field(default_factory=list)
    alert_count: int = 0


class PolypharmacyDetector:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or settings.DATA_DIR
        self.brand_map: Dict[str, Dict[str, str]] = {}
        self.interactions: List[Dict[str, str]] = []
        self._load_data()

    def _load_data(self) -> None:
        # Load brand-to-generic catalog
        brand_path = self.data_dir / "indian_drug_map.json"
        if brand_path.exists():
            try:
                with open(brand_path, encoding="utf-8") as f:
                    self.brand_map = json.load(f)
                logger.info(f"Loaded {len(self.brand_map)} Indian drug mappings.")
            except Exception as e:
                logger.error(f"Failed to load indian_drug_map.json: {e}")
        else:
            logger.warning(f"indian_drug_map.json not found at {brand_path}")

        # Load interactions catalog
        interactions_path = self.data_dir / "drug_interactions.json"
        if interactions_path.exists():
            try:
                with open(interactions_path, encoding="utf-8") as f:
                    self.interactions = json.load(f)
                logger.info(f"Loaded {len(self.interactions)} drug interactions.")
            except Exception as e:
                logger.error(f"Failed to load drug_interactions.json: {e}")
        else:
            logger.warning(f"drug_interactions.json not found at {interactions_path}")

    def normalize_drug(self, raw_name: str) -> Tuple[str, str]:
        """
        Takes raw string (e.g. 'Tab Dolo 650mg BD' or 'Ecosprin 75')
        Returns (generic_name, clean_display_name).
        """
        if not raw_name:
            return "", ""

        clean = raw_name.lower().strip()
        # Strip common prescription prefixes and dose frequencies
        clean = re.sub(r"\b(tab|cap|tablet|capsule|inj|injection|syp|syrup|od|bd|tds|qid|sos|hs|mg|mcg|gm|g)\b", " ", clean)
        clean = re.sub(r"[^\w\s]", " ", clean)
        clean = " ".join(clean.split())

        # 1. Exact or substring match in brand map
        for brand, info in self.brand_map.items():
            pattern = r"\b" + re.escape(brand) + r"\b"
            if re.search(pattern, clean):
                return info["generic"].lower(), raw_name.strip()

        # 2. Known generic molecules direct check
        known_generics = [
            "paracetamol", "acetaminophen", "aspirin", "clopidogrel", "warfarin",
            "metformin", "telmisartan", "amlodipine", "atorvastatin", "rosuvastatin",
            "pantoprazole", "omeprazole", "rabeprazole", "esomeprazole", "ranitidine",
            "ibuprofen", "diclofenac", "aceclofenac", "tramadol", "methotrexate",
            "amoxicillin", "azithromycin", "ciprofloxacin", "ofloxacin", "metronidazole",
            "spironolactone", "ramipril", "enalapril", "losartan", "atenolol", "metoprolol",
            "escitalopram", "fluoxetine", "sertraline", "theophylline", "salbutamol",
            "fexofenadine", "cetirizine", "levocetirizine", "montelukast", "contrast",
            "contrast_dye", "digoxin", "amiodarone", "sildenafil", "nitroglycerin"
        ]
        for gen in known_generics:
            pattern = r"\b" + re.escape(gen) + r"\b"
            if re.search(pattern, clean):
                return gen, raw_name.strip()

        # Fallback: return cleaned word if unrecognized
        return clean.split()[0] if clean else "", raw_name.strip()

    def analyze_medication_list(self, raw_medications: List[str], session_id: str = "unknown") -> PolypharmacyReport:
        """
        Analyzes a list of medication names for duplicate molecules and dangerous drug interactions.
        """
        report = PolypharmacyReport(session_id=session_id)
        if not raw_medications:
            return report

        # Map generic -> list of matched raw drug names
        generic_to_raws: Dict[str, List[str]] = {}
        detected_meds: List[str] = []

        for raw_med in raw_medications:
            if not raw_med or len(raw_med.strip()) < 2:
                continue
            generic, display = self.normalize_drug(raw_med)
            if not generic:
                continue

            detected_meds.append(display)
            if generic not in generic_to_raws:
                generic_to_raws[generic] = []
            if display not in generic_to_raws[generic]:
                generic_to_raws[generic].append(display)

        report.medications_detected = detected_meds

        # 1. Detect Duplicate Active Ingredients (e.g. Dolo 650 and Calpol 500)
        for generic, raws in generic_to_raws.items():
            if len(raws) > 1:
                display_generic = generic.capitalize()
                raws_str = ", ".join(raws)
                alert_msg = f"Possible duplicate: both are {display_generic} ({raws_str})"
                report.duplicates.append(
                    DrugDuplicateAlert(
                        generic=generic,
                        matched_medications=raws,
                        message=alert_msg,
                        severity="high",
                    )
                )

        # 2. Detect Drug-Drug Interactions
        active_generics = list(generic_to_raws.keys())
        for interaction in self.interactions:
            d_a = interaction["drug_a"].lower()
            d_b = interaction["drug_b"].lower()

            if d_a in active_generics and d_b in active_generics and d_a != d_b:
                raws_a = generic_to_raws[d_a]
                raws_b = generic_to_raws[d_b]
                pair_meds = [raws_a[0], raws_b[0]]

                # Clean friendly note message
                note = interaction.get("note", f"Risk between {d_a} and {d_b}")
                if "increased bleeding" in note.lower():
                    msg = f"Interaction risk: increased bleeding ({pair_meds[0]} + {pair_meds[1]})"
                elif "lactic acidosis" in note.lower():
                    msg = f"Interaction risk: lactic acidosis ({pair_meds[0]} + {pair_meds[1]})"
                else:
                    msg = f"Interaction risk: {note} ({pair_meds[0]} + {pair_meds[1]})"

                report.interactions.append(
                    DrugInteractionAlert(
                        drug_a=d_a,
                        drug_b=d_b,
                        matched_medications=pair_meds,
                        severity=interaction.get("severity", "high"),
                        note=note,
                        message=msg,
                    )
        # 3. Populate unified alerts list for Doctor UI and Checkpoint 3 integration
        for d in report.duplicates:
            report.alerts.append({
                "type": "brand_generic_duplicate",
                "drug_a": d.generic,
                "drug_b": None,
                "severity": d.severity,
                "message": d.message,
            })
        for i in report.interactions:
            report.alerts.append({
                "type": "drug_interaction",
                "drug_a": i.drug_a,
                "drug_b": i.drug_b,
                "severity": i.severity,
                "message": i.message,
            })
        report.alert_count = len(report.alerts)

        return report

    async def detect_polypharmacy(self, session_id: str, db: AsyncSession) -> PolypharmacyReport:
        """
        Extracts medications from both interview transcripts and document extracted_entities,
        then runs polypharmacy and drug interaction checks.
        """
        med_strings: List[str] = []

        # 1. Fetch from extracted_entities table (Module B documents)
        stmt_e = select(ExtractedEntityModel).where(
            ExtractedEntityModel.session_id == session_id,
            ExtractedEntityModel.entity_type == "medication",
        )
        res_e = await db.execute(stmt_e)
        entities = res_e.scalars().all()
        for ent in entities:
            if ent.generic_name:
                med_strings.append(ent.generic_name)
            if ent.value:
                med_strings.append(ent.value)

        # 2. Fetch from interview_transcripts table (Module A patient answers)
        stmt_t = select(InterviewTranscript).where(
            InterviewTranscript.session_id == session_id,
            InterviewTranscript.node_name.in_(["medications", "pmh", "allergies"]),
        )
        res_t = await db.execute(stmt_t)
        transcripts = res_t.scalars().all()
        for t in transcripts:
            if t.answer_text:
                # Split possible commas or newlines
                parts = re.split(r"[,;\n\+]+", t.answer_text)
                for p in parts:
                    clean_p = p.strip()
                    if clean_p and not any(neg in clean_p.lower() for neg in ["नहीं", "none", "no", "nothing"]):
                        med_strings.append(clean_p)

        return self.analyze_medication_list(med_strings, session_id=session_id)


polypharmacy_detector = PolypharmacyDetector()
