"""
Structured Clinical Lab Quantity Parser
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Extracts test identifier, numeric value, comparator, unit, multiplier,
and evaluation status from raw clinical lab text without suffering from test-name
digit collisions (e.g. HbA1c: 7.1% -> value: 7.1, not 1) or multiplier omissions
(e.g. Platelets 1.8 Lakhs /cumm -> 180,000 /cumm).
"""

import logging
import re
from dataclasses import dataclass
from typing import Literal, Optional, Tuple

logger = logging.getLogger("medikiosk.lab_parser")

# Recognized Indian & International laboratory test name markers/aliases
KNOWN_TEST_PATTERNS = [
    (r"\b(hba1c|glycosylated\s+hemoglobin|glycated\s+hemoglobin|a1c)\b", "hba1c"),
    (r"\b(serum\s+creatinine|sr\.\s*creatinine|sr\s+creatinine|creatinine|creat)\b", "creatinine"),
    (r"\b(hemoglobin|haemoglobin|hgb|\bhb\b)\b", "hemoglobin"),
    (r"\b(platelet\s+count|platelets|plt)\b", "platelets"),
    (r"\b(total\s+leukocyte\s+count|total\s+wbc|tlc|\bwbc\b)\b", "total_leukocyte_count"),
    (r"\b(sgpt\s*\(alt\)|sgpt|alt|alanine\s+aminotransferase|alanine\s+transaminase)\b", "sgpt_alt"),
    (r"\b(sgot\s*\(ast\)|sgot|ast|aspartate\s+aminotransferase)\b", "sgot_ast"),
    (r"\b(fasting\s+blood\s+sugar|fasting\s+glucose|blood\s+glucose\s+fasting|fbs)\b", "fasting_blood_sugar"),
    (r"\b(total\s+bilirubin|serum\s+bilirubin|bilirubin\s+total|bilirubin)\b", "total_bilirubin"),
]

# Multiplier mapping for Indian English clinical notes
MULTIPLIERS = {
    "lakhs": 100_000.0,
    "lakh": 100_000.0,
    "lacs": 100_000.0,
    "lac": 100_000.0,
    "k": 1_000.0,
    "thousand": 1_000.0,
    "million": 1_000_000.0,
}

# Unit normalizations
UNIT_NORMALIZATIONS = {
    "cu.mm": "/cumm",
    "cells/cumm": "/cumm",
    "cells/ul": "/cumm",
    "cells/µl": "/cumm",
    "/ul": "/cumm",
    "cumm": "/cumm",
    "g/dl": "g/dL",
    "gm/dl": "g/dL",
    "mg/dl": "mg/dL",
    "u/l": "U/L",
    "iu/l": "U/L",
    "%": "%",
    "percent": "%",
    "percentage": "%",
    "mmol/l": "mmol/L",
    "pg/ml": "pg/mL",
    "u/ml": "U/mL",
    "cells/ul": "cells/uL",
}


class ParseStatus:
    OK = "verified"
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    CANNOT_VERIFY = "cannot_verify"
    EMPTY = "cannot_verify"


@dataclass
class ParsedLabQuantity:
    test_key: Optional[str]
    test_name: str
    numeric_value: Optional[float]
    effective_value: Optional[float]  # numeric_value * multiplier
    comparator: Optional[str]  # "<", "<=", ">", ">=", "=", None
    unit: Optional[str]
    multiplier: float
    raw_text: str
    status: str  # "verified", "unverified", "cannot_verify"
    rejection_reason: Optional[str] = None


