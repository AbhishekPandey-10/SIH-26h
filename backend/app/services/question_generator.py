"""
Gemini Clinical Question Generator & Reasoner
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Provides:
1. Chief complaint category classification (pain | general | psych | obgyn)
2. Dynamic clinical question generation using Gemini with few-shot examples
3. Gemini-based Red-Flag emergency confirmation
"""

import json
import logging
import os
import re
from typing import Any, Literal

from app.config import settings
from app.services.gemini_retry import gemini_call_with_retry

logger = logging.getLogger("medikiosk.question_gen")

ChiefComplaintCategory = Literal["pain", "general", "psych", "obgyn"]


FEW_SHOT_EXAMPLES = [
    {
        "language": "hi",
        "chief_complaint": "सीने में तेज दर्द हो रहा है",
        "current_section": "socrates_pain",
        "context": [{"question": "क्या तकलीफ है?", "answer": "सीने में तेज दर्द है"}],
        "output": {
            "question_id": "soc_site_01",
            "text": "यह दर्द छाती में ठीक किस तरफ महसूस हो रहा है — बीच में, बाईं तरफ या दाईं तरफ?",
            "input_type": "tap",
            "options": ["बाईं तरफ (Left)", "बीच में (Center)", "दाईं तरफ (Right)", "पूरे सीने में (Whole chest)"],
            "metadata": {"socrates_axis": "site", "category": "hpi"}
        }
    },
    {
        "language": "hi",
        "chief_complaint": "पिछले 5 दिनों से तेज बुखार और कंपकंपी है",
        "current_section": "socrates_general",
        "context": [{"question": "बुखार कितने दिन से है?", "answer": "5 दिन से लगातार है"}],
        "output": {
            "question_id": "soc_assoc_01",
            "text": "क्या बुखार के साथ ठंड लगना, पसीना आना या उल्टी-दस्त जैसी कोई परेशानी भी है?",
            "input_type": "tap",
            "options": ["ठंड लगकर बुखार (Chills)", "उल्टी या दस्त (Vomiting/Diarrhea)", "बदन दर्द (Body ache)", "कोई नहीं (None)"],
            "metadata": {"socrates_axis": "associated", "category": "hpi"}
        }
    },
    {
        "language": "en",
        "chief_complaint": "Feeling extremely sad, hopeless and crying every day",
        "current_section": "psych_screening",
        "context": [{"question": "Chief complaint?", "answer": "Feeling very sad"}],
        "output": {
            "question_id": "psych_sleep_01",
            "text": "How has this affected your daily routine, sleep pattern, or appetite over the past few weeks?",
            "input_type": "voice",
            "options": ["Unable to sleep", "Loss of appetite", "No interest in work", "Feeling fine physically"],
            "metadata": {"socrates_axis": "impact", "category": "psych"}
        }
    },
    {
        "language": "hi",
        "chief_complaint": "पेट में नीचे बहुत तेज दर्द है और माहवारी रुक गई है",
        "current_section": "obgyn_history",
        "context": [{"question": "मुख्य शिकायत?", "answer": "माहवारी 2 महीने से नहीं आई और दर्द है"}],
        "output": {
            "question_id": "obgyn_lmp_01",
            "text": "आपकी पिछली माहवारी (मासिक धर्म) की अनुमानित तारीख क्या थी?",
            "input_type": "voice",
            "options": ["1 महीने पहले", "2 महीने पहले", "3 महीने से अधिक", "याद नहीं"],
            "metadata": {"socrates_axis": "lmp", "category": "obgyn"}
        }
    }
]


