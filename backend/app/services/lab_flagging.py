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
        """
        Extract numerical reading and any embedded unit from a value string.
        Examples:
          "14.5 g/dL" -> (14.5, "g/dL")
          "5.8 %"     -> (5.8, "%")
          "38 U/L"    -> (38.0, "U/L")
        """
        if not value_str:
            return None, None

        # Look for leading numbers (including decimals)
        match = re.search(r"([><=]?\s*(\d+(?:\.\d+)?))\s*([a-zA-Z%\/\^]+)?", value_str.strip())
        if not match:
            return None, None

        num_part = match.group(2)
        unit_part = match.group(3)

        try:
            val = float(num_part)
            return val, unit_part
        except ValueError:
            return None, None

    def _normalize_unit(self, unit: str | None) -> str:
        if not unit:
            return ""
        clean = unit.strip().lower()
        clean = clean.replace(" ", "")
        clean = clean.replace("cu.mm", "cumm").replace("cells/cumm", "/cumm").replace("cells/ul", "/cumm")
        return clean

    def evaluate_lab_value(
        self,
        test_name: str,
        value_text: str,
        unit: str | None = None,
        gender: str = "male",
    ) -> Tuple[bool | None, str | None]:
        """
        Evaluate if a lab entity is abnormal.

        Returns:
            (is_abnormal, reference_range_string)
            is_abnormal:
              - True: verified outside normal bounds
              - False: verified within normal bounds
              - None: unverified (e.g. unknown test or unit mismatch)
        """
        key = self._match_test_key(test_name)
        if not key or key not in self.ranges:
            return None, None

        config = self.ranges[key]
        num_val, embedded_unit = self._extract_numeric_value(value_text)
        if num_val is None:
            return None, None

        extracted_unit = unit or embedded_unit or ""

        # Select target demographic range
        gender_key = gender.lower() if gender else "default"
        spec = config.get(gender_key) or config.get("normal") or config.get("default")
        if not spec:
            return None, None

        ref_unit = spec.get("unit", "")
        low = spec.get("low", 0.0)
        high = spec.get("high", float("inf"))
        ref_range_str = f"{low} - {high} {ref_unit}".strip()

        # Strict Unit Mismatch Defense:
        # If an extracted unit is present, compare against reference unit
        if extracted_unit:
            norm_extracted = self._normalize_unit(extracted_unit)
            norm_ref = self._normalize_unit(ref_unit)
            if norm_extracted and norm_ref and norm_extracted != norm_ref:
                logger.info(
                    f"Lab unit mismatch for {key}: extracted '{extracted_unit}', "
                    f"expected '{ref_unit}'. Marking is_abnormal=None"
                )
                return None, ref_range_str

        # Compare value
        is_abnormal = bool(num_val < low or num_val > high)
        return is_abnormal, ref_range_str


lab_flagger = LabFlaggingEngine()