class StructuredLabParser:
    """Robust parser for lab quantities with test-name isolation and unit normalization."""

    @classmethod
    def normalize_unit(cls, unit: Optional[str]) -> Optional[str]:
        if not unit:
            return None
        clean = unit.strip().lower()
        clean = clean.replace(" ", "")
        return UNIT_NORMALIZATIONS.get(clean, unit.strip())

    @classmethod
    def isolate_test_and_value(cls, text: str, given_test_name: Optional[str] = None) -> Tuple[Optional[str], str, str]:
        """
        Separates the test name from the value portion of a text snippet.
        Returns: (test_key, canonical_test_name, value_portion)
        """
        raw = text.strip()
        matched_key = None
        matched_name = given_test_name or "Lab Test"
        value_portion = raw

        # 1. Match against known test patterns in text
        for pattern, key in KNOWN_TEST_PATTERNS:
            m = re.search(pattern, raw, re.IGNORECASE)
            if m:
                matched_key = key
                matched_name = key.replace("_", " ").title()
                # Strip matched test name and any delimiter (':', '-', '=')
                prefix_end = m.end()
                remainder = raw[prefix_end:].lstrip(": -=#\t")
                if remainder:
                    value_portion = remainder
                break

        # 2. If given_test_name provided and no match in text, use given_test_name
        if not matched_key and given_test_name:
            for pattern, key in KNOWN_TEST_PATTERNS:
                if re.search(pattern, given_test_name, re.IGNORECASE):
                    matched_key = key
                    matched_name = key.replace("_", " ").title()
                    break

        # 3. Strip given_test_name if present as a prefix
        if given_test_name:
            prefix_pat = rf"^\s*{re.escape(given_test_name)}\s*[:\-=#\t]*\s*"
            m_prefix = re.search(prefix_pat, value_portion, re.IGNORECASE)
            if m_prefix:
                remainder = value_portion[m_prefix.end():]
                if remainder:
                    value_portion = remainder

        # 4. If value_portion contains a colon separating label from value (e.g. "CA-125: 18.5")
        if ":" in value_portion:
            parts = value_portion.split(":", 1)
            # If the right-hand part has digits, the left-hand part is a label
            if re.search(r"\d", parts[1]):
                if not matched_key and not given_test_name:
                    matched_name = parts[0].strip()
                value_portion = parts[1].strip()

        return matched_key, matched_name, value_portion

    @classmethod
    def parse(
        cls,
        text: str,
        test_name: Optional[str] = None,
        explicit_unit: Optional[str] = None,
    ) -> ParsedLabQuantity:
        """
        Parses a lab statement or value string into a structured lab quantity.
        """
        if not text or not text.strip():
            return ParsedLabQuantity(
                test_key=None,
                test_name=test_name or "Unknown",
                numeric_value=None,
                effective_value=None,
                comparator=None,
                unit=explicit_unit,
                multiplier=1.0,
                raw_text=text or "",
                status="cannot_verify",
                rejection_reason="Empty input text",
            )

        test_key, detected_name, value_portion = cls.isolate_test_and_value(text, given_test_name=test_name)

        # Look for comparator: <, <=, >, >=, =
        comp_match = re.search(r"([><]=?|=)", value_portion)
        comparator = comp_match.group(1) if comp_match else None

        # Look for multiplier words (e.g. Lakhs, Lakh, K, Thousand)
        multiplier = 1.0
        for mult_word, mult_val in MULTIPLIERS.items():
            pattern = rf"\b{mult_word}\b"
            if re.search(pattern, value_portion, re.IGNORECASE):
                multiplier = mult_val
                # Remove multiplier word from value string to avoid confusing unit matching
                value_portion = re.sub(pattern, " ", value_portion, flags=re.IGNORECASE)
                break

        # Extract numeric value: float or integer, possibly negative
        # Matches: "7.1", "180000", "0.9", "12,500"
        num_clean = value_portion.replace(",", "")
        num_match = re.search(r"[-+]?\d+(?:\.\d+)?", num_clean)
        if not num_match:
            return ParsedLabQuantity(
                test_key=test_key,
                test_name=detected_name,
                numeric_value=None,
                effective_value=None,
                comparator=comparator,
                unit=cls.normalize_unit(explicit_unit),
                multiplier=multiplier,
                raw_text=text,
                status="cannot_verify",
                rejection_reason=f"No numeric value found in value portion: '{value_portion}'",
            )

        try:
            num_val = float(num_match.group(0))
        except ValueError:
            return ParsedLabQuantity(
                test_key=test_key,
                test_name=detected_name,
                numeric_value=None,
                effective_value=None,
                comparator=comparator,
                unit=cls.normalize_unit(explicit_unit),
                multiplier=multiplier,
                raw_text=text,
                status="cannot_verify",
                rejection_reason=f"Failed to parse float from: '{num_match.group(0)}'",
            )

        effective_val = round(num_val * multiplier, 4)

        # Detect unit if not explicitly passed
        detected_unit = explicit_unit
        if not detected_unit:
            # Look for unit tokens in the remainder after the number
            num_end = num_match.end()
            unit_remainder = num_clean[num_end:].strip()
            # Match common units: %, g/dL, mg/dL, U/L, /cumm, cu.mm, cells/cumm, mmol/L, pg/mL, u/ml, /ul, etc.
            unit_match = re.search(r"(%|g\/dl|gm\/dl|mg\/dl|u\/l|iu\/l|\/cumm|cumm|cu\.mm|cells\/cumm|cells\/ul|\/ul|mmol\/l|pg\/ml|u\/ml)", unit_remainder, re.IGNORECASE)
            if unit_match:
                detected_unit = unit_match.group(1)

        norm_unit = cls.normalize_unit(detected_unit)

        # Status assignment
        if norm_unit is None:
            status = "unverified"
            reason = "Unit missing from lab measurement"
        else:
            status = "verified"
            reason = None

        return ParsedLabQuantity(
            test_key=test_key,
            test_name=detected_name,
            numeric_value=num_val,
            effective_value=effective_val,
            comparator=comparator,
            unit=norm_unit,
            multiplier=multiplier,
            raw_text=text,
            status=status,
            rejection_reason=reason,
        )

    @classmethod
    def parse_quantity(
        cls,
        text: str,
        test_name_hint: Optional[str] = None,
        explicit_unit: Optional[str] = None,
    ) -> ParsedLabQuantity:
        """Alias for parse() supporting test_name_hint parameter."""
        return cls.parse(text, test_name=test_name_hint, explicit_unit=explicit_unit)


lab_parser = StructuredLabParser()
