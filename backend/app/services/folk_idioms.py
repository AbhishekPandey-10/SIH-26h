"""
Folk Idiom Normalizer for Indian Hospital OPDs
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Preserves patient's exact colloquial Hindi/Hinglish phrasing alongside standard clinical mappings.
Examples:
- "pet mein aag" -> Epigastric burning / Dyspepsia (possible GERD)
- "chhati mein jalan" -> Heartburn / Retrosternal burning
- "sar ghoom raha hai" -> Vertigo / Lightheadedness
- "kanpkanpi ke sath bukhar" -> Fever with chills and rigors
- "dil ghabra raha hai" -> Palpitations / Anxiety
"""

import re
from typing import Any, Dict, List, Optional

# Curated catalog of Indian colloquial idioms and folk health metaphors
FOLK_IDIOM_CATALOG: List[Dict[str, Any]] = [
    {
        "patterns": [r"pet\s*me(in)?(?:\s+\w+)?\s*aag", r"पेट\s*में(?:\s+\S+)?\s*आग", r"pet\s*jal\s*raha"],
        "display_idiom": "pet mein aag (पेट में आग)",
        "clinical_term": "Epigastric burning / Dyspepsia",
        "suspected_condition": "GERD / Gastritis",
        "snomed_concept": "Burning sensation in epigastrium (finding)",
    },
    {
        "patterns": [r"chhati\s*me(in)?\s*jalan", r"छाती\s*में\s*जलन", r"seene\s*me(in)?\s*jalan", r"सीने\s*में\s*जलन"],
        "display_idiom": "chhati mein jalan (छाती में जलन)",
        "clinical_term": "Retrosternal burning / Heartburn",
        "suspected_condition": "Acid peptic disorder / GERD",
        "snomed_concept": "Heartburn (finding)",
    },
    {
        "patterns": [r"chhati\s*pe\s*bojh", r"छाती\s*पर\s*बोझ", r"seene\s*me(in)?\s*bhari\s*pan", r"सीने\s*में\s*भारीपन"],
        "display_idiom": "seene mein bhari pan (सीने में भारीपन)",
        "clinical_term": "Retrosternal chest pressure",
        "suspected_condition": "Angina pectoris / Ischemia",
        "snomed_concept": "Chest tightness (finding)",
    },
    {
        "patterns": [r"sar\s*ghoom\s*raha", r"सर\s*घूम\s*रहा", r"sir\s*ghoom\s*raha", r"सिर\s*चकरा\s*रहा"],
        "display_idiom": "sar ghoom raha hai (सिर घूम रहा है)",
        "clinical_term": "Vertigo / Lightheadedness",
        "suspected_condition": "Benign paroxysmal positional vertigo / Orthostatic hypotension",
        "snomed_concept": "Vertigo (finding)",
    },
    {
        "patterns": [r"dil\s*ghabra\s*raha", r"दिल\s*घबरा\s*रहा", r"ghabrahat", r"घबराहट"],
        "display_idiom": "dil ghabra raha hai (घबराहट)",
        "clinical_term": "Palpitations / Acute anxiety",
        "suspected_condition": "Sinus tachycardia / Panic disorder",
        "snomed_concept": "Palpitations (finding)",
    },
    {
        "patterns": [r"kanpkanpi", r"कँपकँपी", r"thartharahat", r"थरथराहट"],
        "display_idiom": "kanpkanpi ke sath bukhar (कँपकँपी)",
        "clinical_term": "Fever with rigors and chills",
        "suspected_condition": "Malaria / Pyelonephritis / Sepsis",
        "snomed_concept": "Rigor (finding)",
    },
    {
        "patterns": [r"sukhi\s*khansi", r"सूखी\s*खांसी", r"khushk\s*khansi"],
        "display_idiom": "sukhi khansi (सूखी खांसी)",
        "clinical_term": "Dry non-productive cough",
        "suspected_condition": "Viral URI / ACE-inhibitor cough",
        "snomed_concept": "Dry cough (finding)",
    },
    {
        "patterns": [r"paanv\s*me(in)?\s*sujan", r"पांव\s*में\s*सूजन", r"pairo(n)?\s*me(in)?\s*sujan", r"पैरों\s*में\s*सूजन"],
        "display_idiom": "paanv mein sujan (पैरों में सूजन)",
        "clinical_term": "Bilateral pedal edema",
        "suspected_condition": "Congestive heart failure / Renal compromise / Venous insufficiency",
        "snomed_concept": "Peripheral edema (finding)",
    },
    {
        "patterns": [r"peshab\s*me(in)?\s*jalan", r"पेशाब\s*में\s*जलन", r"peshab\s*kat\s*kat"],
        "display_idiom": "peshab mein jalan (पेशाब में जलन)",
        "clinical_term": "Dysuria / Burning micturition",
        "suspected_condition": "Urinary tract infection",
        "snomed_concept": "Dysuria (finding)",
    },
    {
        "patterns": [r"dum\s*ghut\s*raha", r"दम\s*घुट\s*रहा", r"saans\s*phool\s*rahi", r"सांस\s*फूल\s*रही"],
        "display_idiom": "saans phool rahi hai (सांस फूल रही है)",
        "clinical_term": "Dyspnea on exertion / Breathlessness",
        "suspected_condition": "Asthma / COPD / Heart Failure",
        "snomed_concept": "Dyspnea (finding)",
    },
    {
        "patterns": [r"aankho(n)?\s*ke\s*aage\s*andhera", r"आंखों\s*के\s*आगे\s*अंधेरा"],
        "display_idiom": "aankhon ke aage andhera (आंखों के आगे अंधेरा)",
        "clinical_term": "Presyncope / Transient visual obscuration",
        "suspected_condition": "Postural hypotension / Severe anemia",
        "snomed_concept": "Presyncope (finding)",
    },
]


