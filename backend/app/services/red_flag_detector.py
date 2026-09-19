"""
Red-Flag Detection Service
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Evaluates patient statements and interview answers against high-confidence emergency rules.
Supports contextual question-and-answer evaluation, multi-rule scanning with highest-severity
deterministic aggregation (RED > AMBER), and strict fail-safe confirmation.
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

# Comprehensive built-in clinical emergency rules (never allow empty rule set)
FALLBACK_CLINICAL_RULES: list[dict[str, Any]] = [
    {
        "id": "RF-CARD-001",
        "trigger": "chest pain with breathlessness",
        "severity": "red",
        "category": "cardiac",
        "keywords": [
            "chest pain with breathlessness", "chest pain and shortness of breath",
            "chhati me dard aur saans fulna", "seene mein dard aur saans fulna",
            "chest pain", "angina", "seene mein dard", "chhati mein dard"
        ]
    },
    {
        "id": "RF-CARD-002",
        "trigger": "crushing chest pressure",
        "severity": "red",
        "category": "cardiac",
        "keywords": ["crushing chest pressure", "chest pain left arm", "heavy pressure on chest", "dil ka daura"]
    },
    {
        "id": "RF-STROKE-001",
        "trigger": "sudden weakness one side",
        "severity": "red",
        "category": "stroke",
        "keywords": ["sudden weakness one side", "one side paralysis", "ek taraf kamzori", "one side body numb", "falij", "lakwa"]
    },
    {
        "id": "RF-STROKE-002",
        "trigger": "facial droop with slurred speech",
        "severity": "red",
        "category": "stroke",
        "keywords": ["facial droop", "slurred speech", "unable to speak suddenly", "chehra tedha"]
    },
    {
        "id": "RF-PSYCH-001",
        "trigger": "suicidal thoughts or self-harm",
        "severity": "red",
        "category": "psychiatric",
        "keywords": [
            "suicidal thoughts", "want to end my life", "suicide", "marne ka man karta hai",
            "jeene ki ichha nahi", "harming yourself", "kill myself", "end it all", "aatmahatya"
        ]
    },
    {
        "id": "RF-ANAPH-001",
        "trigger": "severe allergic reaction",
        "severity": "red",
        "category": "anaphylaxis",
        "keywords": ["severe allergic reaction", "anaphylaxis", "allergic shock", "swollen tongue", "throat closing"]
    },
    {
        "id": "RF-RESP-001",
        "trigger": "severe acute shortness of breath at rest",
        "severity": "red",
        "category": "respiratory",
        "keywords": ["severe shortness of breath at rest", "gasping for air", "cannot breathe sitting", "saans nahi aa rahi", "dam ghutna"]
    },
    {
        "id": "RF-HEM-001",
        "trigger": "massive active bleeding or vomiting blood",
        "severity": "red",
        "category": "hemorrhage",
        "keywords": ["vomiting blood", "hematemesis", "khoon ki ulti", "coughing up blood", "bleeding profusely"]
    },
    {
        "id": "RF-NEURO-001",
        "trigger": "continuous active seizure",
        "severity": "red",
        "category": "neurological",
        "keywords": ["continuous seizure", "status epilepticus", "fits not stopping", "daura padna band nahi"]
    },
    {
        "id": "RF-TOX-001",
        "trigger": "poison ingestion",
        "severity": "red",
        "category": "toxicology",
        "keywords": ["poison ingestion", "drank pesticide", "zeher khaa liya", "chemical swallowed"]
    },
    {
        "id": "RF-AMB-001",
        "trigger": "high fever with confusion or delirium",
        "severity": "amber",
        "category": "infectious",
        "keywords": ["fever with confusion", "tez bukhar behoshi", "high fever delirious"]
    },
]

# Words indicating positive affirmation in English and Hindi
AFFIRMATIVE_MARKERS = {
    "yes", "yeah", "yep", "yup", "haan", "ha", "haa", "ji haan", "ji ha",
    "haanji", "haan ji", "sometimes", "often", "always", "active", "true",
    "1", "कहा", "हाँ", "हाँजी", "जी हाँ", "जी", "लगता है", "होता है",
    "रहता है", "आते हैं", "चाहता हूँ", "चाहती हूँ", "कभी कभी", "अक्सर"
}

NEGATION_MARKERS = {
    "no", "nope", "not", "never", "none", "nahi", "nahin", "na",
    "नहीं", "ना", "कभी नहीं", "बिलकुल नहीं", "कोई नहीं", "false", "0"
}


class RedFlagDetector:
    def __init__(self, rules_path: Path | None = None):
        self.rules_path = rules_path or DEFAULT_RED_FLAGS_PATH
        self.triggers: list[dict[str, Any]] = []
        self.is_degraded: bool = False
        self.load_rules()

    def load_rules(self) -> None:
        """
        Loads rules from configured JSON path. If invalid, missing, or empty,
        loads comprehensive hardcoded fallback rules and marks safety state degraded.
        Guarantees that self.triggers is NEVER empty.
        """
        if not self.rules_path.exists():
            logger.warning(f"Red flags rules file not found at {self.rules_path}; using clinical fallback set.")
            self.triggers = list(FALLBACK_CLINICAL_RULES)
            self.is_degraded = True
            return

        try:
            with open(self.rules_path, encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, list) and len(loaded) > 0:
                self.triggers = loaded
                self.is_degraded = False
                logger.info(f"Loaded {len(self.triggers)} clinical red-flag triggers from {self.rules_path}")
            else:
                logger.error(f"Red flags file {self.rules_path} contained empty or invalid list; using fallback set.")
                self.triggers = list(FALLBACK_CLINICAL_RULES)
                self.is_degraded = True
        except Exception as e:
            logger.error(f"Failed to load red flags from {self.rules_path}: {e}; using fallback set.")
            self.triggers = list(FALLBACK_CLINICAL_RULES)
            self.is_degraded = True

    def _is_affirmative(self, text: str) -> bool:
        """Check if patient text expresses positive confirmation without explicit negation."""
        cleaned = text.lower().strip()
        tokens = set(cleaned.split())
        has_affirmative = bool(tokens & AFFIRMATIVE_MARKERS) or any(m in cleaned for m in ["हाँ", "जी हाँ", "haan", "yes"])
        has_negation = bool(tokens & NEGATION_MARKERS) or any(n in cleaned for n in ["नहीं", "nahi", "no", "never"])
        return has_affirmative and not has_negation

    def scan_text(
        self,
        text: str,
        session_id: str,
        question_context: str | None = None,
    ) -> RedFlagEvent | None:
        """
        Scans a text input and optional question context for red-flag triggers.
        Evaluates ALL matching rules, selects highest severity deterministically (red > amber),
        and supports contextual affirmative answers to safety questions.
        """
        if not text and not question_context:
            return None

        normalized_text = (text or "").lower().strip()
        normalized_qc = (question_context or "").lower().strip() if question_context else ""

        matched_candidates: list[tuple[int, int, dict[str, Any], str]] = []
        # Tuple format: (severity_rank: 2=red 1=amber, match_length, rule_item, matched_phrase)

        # 1. Direct answer text scan across all triggers
        if normalized_text:
            for item in self.triggers:
                sev = item.get("severity", "red").lower()
                sev_rank = 2 if sev == "red" else 1

                trigger_phrase = item.get("trigger", "").lower()
                if trigger_phrase and trigger_phrase in normalized_text:
                    matched_candidates.append((sev_rank, len(trigger_phrase), item, trigger_phrase))

                for kw in item.get("keywords", []):
                    kw_lower = kw.lower()
                    if kw_lower and kw_lower in normalized_text:
                        matched_candidates.append((sev_rank, len(kw_lower), item, kw))

        # 2. Contextual scan: question asks about emergency, answer is affirmative
        if normalized_qc and normalized_text and self._is_affirmative(normalized_text):
            for item in self.triggers:
                sev = item.get("severity", "red").lower()
                sev_rank = 2 if sev == "red" else 1

                trigger_phrase = item.get("trigger", "").lower()
                qc_match = False
                matched_kw = trigger_phrase

                if trigger_phrase and trigger_phrase in normalized_qc:
                    qc_match = True
                else:
                    for kw in item.get("keywords", []):
                        kw_lower = kw.lower()
                        if kw_lower and kw_lower in normalized_qc:
                            qc_match = True
                            matched_kw = kw
                            break

                # Also match psych/suicide screening questions
                if not qc_match and item.get("category") == "psychiatric":
                    if any(w in normalized_qc for w in ["harm", "suicid", "life", "marne", "jeene", "सुरक्षा", "नुकसान", "आत्महत्या", "जान लेने"]):
                        qc_match = True
                        matched_kw = "psychiatric safety question confirmed"

                if qc_match:
                    logger.info(
                        f"Contextual safety trigger: Question '{question_context}' affirmed by answer '{text}' "
                        f"(rule: {item.get('id')})"
                    )
                    matched_candidates.append((sev_rank, len(matched_kw) + 100, item, f"Contextual Affirmation: {matched_kw}"))

        if not matched_candidates:
            return None

        # Sort: Highest severity rank first (RED > AMBER), then longest match phrase (most specific)
        matched_candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
        best_sev_rank, _, best_item, best_phrase = matched_candidates[0]

        return self._create_event(best_item, best_phrase, session_id)

    def scan_and_confirm(
        self,
        text: str,
        session_id: str,
        question_context: str | None = None,
    ) -> RedFlagEvent | None:
        """
        1. Scans text and question context for candidate keyword triggers.
        2. If candidate matched, executes strict confirmation.
        3. Fails safe: preserves candidate on any uncertainty, error, timeout, or missing fields.
        """
        candidate = self.scan_text(text, session_id, question_context=question_context)
        if not candidate:
            return None

        try:
            from app.services.question_generator import question_generator
            confirmation = question_generator.confirm_red_flag_emergency(
                answer=text,
                matched_keywords=[candidate.trigger_phrase, candidate.matched_rule],
                question_context=question_context,
            )

            if confirmation.get("is_emergency", True):
                logger.warning(
                    f"Red flag emergency CONFIRMED for session {session_id}: "
                    f"{candidate.trigger_phrase} (rule: {candidate.matched_rule}, "
                    f"confidence: {confirmation.get('confidence')})"
                )
                return candidate
            else:
                logger.info(
                    f"Red flag candidate '{candidate.trigger_phrase}' cleared by high-confidence "
                    f"model confirmation (status: {confirmation.get('audit_status')}, "
                    f"confidence: {confirmation.get('confidence')})"
                )
                return None
        except Exception as e:
            logger.error(f"Error during red-flag confirmation: {e}; preserving candidate event as fail-safe.")
            return candidate

    def _create_event(self, item: dict[str, Any], matched_phrase: str, session_id: str) -> RedFlagEvent:
        sev = item.get("severity", "red").lower()
        if sev not in ("red", "amber"):
            sev = "red"
        return RedFlagEvent(
            event_id=f"rfe_{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            trigger_phrase=matched_phrase,
            matched_rule=f"{item.get('id', 'RF-EMERG')}: {item.get('trigger', matched_phrase)}",
            severity=sev,
            category=item.get("category", "general"),
            timestamp=datetime.now(UTC),
        )


# Singleton instance for application reuse
detector = RedFlagDetector()
red_flag_detector = detector
