"""
Clinical Laboratory Value Normalization and Abnormal Flagging Engine
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Compares extracted lab test values against standard clinical reference ranges.
On unit mismatch between extracted and reference units, returns is_abnormal = None
(cannot verify) rather than guessing.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Tuple

logger = logging.getLogger("medikiosk.lab_flagging")

RANGES_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "lab_ranges.json"


from app.services.lab_parser import lab_parser


class LabFlaggingEngine:
    """Evaluates lab values against Indian OPD clinical normal ranges."""

    def __init__(self, ranges_path: Path = RANGES_FILE):
        self.ranges: Dict[str, Any] = {}
        self._load_ranges(ranges_path)

    def _load_ranges(self, ranges_path: Path):
        try:
            if ranges_path.exists():
                with open(ranges_path, encoding="utf-8") as f:
                    self.ranges = json.load(f)
            else:
                logger.warning(f"Lab ranges file not found at {ranges_path}")
        except Exception as e:
            logger.error(f"Failed to load lab reference ranges: {e}")
            self.ranges = {}

    def _match_test_key(self, test_name: str) -> str | None:
        """Find the canonical key in lab_ranges for a given test name or alias."""
        clean = test_name.strip().lower()
        clean_sub = re.sub(r"[\(\)\[\]\-_\/:]", " ", clean)
        words = clean_sub.split()

        # Pass 1: Exact matches (keys or aliases)
        for key, config in self.ranges.items():
            if key == clean or key.replace("_", " ") == clean_sub:
                return key
            aliases = [a.lower() for a in config.get("aliases", [])]
            if clean in aliases or clean_sub in aliases:
                return key

        # Pass 2: Whole-word boundary matches (prioritize longer aliases)
        candidates = []
        for key, config in self.ranges.items():
            key_clean = key.replace("_", " ")
            if re.search(rf"\b{re.escape(key_clean)}\b", clean_sub):
                candidates.append((len(key_clean), key))
            for alias in config.get("aliases", []):
                alias_clean = alias.lower()
                if re.search(rf"\b{re.escape(alias_clean)}\b", clean_sub) or any(w == alias_clean for w in words):
                    candidates.append((len(alias_clean), key))

        if candidates:
            # Sort by match length descending so 'hba1c' matches before 'hb'
            candidates.sort(key=lambda c: c[0], reverse=True)
            return candidates[0][1]

        return None

    def _extract_numeric_value(self, value_str: str) -> Tuple[float | None, str | None]:
        """Delegates to StructuredLabParser."""
        parsed = lab_parser.parse(value_str)
        return parsed.effective_value, parsed.unit

    def _normalize_unit(self, unit: str | None) -> str:
        return lab_parser.normalize_unit(unit) or ""

    def evaluate_lab_value(
        self,
        test_name: str,
        value_text: str,
        unit: str | None = None,
        gender: str = "default",
    ) -> Tuple[bool | None, str | None]:
        """
        Evaluate if a lab entity is abnormal.

        Returns:
            (is_abnormal, reference_range_string)
            is_abnormal:
              - True: verified outside normal bounds
              - False: verified within normal bounds
              - None: unverified (e.g. unknown test, unit mismatch, missing unit)
        """
        # Parse value text using structured lab parser
        parsed = lab_parser.parse(value_text, test_name=test_name, explicit_unit=unit)
        if parsed.status == "cannot_verify" or parsed.effective_value is None:
            return None, None

        key = parsed.test_key or self._match_test_key(test_name)
        if not key or key not in self.ranges:
            return None, None

        config = self.ranges[key]

        # Select target demographic range explicitly
        gender_norm = (gender or "default").lower().strip()
        if gender_norm in ("female", "f", "woman", "girl"):
            demog_key = "female"
        elif gender_norm in ("male", "m", "man", "boy"):
            demog_key = "male"
        else:
            demog_key = "default"

        spec = config.get(demog_key) or config.get("normal") or config.get("default")
        if not spec:
            return None, None

        ref_unit = spec.get("unit", "")
        low = float(spec.get("low", 0.0))
        high = float(spec.get("high", float("inf")))
        ref_range_str = f"{low} - {high} {ref_unit}".strip()

        # Strict Unit Mismatch Defense:
        # If an extracted unit is present, compare against reference unit
        extracted_unit = parsed.unit
        if extracted_unit:
            norm_extracted = self._normalize_unit(extracted_unit)
            norm_ref = self._normalize_unit(ref_unit)
            if norm_extracted and norm_ref and norm_extracted != norm_ref:
                logger.info(
                    f"Lab unit mismatch for {key}: extracted '{extracted_unit}' ({norm_extracted}), "
                    f"expected '{ref_unit}' ({norm_ref}). Marking is_abnormal=None"
                )
                return None, ref_range_str
        elif ref_unit:
            # Unit missing on a test that has expected units: unverified
            logger.info(f"Missing required unit '{ref_unit}' for lab test {key}. Marking unverified.")
            return None, ref_range_str

        num_val = parsed.effective_value

        # Comparator handling: <, <=, >, >=
        if parsed.comparator in ("<", "<="):
            if num_val <= high:
                # e.g. < 5.7% for HbA1c where normal is <= 5.7% -> verified normal
                return False, ref_range_str
            else:
                return True, ref_range_str
        elif parsed.comparator in (">", ">="):
            if num_val > high:
                # e.g. > 10.0% for HbA1c -> verified abnormal high
                return True, ref_range_str
            elif num_val >= low:
                return False, ref_range_str
            else:
                return None, ref_range_str

        # Standard numeric evaluation
        is_abnormal = bool(num_val < low or num_val > high)
        return is_abnormal, ref_range_str


lab_flagger = LabFlaggingEngine()
