"""
Polypharmacy and Drug-Drug Interaction Detector
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Features:
1. Normalizes Indian brand names and combination formulations to generic active molecules using indian_drug_map.json
2. Detects duplicate active ingredients across distinct therapies (e.g. Dolo 650 + Calpol 500 -> both Paracetamol)
   while ensuring a single therapy mention is never double-counted as a duplicate of itself
3. Word-boundary negation check preserving legitimate molecules like 'atenolol'
4. Detects dangerous drug-drug interactions (e.g. Warfarin + Aspirin -> increased bleeding)
5. Structured status reporting: 'completed_with_alerts', 'completed_without_alerts', or 'incomplete'
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

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
    status: str = "incomplete"  # "completed_with_alerts" | "completed_without_alerts" | "incomplete"
    medications_detected: List[str] = Field(default_factory=list)
    duplicates: List[DrugDuplicateAlert] = Field(default_factory=list)
    interactions: List[DrugInteractionAlert] = Field(default_factory=list)
    alerts: List[dict] = Field(default_factory=list)
    alert_count: int = 0


# Strict word-boundary negation expressions: must not match substrings inside drug names (e.g. 'atenolol')
WHOLE_NEGATION_REGEX = re.compile(
    r"^\s*(no|not|none|nothing|denies|stopped|discontinued|off|never|nil|na|बंद|नहीं)\s*$",
    re.IGNORECASE
)
NEGATION_PHRASE_REGEX = re.compile(
    r"\b(no medications|no meds|no drugs|no pills|कोई दवा नहीं|दवा नहीं लेते|all discontinued|not taking any)\b",
    re.IGNORECASE
)


class PolypharmacyDetector:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or (Path(__file__).resolve().parent.parent.parent / "data")
        self.brand_map: Dict[str, Dict[str, str]] = {}
        self.interactions: List[Dict[str, str]] = []
        self._load_data()

    def _load_data(self) -> None:
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

    def normalize_single_molecule(self, raw_part: str) -> Tuple[str, str]:
        """
        Normalizes a single molecule or brand name to (generic_name, clean_display_name).
        Safely handles None or empty input.
        """
        if not raw_part:
            return "", ""

        clean = raw_part.lower().strip()
        # Strip common prescription dosage forms and frequencies
        clean = re.sub(r"\b(tab|cap|tablet|capsule|inj|injection|syp|syrup|od|bd|tds|qid|sos|hs|mg|mcg|gm|g)\b", " ", clean)
        clean = re.sub(r"[^\w\s]", " ", clean)
        clean = " ".join(clean.split())

        if not clean:
            return "", raw_part.strip()

        # 1. Match in brand map (check longer brand strings first)
        for brand in sorted(self.brand_map.keys(), key=len, reverse=True):
            pattern = r"\b" + re.escape(brand) + r"\b"
            if re.search(pattern, clean):
                info = self.brand_map[brand]
                gen = info.get("generic", brand)
                return (gen.lower() if gen else brand.lower()), raw_part.strip()

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
            "contrast_dye", "digoxin", "amiodarone", "sildenafil", "nitroglycerin",
            "glimepiride", "gliclazide", "glipizide", "vildagliptin", "sitagliptin"
        ]
        for gen in known_generics:
            pattern = r"\b" + re.escape(gen) + r"\b"
            if re.search(pattern, clean):
                return gen, raw_part.strip()

        # Fallback to first non-numeric word
        tokens = clean.split()
        fallback_gen = tokens[0] if tokens and not tokens[0].isdigit() else clean
        return fallback_gen, raw_part.strip()

    def normalize_drug(self, raw_name: str) -> List[Tuple[str, str]]:
        """
        Takes raw string, splits combination formulations (e.g. 'Metformin + Glimepiride'),
        and returns a list of (generic_name, clean_display_name) tuples for each active ingredient.
        """
        if not raw_name:
            return []

        # Check for combination markers: '+', '/', '&', or ' and '
        sub_parts = re.split(r"[\+/&]|\band\b", raw_name, flags=re.IGNORECASE)
        results = []
        for part in sub_parts:
            part_str = part.strip()
            if len(part_str) >= 2:
                gen, disp = self.normalize_single_molecule(part_str)
                if gen:
                    results.append((gen, disp))

        if not results:
            gen, disp = self.normalize_single_molecule(raw_name)
            if gen:
                results.append((gen, disp))

        return results

    def analyze_medication_list(self, raw_medications: List[str], session_id: str = "unknown") -> PolypharmacyReport:
        """
        Analyzes a list of distinct medication occurrences for duplicate active molecules
        and dangerous drug-drug interactions.
        """
        report = PolypharmacyReport(session_id=session_id)
        if not raw_medications:
            report.status = "incomplete"
            return report

        # Filter out empty or pure negation entries
        clean_inputs: List[str] = []
        for raw_med in raw_medications:
            if not raw_med:
                continue
            trimmed = raw_med.strip()
            if len(trimmed) < 2:
                continue
            if WHOLE_NEGATION_REGEX.match(trimmed) or NEGATION_PHRASE_REGEX.search(trimmed):
                continue
            clean_inputs.append(trimmed)

        if not clean_inputs:
            report.status = "incomplete"
            return report

        # Map generic -> set of distinct therapy names
        generic_to_raws: Dict[str, Set[str]] = {}
        detected_meds: List[str] = []

        # Deduplicate identical raw entries first so repeats of the same prescription line aren't duplicates
        unique_raw_inputs = list(dict.fromkeys(clean_inputs))

        for raw_med in unique_raw_inputs:
            molecules = self.normalize_drug(raw_med)
            if not molecules:
                continue

            for generic, display in molecules:
                if not generic:
                    continue
                if display not in detected_meds:
                    detected_meds.append(display)

                if generic not in generic_to_raws:
                    generic_to_raws[generic] = set()
                generic_to_raws[generic].add(raw_med)

        report.medications_detected = detected_meds

        # 1. Detect Duplicate Active Ingredients
        # Trigger duplicate ONLY if 2 or more distinct therapy occurrences contain the same generic molecule
        for generic, raws_set in generic_to_raws.items():
            if len(raws_set) > 1:
                display_generic = generic.capitalize()
                raws_list = sorted(list(raws_set))
                raws_str = ", ".join(raws_list)
                alert_msg = f"Possible duplicate: both contain {display_generic} ({raws_str})"
                report.duplicates.append(
                    DrugDuplicateAlert(
                        generic=generic,
                        matched_medications=raws_list,
                        message=alert_msg,
                        severity="high",
                    )
                )

        # 2. Detect Drug-Drug Interactions
        active_generics = set(generic_to_raws.keys())
        for interaction in self.interactions:
            d_a = interaction.get("drug_a", "").lower()
            d_b = interaction.get("drug_b", "").lower()

            if d_a in active_generics and d_b in active_generics and d_a != d_b:
                raws_a = sorted(list(generic_to_raws[d_a]))
                raws_b = sorted(list(generic_to_raws[d_b]))
                pair_meds = [raws_a[0], raws_b[0]]

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
                )

        # 3. Populate unified alerts list
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

        # 4. Status determination
        if report.alert_count > 0:
            report.status = "completed_with_alerts"
        elif detected_meds:
            report.status = "completed_without_alerts"
        else:
            report.status = "incomplete"

        return report

    async def detect_polypharmacy(self, session_id: str, db: AsyncSession) -> PolypharmacyReport:
        """
        Extracts medications from both interview transcripts and document extracted_entities,
        then runs polypharmacy and drug interaction checks.
        Ensures each entity represents exactly one therapy occurrence.
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
            # One therapy occurrence per entity: prefer full prescribed value, fallback to generic
            val = ent.value or ent.generic_name
            if val and val.strip():
                med_strings.append(val.strip())

        # 2. Fetch from interview_transcripts table (Module A patient answers)
        stmt_t = select(InterviewTranscript).where(
            InterviewTranscript.session_id == session_id,
            InterviewTranscript.node_name.in_(["medications", "pmh", "allergies"]),
        )
        res_t = await db.execute(stmt_t)
        transcripts = res_t.scalars().all()
        for t in transcripts:
            if t.answer_text:
                # Split comma/newline/semicolon separated lines
                parts = re.split(r"[,;\n]+", t.answer_text)
                for p in parts:
                    clean_p = p.strip()
                    if clean_p:
                        # Skip pure negation expressions without deleting words like 'atenolol'
                        if WHOLE_NEGATION_REGEX.match(clean_p) or NEGATION_PHRASE_REGEX.search(clean_p):
                            continue
                        med_strings.append(clean_p)

        return self.analyze_medication_list(med_strings, session_id=session_id)


polypharmacy_detector = PolypharmacyDetector()