class QuestionGenerator:
    """
    Orchestrates Gemini LLM for question generation and clinical classification.
    Falls back deterministically if Gemini is offline or unconfigured.
    """
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
        self.model_name = settings.GEMINI_MODEL or "gemini-2.0-flash"
        self._client = None

    def _get_client(self):
        if not self.api_key:
            return None
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Unable to initialize google-genai client: {e}")
                return None
        return self._client

    def classify_complaint(self, chief_complaint: str) -> ChiefComplaintCategory:
        """
        Classifies the chief complaint into pain, general, psych, or obgyn.
        """
        if not chief_complaint:
            return "general"

        text_lower = chief_complaint.lower()

        # Check with Gemini if client available
        client = self._get_client()
        if client:
            try:
                prompt = (
                    f"Classify the following medical chief complaint into exactly ONE of these four categories:\n"
                    f"1. pain (for any pain symptom: chest pain, headache, abdominal pain, joint pain, etc.)\n"
                    f"2. psych (for depression, sadness, anxiety, suicidal thoughts, mental distress)\n"
                    f"3. obgyn (for pregnancy, menstruation, vaginal bleeding, pelvic pain in female patients)\n"
                    f"4. general (for fever, cough, nausea, rash, fatigue, weakness, vomiting, etc.)\n\n"
                    f'Chief complaint: "{chief_complaint}"\n\n'
                    f'Respond ONLY with valid JSON: {{"category": "pain" | "general" | "psych" | "obgyn"}}'
                )
                response = gemini_call_with_retry(client, self.model_name, prompt)
                if response is None:
                    raise RuntimeError("Gemini retries exhausted")
                raw_text = response.text.strip()
                # Parse JSON
                match = re.search(r"\{.*?\}", raw_text, re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
                    cat = data.get("category", "").lower()
                    if cat in ["pain", "general", "psych", "obgyn"]:
                        logger.info(f"Gemini classified '{chief_complaint}' as category: {cat}")
                        return cat
            except Exception as e:
                logger.warning(f"Gemini complaint classification failed: {e}; using heuristic fallback.")

        # Heuristic / Deterministic Fallback
        # 1. Psychiatric
        psych_keywords = [
            "sad", "depress", "suicid", "hopeless", "cry", "anxiety", "panic",
            "mental", "stress", "sleep", "marne", "udas", "depression", "tension", "dimag",
            "उदास", "मरने", "आत्महत्या", "रोना", "घबराहट", "चिंता", "तनाव", "डिप्रेशन",
            "नींद नहीं", "जीने की इच्छा", "बेचैनी", "मानसिक"
        ]
        if any(kw in text_lower for kw in psych_keywords):
            return "psych"

        # 2. ObGyn
        obgyn_keywords = [
            "period", "pregnant", "pregnancy", "menstru", "bleed", "bleeding",
            "vagina", "discharge", "lmp", "delivery", "garbh", "mahawari", "mahavari",
            "माहवारी", "महावारी", "पीरियड्स", "पीरियड", "गर्भवती", "गर्भ", "प्रेगनेंसी",
            "डिलीवरी", "सफेद पानी", "मासिक धर्म"
        ]
        if any(kw in text_lower for kw in obgyn_keywords):
            return "obgyn"

        # 3. Pain
        pain_keywords = [
            "pain", "ache", "hurt", "tender", "burning", "cramp", "sore", "pressure",
            "radiat", "colic", "stabbing", "droop", "slur", "numb", "dizzy",
            "dard", "chhati me dard", "peeth", "sar dard", "pet dard", "dukhta",
            "दर्द", "सीने में", "छाती", "दबाव", "जलन", "पीड़ा", "कष्ट", "दुखता", "सुन्न",
            "टेढ़ा", "कमर", "सिर", "पेट में दर्द", "पसलियों", "धड़कन", "भारीपन", "खिंचाव",
            "चुभन", "कंधे", "घुटनों", "दांत", "पैर में", "कान में दर्द"
        ]
        if any(kw in text_lower for kw in pain_keywords):
            return "pain"

        # 4. Default: General
        return "general"

    def generate_question(
        self,
        current_section: str,
        chief_complaint: str,
        context: list[dict[str, Any]],
        language: str = "hi",
        socrates_axis: str | None = None,
        extracted_context: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Generates the next clinical question via Gemini or clinical fallback.
        Incorporates Smart Recall known facts from patient documents.
        """
        client = self._get_client()
        context_json = json.dumps(context[-4:], ensure_ascii=False) if context else "[]"
        known_facts_json = json.dumps(extracted_context, ensure_ascii=False, indent=2) if extracted_context else "None"

        if client:
            try:
                examples_text = json.dumps(FEW_SHOT_EXAMPLES, ensure_ascii=False, indent=2)
                system_prompt = (
                    f"You are a clinical history-taking assistant in an Indian hospital OPD.\n"
                    f"Patient language: {language}\n"
                    f"Chief complaint: {chief_complaint}\n"
                    f"Answers so far: {context_json}\n\n"
                    f"ALREADY KNOWN FACTS (from patient's medical documents):\n"
                    f"{known_facts_json}\n\n"
                    f"Rules:\n"
                    f"- Do NOT re-ask questions whose answers are already available above.\n"
                    f"- If a fact has confidence > 0.8: confirm briefly (\"Your records show you take Metformin 500mg — is that still current?\")\n"
                    f"- If confidence 0.5-0.8: rephrase as a verification question\n"
                    f"- If confidence < 0.5: ask the question normally as if you don't know\n\n"
                    f'Generate the next question for the "{current_section}" section.\n'
                    f"Follow the SOCRATES framework for pain-related complaints.\n"
                    f"Ask ONE question at a time. Be conversational, culturally empathetic, not clinical.\n\n"
                    f"Few-shot examples:\n{examples_text}\n\n"
                    f"Output strictly as JSON:\n"
                    f"{{\n"
                    f'  "question_id": "unique_id",\n'
                    f'  "text": "question in patient\'s language",\n'
                    f'  "input_type": "voice" | "tap",\n'
                    f'  "options": ["optional", "tap", "choices"],\n'
                    f'  "metadata": {{ "socrates_axis": "{socrates_axis or "detail"}", "category": "{current_section}" }}\n'
                    f"}}"
                )
                response = gemini_call_with_retry(client, self.model_name, system_prompt)
                if response is None:
                    raise RuntimeError("Gemini retries exhausted")
                raw_text = response.text.strip()
                match = re.search(r"\{.*\}", raw_text, re.DOTALL)
                if match:
                    parsed = json.loads(match.group(0))
                    if "text" in parsed:
                        return parsed
            except Exception as e:
                logger.warning(f"Gemini question generation failed: {e}; using fallback question template.")


        # Fallback question generation
        return self._fallback_question(current_section, chief_complaint, language, socrates_axis)

    def confirm_red_flag_emergency(
        self,
        answer: str,
        matched_keywords: list[str],
        question_context: str | None = None,
    ) -> dict[str, Any]:
        """
        Gemini verification of red-flag emergency:
        Strictly parses confirmation. Any failure, malformed JSON, missing fields,
        or uncertain output preserves the rule candidate (fail-safe).
        """
        keywords_str = ", ".join(matched_keywords)
        client = self._get_client()

        if client:
            try:
                context_str = f'Question asked: "{question_context}"\n' if question_context else ""
                prompt = (
                    f"{context_str}"
                    f'Patient statement: "{answer}"\n'
                    f"Does this indicate any of these emergencies: {keywords_str}?\n\n"
                    f"Output strictly as JSON:\n"
                    f'{{"is_emergency": true|false, "matched_rule": str, "confidence": float}}\n'
                    f"Only return false if you are certain this is NOT a medical emergency."
                )
                response = gemini_call_with_retry(client, self.model_name, prompt)
                if response is not None and response.text:
                    raw_text = response.text.strip()
                    match = re.search(r"\{.*?\}", raw_text, re.DOTALL)
                    if match:
                        result = json.loads(match.group(0))
                        
                        # Strict boolean parsing
                        raw_is_emerg = result.get("is_emergency")
                        is_emerg: bool | None = None
                        if isinstance(raw_is_emerg, bool):
                            is_emerg = raw_is_emerg
                        elif isinstance(raw_is_emerg, str):
                            lower_str = raw_is_emerg.strip().lower()
                            if lower_str in ("true", "1", "yes", "t"):
                                is_emerg = True
                            elif lower_str in ("false", "0", "no", "f"):
                                is_emerg = False

                        # If field missing or invalid, fail safe (preserve candidate)
                        if is_emerg is None:
                            logger.warning("Gemini emergency confirmation output missing or invalid 'is_emergency'; preserving candidate.")
                            return {
                                "is_emergency": True,
                                "matched_rule": result.get("matched_rule", keywords_str),
                                "confidence": 0.90,
                                "audit_status": "fail_safe_missing_field",
                            }

                        try:
                            confidence = float(result.get("confidence", 0.9))
                        except (ValueError, TypeError):
                            confidence = 0.9

                        # If model is uncertain (< 0.8 confidence), fail safe
                        if confidence < 0.80:
                            logger.info(f"Gemini confirmation confidence ({confidence}) < 0.80; preserving candidate.")
                            return {
                                "is_emergency": True,
                                "matched_rule": result.get("matched_rule", keywords_str),
                                "confidence": confidence,
                                "audit_status": "fail_safe_low_confidence",
                            }

                        # High-confidence classification
                        return {
                            "is_emergency": is_emerg,
                            "matched_rule": result.get("matched_rule", keywords_str),
                            "confidence": confidence,
                            "audit_status": "model_confirmed" if is_emerg else "model_rejected",
                        }
            except Exception as e:
                logger.warning(f"Gemini emergency confirmation error: {e}; preserving matched rule candidate.")

        # Fail-safe fallback when Gemini is unavailable, timed out, or unconfigured:
        # Candidate matched configured emergency rules; preserve it!
        return {
            "is_emergency": True,
            "matched_rule": keywords_str,
            "confidence": 0.95,
            "audit_status": "fail_safe_rule_match",
        }


    def _fallback_question(
        self,
        current_section: str,
        chief_complaint: str,
        language: str = "hi",
        socrates_axis: str | None = None,
    ) -> dict[str, Any]:
        """Curated high-quality clinical fallback questions in Hindi and English."""
        is_hi = (language == "hi")

        if current_section == "socrates_pain":
            axis = socrates_axis or "site"
            pain_templates = {
                "site": {
                    "hi": "यह दर्द शरीर के किस हिस्से में हो रहा है?",
                    "en": "Where exactly is the pain located in your body?",
                    "options": ["सीने में (Chest)", "पेट में (Abdomen)", "सिर में (Head)", "कमर / पीठ (Back)"],
                },
                "onset": {
                    "hi": "यह दर्द कब और कैसे शुरू हुआ — अचानक या धीरे-धीरे?",
                    "en": "When and how did this pain begin — suddenly or gradually?",
                    "options": ["अचानक शुरू हुआ (Sudden)", "धीरे-धीरे बढ़ा (Gradual)", "आज ही (Today)", "कुछ दिनों से (Few days)"],
                },
                "character": {
                    "hi": "दर्द का अहसास कैसा है (चुभने वाला, भारीपन, जलन या खिंचाव)?",
                    "en": "How would you describe the pain (sharp, heavy, burning, squeezing)?",
                    "options": ["भारीपन/दबाव (Heavy pressure)", "चुभने वाला (Sharp/Stabbing)", "जलन जैसा (Burning)", "हल्का मीठा दर्द (Dull ache)"],
                },
                "radiation": {
                    "hi": "क्या यह दर्द कहीं और फैल रहा है (जैसे कंधे, हाथ, जबड़े या पीठ में)?",
                    "en": "Does the pain radiate or travel anywhere else (shoulder, arm, jaw, back)?",
                    "options": ["बाएँ हाथ में (Left arm)", "पीठ की तरफ (To the back)", "गर्दन/जबड़े में (Neck/jaw)", "कहीं नहीं फैलता (Nowhere)"],
                },
                "associations": {
                    "hi": "दर्द के साथ क्या सांस फूलना, पसीना आना या चक्कर महसूस हो रहा है?",
                    "en": "Are there any associated symptoms like breathlessness, sweating, or nausea?",
                    "options": ["सांस फूलना (Breathlessness)", "पसीना आना (Sweating)", "उल्टी/घबराहट (Nausea)", "कोई अन्य लक्षण नहीं (None)"],
                },
                "time": {
                    "hi": "क्या दर्द लगातार बना हुआ है या बीच-बीच में आता जाता है?",
                    "en": "Is the pain constant or does it come and go in waves?",
                    "options": ["लगातार बना हुआ है (Constant)", "आता-जाता रहता है (Intermittent)", "रात को बढ़ता है (Worse at night)"],
                },
                "exacerbating": {
                    "hi": "किस चीज़ से दर्द बढ़ता या घटता है (चलने-फिरने से, आराम करने से या खाने से)?",
                    "en": "What makes the pain better or worse (resting, movement, food)?",
                    "options": ["चलने से बढ़ता है (Worse on walking)", "आराम से घटता है (Better with rest)", "कोई फर्क नहीं पड़ता (No change)"],
                },
                "severity": {
                    "hi": "दर्द की तीव्रता 1 से 10 के पैमाने पर कितनी है?",
                    "en": "On a scale of 1 to 10, how severe is the pain?",
                    "options": ["1-3 (हल्का / Mild)", "4-6 (मध्यम / Moderate)", "7-8 (तेज / Severe)", "9-10 (असहनीय / Critical)"],
                },
            }
            cfg = pain_templates.get(axis, pain_templates["site"])
            return {
                "question_id": f"soc_pain_{axis}",
                "text": cfg["hi"] if is_hi else cfg["en"],
                "input_type": "tap" if cfg.get("options") else "voice",
                "options": cfg.get("options"),
                "metadata": {"socrates_axis": axis, "category": "socrates_pain"},
            }

        elif current_section == "socrates_general":
            axis = socrates_axis or "duration"
            gen_templates = {
                "duration": {
                    "hi": "यह तकलीफ कितने दिनों या हफ़्तों से महसूस हो रही है?",
                    "en": "How many days or weeks have you had this issue?",
                    "options": ["1-2 दिन से", "3-5 दिन से", "1-2 हफ्ते से", "महीने भर से"],
                },
                "pattern": {
                    "hi": "क्या बुखार या तकलीफ पूरे दिन रहती है या किसी खास वक्त पर तेज होती है?",
                    "en": "Does the symptom stay all day or spike at particular times?",
                    "options": ["लगातार पूरे दिन", "शाम या रात में", "सुबह के समय", "उतार-चढ़ाव होता है"],
                },
                "associated": {
                    "hi": "क्या इसके साथ कोई अन्य लक्षण जैसे खांसी, उल्टी, दस्त या कमजोरी है?",
                    "en": "Any associated symptoms like cough, vomiting, diarrhea, or weakness?",
                    "options": ["खांसी / कफ", "उल्टी या दस्त", "बहुत कमजोरी", "कोई अन्य लक्षण नहीं"],
                },
                "severity": {
                    "hi": "इस तकलीफ से आपका रोजमर्रा का काम कितना प्रभावित हो रहा है?",
                    "en": "How much is this affecting your daily activities?",
                    "options": ["हल्का असर", "काम करने में परेशानी", "पूरी तरह बिस्तर पर"],
                },
            }
            cfg = gen_templates.get(axis, gen_templates["duration"])
            return {
                "question_id": f"soc_gen_{axis}",
                "text": cfg["hi"] if is_hi else cfg["en"],
                "input_type": "tap",
                "options": cfg.get("options"),
                "metadata": {"socrates_axis": axis, "category": "socrates_general"},
            }

        elif current_section == "psych_screening":
            axis = socrates_axis or "duration"
            psych_templates = {
                "duration": {
                    "hi": "आप इस तरह का उदास या भारी मन कितने समय से महसूस कर रहे हैं?",
                    "en": "How long have you been feeling this sadness or low mood?",
                    "options": ["कुछ दिनों से", "2-4 हफ़्तों से", "कई महीनों से"],
                },
                "sleep_appetite": {
                    "hi": "क्या आपकी नींद और भूख में कोई बड़ा बदलाव आया है?",
                    "en": "Has this affected your sleep or appetite significantly?",
                    "options": ["नींद नहीं आती", "भूख कम हो गई है", "हमेशा थकान रहती है", "कोई खास बदलाव नहीं"],
                },
                "triggers": {
                    "hi": "क्या हाल ही में कोई बड़ा मानसिक तनाव, नुकसान या पारिवारिक परेशानी हुई है?",
                    "en": "Has there been any recent severe stress, loss, or family difficulty?",
                    "options": ["पारिवारिक तनाव", "आर्थिक / काम का तनाव", "किसी प्रियजन का बिछड़ना", "कोई खास वजह नहीं"],
                },
                "safety": {
                    "hi": "क्या मन में कभी जीवन समाप्त करने या खुद को नुकसान पहुँचाने का विचार आया है?",
                    "en": "Have you had thoughts of wanting to harm yourself or end your life?",
                    "options": ["नहीं, कभी नहीं (No, never)", "हाँ, कभी-कभी विचार आता है (Yes, occasionally)"],
                },
            }
            cfg = psych_templates.get(axis, psych_templates["duration"])
            return {
                "question_id": f"soc_psych_{axis}",
                "text": cfg["hi"] if is_hi else cfg["en"],
                "input_type": "tap",
                "options": cfg.get("options"),
                "metadata": {"socrates_axis": axis, "category": "psych_screening"},
            }

        elif current_section == "obgyn_history":
            axis = socrates_axis or "lmp"
            obgyn_templates = {
                "lmp": {
                    "hi": "आपकी पिछली माहवारी (पीरियड्स) की शुरुआत किस तारीख को हुई थी?",
                    "en": "When was the first day of your last menstrual period (LMP)?",
                    "options": ["पिछले हफ्ते", "2-3 हफ्ते पहले", "1 महीने पहले", "याद नहीं"],
                },
                "regularity": {
                    "hi": "क्या आपके पीरियड्स आमतौर पर नियमित रहते हैं या अनियमित?",
                    "en": "Are your menstrual cycles usually regular or irregular?",
                    "options": ["हमेशा नियमित (Regular)", "अक्सर अनियमित (Irregular)"],
                },
                "pregnancy": {
                    "hi": "क्या वर्तमान में गर्भधारण (प्रेग्नेंसी) की संभावना है?",
                    "en": "Is there a possibility of current pregnancy?",
                    "options": ["हाँ (Yes)", "नहीं (No)", "जाँच नहीं की (Not tested)"],
                },
            }
            cfg = obgyn_templates.get(axis, obgyn_templates["lmp"])
            return {
                "question_id": f"soc_obgyn_{axis}",
                "text": cfg["hi"] if is_hi else cfg["en"],
                "input_type": "tap",
                "options": cfg.get("options"),
                "metadata": {"socrates_axis": axis, "category": "obgyn_history"},
            }

        elif current_section == "pmh":
            return {
                "question_id": "q_pmh_01",
                "text": "क्या आपको पहले से कोई पुरानी बीमारी है (जैसे बीपी, शुगर, थायरॉइड, अस्थमा)?" if is_hi else "Do you have any past medical conditions (diabetes, hypertension, asthma)?",
                "input_type": "tap",
                "options": ["मधुमेह (Diabetes)", "उच्च रक्तचाप (Hypertension)", "थायरॉइड (Thyroid)", "अस्थमा (Asthma)", "कोई नहीं (None)"],
                "metadata": {"category": "pmh"},
            }
        elif current_section == "medications":
            return {
                "question_id": "q_med_01",
                "text": "क्या आप वर्तमान में नियमित रूप से कोई दवाई या गोली ले रहे हैं?" if is_hi else "Are you currently taking any regular medications or tablets?",
                "input_type": "voice",
                "options": ["हाँ, नियमित दवाइयाँ हैं", "नहीं, कोई दवाई नहीं"],
                "metadata": {"category": "medications"},
            }
        elif current_section == "allergies":
            return {
                "question_id": "q_all_01",
                "text": "क्या आपको किसी दवाई, इंजेक्शन या खाने की चीज़ से कोई एलर्जी है?" if is_hi else "Do you have any known allergies to medicines, injections, or food?",
                "input_type": "tap",
                "options": ["हाँ (Yes)", "नहीं (No)"],
                "metadata": {"category": "allergies"},
            }
        elif current_section == "family_hx":
            return {
                "question_id": "q_fam_01",
                "text": "क्या आपके परिवार (माता-पिता, भाई-बहन) में किसी को दिल की बीमारी, शुगर या कैंसर का इतिहास है?" if is_hi else "Is there a family history of heart disease, diabetes, or cancer?",
                "input_type": "voice",
                "options": ["हाँ, परिवार में इतिहास है", "नहीं, कोई इतिहास नहीं"],
                "metadata": {"category": "family_hx"},
            }
        elif current_section == "personal_hx":
            return {
                "question_id": "q_per_01",
                "text": "आपकी जीवनशैली से जुड़ी आदतें (धूम्रपान, तंबाकू, शराब सेवन आदि)?" if is_hi else "Any personal habits such as smoking, tobacco, or alcohol?",
                "input_type": "tap",
                "options": ["तंबाकू / बीड़ी", "शराब", "दोनों", "कोई नशा नहीं"],
                "metadata": {"category": "personal_hx"},
            }
        elif current_section == "ros":
            return {
                "question_id": "q_ros_01",
                "text": "क्या इनके अलावा वजन घटना, भूख में कमी या चक्कर जैसी कोई अन्य शिकायत है?" if is_hi else "Any systemic symptoms like weight loss, dizziness, or appetite changes?",
                "input_type": "voice",
                "options": ["हाँ, अन्य शिकायत है", "नहीं, कुछ नहीं"],
                "metadata": {"category": "ros"},
            }
        else: # complete
            return {
                "question_id": "q_end_01",
                "text": "धन्यवाद! आपकी प्राथमिक जानकारी दर्ज कर ली गई है। कृपया डॉक्टर के केबिन के बाहर प्रतीक्षा करें।" if is_hi else "Thank you! Your intake is complete. Please wait outside the doctor cabin.",
                "input_type": "tap",
                "options": ["ठीक है (OK)"],
                "metadata": {"category": "complete"},
            }


question_generator = QuestionGenerator()