class FolkIdiomNormalizer:
    def __init__(self, catalog: Optional[List[Dict[str, Any]]] = None):
        self.catalog = catalog or FOLK_IDIOM_CATALOG

    def detect_idioms(self, text: str) -> List[Dict[str, Any]]:
        """
        Scans a text for colloquial folk idioms.
        Returns matched mappings with original text spans.
        """
        if not text:
            return []

        matched: List[Dict[str, Any]] = []
        for entry in self.catalog:
            for pat in entry["patterns"]:
                match = re.search(pat, text, re.IGNORECASE)
                if match:
                    matched.append({
                        "matched_span": match.group(0),
                        "display_idiom": entry["display_idiom"],
                        "clinical_term": entry["clinical_term"],
                        "suspected_condition": entry["suspected_condition"],
                        "snomed_concept": entry["snomed_concept"],
                    })
                    break  # Matched this catalog entry, move to next
        return matched

    def normalize_statement(self, text: str) -> Dict[str, Any]:
        """
        Normalizes patient statement preserving both clinical mapping and exact colloquial verbatim.
        """
        idioms = self.detect_idioms(text)
        if not idioms:
            return {
                "has_idiom": False,
                "original_text": text,
                "clinical_summary": text,
                "verbatim": text,
                "mappings": [],
            }

        primary = idioms[0]
        clinical_annotated = (
            f"{primary['clinical_term']} (suspected {primary['suspected_condition']}) "
            f"[Patient verbatim: \"{primary['matched_span']}\"]"
        )

        return {
            "has_idiom": True,
            "original_text": text,
            "clinical_summary": clinical_annotated,
            "verbatim": primary["matched_span"],
            "primary_clinical_term": primary["clinical_term"],
            "suspected_condition": primary["suspected_condition"],
            "mappings": idioms,
        }

    def enhance_summary_content(self, content: str) -> str:
        """
        Replaces colloquial idioms in summary content with clinically annotated terms.
        """
        enhanced = content
        for entry in self.catalog:
            for pat in entry["patterns"]:
                match = re.search(pat, enhanced, re.IGNORECASE)
                if match:
                    span = match.group(0)
                    replacement = f"{entry['clinical_term']} [Patient verbatim: '{span}']"
                    enhanced = re.sub(pat, replacement, enhanced, count=1, flags=re.IGNORECASE)
                    break
        return enhanced


folk_idiom_normalizer = FolkIdiomNormalizer()
