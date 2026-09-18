"""
Red-Flag Detection Service
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Evaluates patient statements and interview answers against high-confidence emergency rules.
Emits a RedFlagEvent if critical danger signs are detected.
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.shared.schemas import RedFlagEvent

logger = logging.getLogger("medikiosk.red_flag")

# Locate red_flags.json relative to this file
DEFAULT_RED_FLAGS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "red_flags.json"


class RedFlagDetector:
    def __init__(self, rules_path: Path | None = None):
        self.rules_path = rules_path or DEFAULT_RED_FLAGS_PATH
        self.triggers: list[dict[str, Any]] = []
        self.load_rules()

    def load_rules(self) -> None:
        if not self.rules_path.exists():
            logger.warning(f"Red flags rules file not found at {self.rules_path}, using built-in defaults")
            self.triggers = [
                {"id": "RF-CARD-001", "trigger": "chest pain with breathlessness", "severity": "red", "category": "cardiac", "keywords": ["chest pain with breathlessness"]},
                {"id": "RF-PSYCH-001", "trigger": "suicidal thoughts", "severity": "red", "category": "psychiatric", "keywords": ["suicidal thoughts"]},
                {"id": "RF-STROKE-001", "trigger": "sudden weakness one side", "severity": "red", "category": "stroke", "keywords": ["sudden weakness one side"]},
                {"id": "RF-ANAPH-001", "trigger": "severe allergic reaction", "severity": "red", "category": "anaphylaxis", "keywords": ["severe allergic reaction"]}
            ]
            return

        try:
            with open(self.rules_path, encoding="utf-8") as f:
                self.triggers = json.load(f)
            logger.info(f"Loaded {len(self.triggers)} clinical red-flag triggers from {self.rules_path}")
        except Exception as e:
            logger.error(f"Failed to load red flags from {self.rules_path}: {e}")
            self.triggers = []

    def scan_text(self, text: str, session_id: str) -> RedFlagEvent | None:
        """
        Scans a text input for red-flag triggers.
        Returns the highest-severity RedFlagEvent if triggered, otherwise None.
        """
        if not text:
            return None

        normalized_text = text.lower().strip()

        for item in self.triggers:
            # Check main trigger phrase
            trigger_phrase = item.get("trigger", "").lower()
            if trigger_phrase and trigger_phrase in normalized_text:
                return self._create_event(item, trigger_phrase, session_id)

            # Check keyword / synonym variants
            for kw in item.get("keywords", []):
                if kw.lower() in normalized_text:
                    return self._create_event(item, kw, session_id)

        return None

    def _create_event(self, item: dict[str, Any], matched_phrase: str, session_id: str) -> RedFlagEvent:
        return RedFlagEvent(
            event_id=f"rfe_{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            trigger_phrase=matched_phrase,
            matched_rule=f"{item.get('id')}: {item.get('trigger')}",
            severity=item.get("severity", "red"),
            category=item.get("category", "general"),
            timestamp=datetime.now(UTC)
        )


# Singleton instance for application reuse
detector = RedFlagDetector()
