"""
LangGraph Clinical Interview Engine — Full Implementation
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

State machine orchestrating the clinical history-taking flow:
intake -> chief_complaint -> categorize_complaint ->
  [if pain] -> socrates_pain
  [if general] -> socrates_general
  [if psych] -> psych_screening
  [if obgyn] -> obgyn_history
-> pmh -> medications -> allergies -> family_hx -> personal_hx -> ros -> complete
"""

import logging
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.services.ayush_service import DASHHAVIDHA_STAGES
from app.services.question_generator import question_generator
from app.shared.schemas import NextQuestion

logger = logging.getLogger("medikiosk.interview_engine")


class InterviewState(TypedDict, total=False):
    session_id: str
    language: str
    current_node: str
    chief_complaint: str
    chief_complaint_category: str  # "pain" | "general" | "psych" | "obgyn"
    asked_questions: list[dict[str, Any]]
    answers: list[dict[str, Any]]
    extracted_context: list[dict[str, Any]]  # filled by Smart Recall
    red_flags_triggered: list[dict[str, Any]]
    confirmed_facts: list[dict[str, Any]]  # facts confirmed/corrected by patient
    is_paused: bool
    paused_reason: str | None

    # Step navigation helpers
    socrates_axis_index: int
    last_answer: str | None
    next_question: NextQuestion | None
    is_complete: bool

    # Phase 5: Body Map, AYUSH Dashavidha Pariksha, and Caregiver Mode
    body_map_selections: list[str] | None
    interview_mode: str  # "allopathic" | "ayush"
    ayush_stage_index: int
    ayush_answers: dict[str, Any]
    prakriti_result: dict[str, Any] | None
    is_caregiver: bool
    caregiver_name: str | None
    caregiver_relationship: str | None


PAIN_AXES = [
    "site",
    "onset",
    "character",
    "radiation",
    "associations",
    "time",
    "exacerbating",
    "severity",
]
GENERAL_AXES = ["duration", "pattern", "associated", "severity"]
PSYCH_AXES = ["duration", "sleep_appetite", "triggers", "safety"]
OBGYN_AXES = ["lmp", "regularity", "pregnancy"]


def node_intake(state: InterviewState) -> InterviewState:
    """Initial kiosk intake node."""
    lang = state.get("language", "hi")
    return {
        "current_node": "intake",
        "language": lang,
        "chief_complaint_category": "general",
        "asked_questions": state.get("asked_questions", []),
        "answers": state.get("answers", []),
        "extracted_context": state.get("extracted_context", []),
        "red_flags_triggered": state.get("red_flags_triggered", []),
        "socrates_axis_index": 0,
        "ayush_stage_index": 0,
        "ayush_answers": state.get("ayush_answers", {}),
    }


def node_chief_complaint(state: InterviewState) -> InterviewState:
    """Chief complaint elicitation."""
    lang = state.get("language", "hi")
    is_hi = (lang == "hi")
    text = (
        "नमस्ते, आज आपको अस्पताल किस तकलीफ या समस्या के कारण आना पड़ा?"
        if is_hi
        else "Hello, what primary symptom or health concern brings you to the hospital today?"
    )
    nq = NextQuestion(
        question_id="q_cc_01",
        text=text,
        input_type="voice_touch",
        options=["सीने में दर्द (Chest pain)", "बुखार (Fever)", "पेट में दर्द (Stomach pain)", "सिरदर्द (Headache)"],
        section="chief_complaint",
        progress_pct=10.0,
    )
    asked = list(state.get("asked_questions", []))
    asked.append(nq.model_dump())
    return {
        "current_node": "chief_complaint",
        "next_question": nq,
        "asked_questions": asked,
    }


def node_categorize_complaint(state: InterviewState) -> InterviewState:
    """Classifies the chief complaint category (pain | general | psych | obgyn)."""
    cc = state.get("last_answer") or state.get("chief_complaint") or ""
    category = question_generator.classify_complaint(cc)
    logger.info(f"Session {state.get('session_id')}: Categorized chief complaint '{cc}' as '{category}'")
    return {
        "current_node": "categorize_complaint",
        "chief_complaint": cc,
        "chief_complaint_category": category,
        "socrates_axis_index": 0,
    }


def route_complaint(state: InterviewState) -> Literal["ayush_pariksha", "socrates_pain", "socrates_general", "psych_screening", "obgyn_history"]:
    """Conditional router based on interview mode and categorized chief complaint."""
    if state.get("interview_mode") == "ayush":
        return "ayush_pariksha"
    cat = state.get("chief_complaint_category", "general")
    if cat == "pain":
        return "socrates_pain"
    elif cat == "psych":
        return "psych_screening"
    elif cat == "obgyn":
        return "obgyn_history"
    else:
        return "socrates_general"


def node_socrates_pain(state: InterviewState) -> InterviewState:
    """SOCRATES pain framework questions with 2D Body Map site-skip."""
    idx = state.get("socrates_axis_index", 0)
    body_map = state.get("body_map_selections") or []
    answers = list(state.get("answers", []))

    # Body-map context reaches LangGraph and skips SOCRATES "site" question
    if idx == 0 and body_map:
        site_str = ", ".join(body_map)
        logger.info(f"Skipping SOCRATES site axis using 2D Body Map selections: {site_str}")
        answers.append({
            "node": "socrates_pain",
            "question_id": "soc_pain_site",
            "question_text": "शरीर में दर्द का स्थान (2D Body Map)",
            "answer_text": site_str,
            "verbatim_voice": None,
            "language": state.get("language", "hi"),
        })
        state["answers"] = answers
        idx = 1
        state["socrates_axis_index"] = 1

    axis = PAIN_AXES[min(idx, len(PAIN_AXES) - 1)]
    lang = state.get("language", "hi")
    cc = state.get("chief_complaint", "")

    q_data = question_generator.generate_question(
        current_section="socrates_pain",
        chief_complaint=cc,
        context=answers,
        language=lang,
        socrates_axis=axis,
    )
    meta = dict(q_data.get("metadata") or {})
    meta["category"] = "socrates_pain"
    if body_map:
        meta["body_map_skipped_site"] = True
        meta["body_map_selections"] = body_map

    nq = NextQuestion(
        question_id=q_data.get("question_id", f"soc_pain_{axis}"),
        text=q_data.get("text", "दर्द कहाँ है?"),
        input_type=q_data.get("input_type", "voice_touch"),
        options=q_data.get("options"),
        section="socrates",
        progress_pct=25.0 + min(idx * 2.0, 15.0),
        metadata=meta,
    )
    asked = list(state.get("asked_questions", []))
    asked.append(nq.model_dump())
    return {
        "current_node": "socrates_pain",
        "next_question": nq,
        "asked_questions": asked,
        "socrates_axis_index": idx,
        "answers": answers,
    }


def node_ayush_pariksha(state: InterviewState) -> InterviewState:
    """Dashavidha Pariksha 10-stage classical Ayurvedic diagnostic interview."""
    idx = state.get("ayush_stage_index", 0)
    stage = DASHHAVIDHA_STAGES[min(idx, len(DASHHAVIDHA_STAGES) - 1)]
    lang = state.get("language", "hi")
    is_hi = (lang == "hi")

    text = stage["question_hi"] if is_hi else stage["question_en"]
    options = [
        opt["label_hi"] if is_hi else opt["label_en"]
        for opt in stage.get("options", [])
    ]

    nq = NextQuestion(
        question_id=f"ayush_{stage['id']}",
        text=f"[{stage['name']}] {text}",
        input_type="choice",
        options=options,
        section="ayush_pariksha",
        progress_pct=10.0 + (idx + 1) * 8.5,
        metadata={
            "stage_id": stage["id"],
            "stage_name": stage["name"],
            "stage_index": idx,
            "total_stages": len(DASHHAVIDHA_STAGES),
            "category": "ayush_pariksha",
        }
    )
    asked = list(state.get("asked_questions", []))
    asked.append(nq.model_dump())
    return {
        "current_node": "ayush_pariksha",
        "next_question": nq,
        "asked_questions": asked,
        "ayush_stage_index": idx,
    }


def node_socrates_general(state: InterviewState) -> InterviewState:
    """Adapted SOCRATES questions for general complaints (fever, weakness, cough)."""
    idx = state.get("socrates_axis_index", 0)
    axis = GENERAL_AXES[min(idx, len(GENERAL_AXES) - 1)]
    lang = state.get("language", "hi")
    cc = state.get("chief_complaint", "")
    answers = state.get("answers", [])

    q_data = question_generator.generate_question(
        current_section="socrates_general",
        chief_complaint=cc,
        context=answers,
        language=lang,
        socrates_axis=axis,
    )

    nq = NextQuestion(
        question_id=q_data.get("question_id", f"soc_gen_{axis}"),
        text=q_data.get("text", "तकलीफ कितने दिन से है?"),
        input_type=q_data.get("input_type", "voice_touch"),
        options=q_data.get("options"),
        section="socrates",
        progress_pct=25.0 + min(idx * 4.0, 15.0),
        metadata=q_data.get("metadata"),
    )
    asked = list(state.get("asked_questions", []))
    asked.append(nq.model_dump())
    return {
        "current_node": "socrates_general",
        "next_question": nq,
        "asked_questions": asked,
    }


def node_psych_screening(state: InterviewState) -> InterviewState:
    """Psychiatric screening flow for emotional/mental health chief complaints."""
    idx = state.get("socrates_axis_index", 0)
    axis = PSYCH_AXES[min(idx, len(PSYCH_AXES) - 1)]
    lang = state.get("language", "hi")
    cc = state.get("chief_complaint", "")
    answers = state.get("answers", [])

    q_data = question_generator.generate_question(
        current_section="psych_screening",
        chief_complaint=cc,
        context=answers,
        language=lang,
        socrates_axis=axis,
    )

    nq = NextQuestion(
        question_id=q_data.get("question_id", f"soc_psych_{axis}"),
        text=q_data.get("text", "आप कैसा महसूस कर रहे हैं?"),
        input_type=q_data.get("input_type", "voice_touch"),
        options=q_data.get("options"),
        section="socrates",
        progress_pct=25.0 + min(idx * 4.0, 15.0),
        metadata=q_data.get("metadata"),
    )
    asked = list(state.get("asked_questions", []))
    asked.append(nq.model_dump())
    return {
        "current_node": "psych_screening",
        "next_question": nq,
        "asked_questions": asked,
    }


def node_obgyn_history(state: InterviewState) -> InterviewState:
    """OBGYN history flow for female reproductive/obstetric complaints."""
    idx = state.get("socrates_axis_index", 0)
    axis = OBGYN_AXES[min(idx, len(OBGYN_AXES) - 1)]
    lang = state.get("language", "hi")
    cc = state.get("chief_complaint", "")
    answers = state.get("answers", [])

    q_data = question_generator.generate_question(
        current_section="obgyn_history",
        chief_complaint=cc,
        context=answers,
        language=lang,
        socrates_axis=axis,
    )

    nq = NextQuestion(
        question_id=q_data.get("question_id", f"soc_obgyn_{axis}"),
        text=q_data.get("text", "पिछली माहवारी की तारीख क्या थी?"),
        input_type=q_data.get("input_type", "voice_touch"),
        options=q_data.get("options"),
        section="socrates",
        progress_pct=25.0 + min(idx * 5.0, 15.0),
        metadata=q_data.get("metadata"),
    )
    asked = list(state.get("asked_questions", []))
    asked.append(nq.model_dump())
    return {
        "current_node": "obgyn_history",
        "next_question": nq,
        "asked_questions": asked,
    }


def node_pmh(state: InterviewState) -> InterviewState:
    """Past Medical History with Smart Recall."""
    lang = state.get("language", "hi")
    cc = state.get("chief_complaint", "")
    answers = state.get("answers", [])
    extracted_context = state.get("extracted_context", [])

    # Check for existing diagnosis / condition facts
    pmh_entities = [
        e for e in extracted_context
        if e.get("entity_type") in ("diagnosis", "condition", "pmh") or "diag" in e.get("entity_type", "")
    ]

    if pmh_entities:
        best_diag = max(pmh_entities, key=lambda x: float(x.get("confidence", 0.0)))
        conf = float(best_diag.get("confidence", 0.0))
        diag_val = best_diag.get("value", "")

        if conf > 0.8:
            # Rule: Confidence > 0.8 -> confirm briefly
            if lang == "en":
                q_text = f"Your records show a history of {diag_val} — is that still ongoing or resolved?"
                opts = ["Yes, still ongoing", "Resolved / Cured", "Under control with medication"]
            else:
                q_text = f"आपके पिछले रिकॉर्ड में {diag_val} दर्ज है — क्या यह अभी भी है? (Your records show {diag_val} — still ongoing?)"
                opts = ["हाँ, अभी भी है (Ongoing)", "नहीं, अब ठीक है (Resolved)", "दवाई से नियंत्रण में है"]

            nq = NextQuestion(
                question_id="q_pmh_confirm_01",
                text=q_text,
                input_type="choice",
                options=opts,
                section="pmh",
                progress_pct=45.0,
                metadata={
                    "is_smart_recall": True,
                    "recall_mode": "confirm_known_fact",
                    "confidence": conf,
                    "target_entity": diag_val,
                    "entity_id": best_diag.get("entity_id"),
                },
            )
            asked = list(state.get("asked_questions", []))
            asked.append(nq.model_dump())
            return {"current_node": "pmh", "next_question": nq, "asked_questions": asked}

        elif 0.5 <= conf <= 0.8:
            # Rule: Confidence 0.5 - 0.8 -> rephrase as verification
            if lang == "en":
                q_text = f"Our hospital records mention possible history of {diag_val}. Could you please confirm?"
                opts = ["Yes, confirmed", "No, never had this", "Not sure"]
            else:
                q_text = f"रिकॉर्ड में {diag_val} का उल्लेख है। क्या आप इसकी पुष्टि कर सकते हैं?"
                opts = ["हाँ, पुष्टि करता हूँ", "नहीं, ऐसा नहीं है", "निश्चित नहीं"]

            nq = NextQuestion(
                question_id="q_pmh_verify_01",
                text=q_text,
                input_type="choice",
                options=opts,
                section="pmh",
                progress_pct=45.0,
                metadata={
                    "is_smart_recall": True,
                    "recall_mode": "rephrase_verification",
                    "confidence": conf,
                    "target_entity": diag_val,
                    "entity_id": best_diag.get("entity_id"),
                },
            )
            asked = list(state.get("asked_questions", []))
            asked.append(nq.model_dump())
            return {"current_node": "pmh", "next_question": nq, "asked_questions": asked}

    # Default / Confidence < 0.5 -> ask normally
    q_data = question_generator.generate_question(
        current_section="pmh",
        chief_complaint=cc,
        context=answers,
        language=lang,
        extracted_context=extracted_context,
    )
    nq = NextQuestion(
        question_id="q_pmh_01",
        text=q_data.get("text", "क्या आपको पहले से कोई बीमारी है?"),
        input_type="choice",
        options=q_data.get("options", ["मधुमेह", "उच्च रक्तचाप", "थायरॉइड", "कोई नहीं"]),
        section="pmh",
        progress_pct=45.0,
        metadata=q_data.get("metadata"),
    )
    # Smart Recall adaptation: confirm known diagnoses instead of re-asking
    from app.services.smart_recall import smart_recall_service
    nq = smart_recall_service.adapt_question_with_recall("pmh", nq, state.get("extracted_context", []), lang)

    asked = list(state.get("asked_questions", []))
    asked.append(nq.model_dump())
    return {"current_node": "pmh", "next_question": nq, "asked_questions": asked}


def node_medications(state: InterviewState) -> InterviewState:
    """Medications intake with Smart Recall."""
    lang = state.get("language", "hi")
    cc = state.get("chief_complaint", "")
    answers = state.get("answers", [])
    extracted_context = state.get("extracted_context", [])

    # Check for existing medication facts
    med_entities = [
        e for e in extracted_context
        if e.get("entity_type") == "medication" or e.get("generic_name")
    ]

    if med_entities:
        best_med = max(med_entities, key=lambda x: float(x.get("confidence", 0.0)))
        conf = float(best_med.get("confidence", 0.0))
        med_val = best_med.get("generic_name") or best_med.get("value", "")

        if conf > 0.8:
            # Rule: Confidence > 0.8 -> confirm briefly
            if lang == "en":
                q_text = f"Your records show you take {med_val} — is that still current?"
                opts = ["Yes, still taking it", "No, stopped taking it", "Dose has changed", "Taking other medications too"]
            else:
                q_text = f"आपके पिछले रिकॉर्ड के अनुसार आप {med_val} लेते हैं — क्या यह अभी भी जारी है? (Your records show you take {med_val} — is that still current?)"
                opts = ["हाँ, अभी भी ले रहा हूँ (Yes, still current)", "नहीं, बंद कर दी है (Stopped)", "डोज़ बदल गई है (Dose changed)", "अन्य दवाइयाँ भी हैं"]

            nq = NextQuestion(
                question_id="q_med_confirm_01",
                text=q_text,
                input_type="choice",
                options=opts,
                section="medications",
                progress_pct=58.0,
                metadata={
                    "is_smart_recall": True,
                    "recall_mode": "confirm_known_fact",
                    "confidence": conf,
                    "target_entity": med_val,
                    "entity_id": best_med.get("entity_id"),
                },
            )
            asked = list(state.get("asked_questions", []))
            asked.append(nq.model_dump())
            return {"current_node": "medications", "next_question": nq, "asked_questions": asked}

        elif 0.5 <= conf <= 0.8:
            # Rule: Confidence 0.5 - 0.8 -> rephrase as verification
            if lang == "en":
                q_text = f"Our hospital records mention you may be taking {med_val}. Could you please verify if you take this?"
                opts = ["Yes, I take this", "No, I do not take this", "Taking different medicine"]
            else:
                q_text = f"रिकॉर्ड में {med_val} का उल्लेख है। क्या आप पुष्टि कर सकते हैं कि आप यह दवाई लेते हैं?"
                opts = ["हाँ, यह दवाई लेता हूँ", "नहीं, यह नहीं लेता", "कोई अन्य दवाई लेता हूँ"]

            nq = NextQuestion(
                question_id="q_med_verify_01",
                text=q_text,
                input_type="choice",
                options=opts,
                section="medications",
                progress_pct=58.0,
                metadata={
                    "is_smart_recall": True,
                    "recall_mode": "rephrase_verification",
                    "confidence": conf,
                    "target_entity": med_val,
                    "entity_id": best_med.get("entity_id"),
                },
            )
            asked = list(state.get("asked_questions", []))
            asked.append(nq.model_dump())
            return {"current_node": "medications", "next_question": nq, "asked_questions": asked}

    # Default / Confidence < 0.5 -> ask normally
    q_data = question_generator.generate_question(
        current_section="medications",
        chief_complaint=cc,
        context=answers,
        language=lang,
        extracted_context=extracted_context,
    )
    nq = NextQuestion(
        question_id="q_med_01",
        text=q_data.get("text", "क्या आप कोई नियमित दवाई ले रहे हैं?"),
        input_type="voice_touch",
        options=q_data.get("options", ["हाँ", "नहीं"]),
        section="medications",
        progress_pct=58.0,
        metadata=q_data.get("metadata"),
    )
    # Smart Recall adaptation: confirm known active prescriptions
    from app.services.smart_recall import smart_recall_service
    nq = smart_recall_service.adapt_question_with_recall("medications", nq, state.get("extracted_context", []), lang)

    asked = list(state.get("asked_questions", []))
    asked.append(nq.model_dump())
    return {"current_node": "medications", "next_question": nq, "asked_questions": asked}



def node_allergies(state: InterviewState) -> InterviewState:
    """Allergies screen."""
    lang = state.get("language", "hi")
    cc = state.get("chief_complaint", "")
    answers = state.get("answers", [])
    q_data = question_generator.generate_question(
        current_section="allergies",
        chief_complaint=cc,
        context=answers,
        language=lang,
    )
    nq = NextQuestion(
        question_id="q_all_01",
        text=q_data.get("text", "क्या आपको किसी दवाई से एलर्जी है?"),
        input_type="yes_no",
        options=q_data.get("options", ["हाँ", "नहीं"]),
        section="allergies",
        progress_pct=70.0,
        metadata=q_data.get("metadata"),
    )
    # Smart Recall adaptation: verify existing documented allergies
    from app.services.smart_recall import smart_recall_service
    nq = smart_recall_service.adapt_question_with_recall("allergies", nq, state.get("extracted_context", []), lang)

    asked = list(state.get("asked_questions", []))
    asked.append(nq.model_dump())
    return {"current_node": "allergies", "next_question": nq, "asked_questions": asked}



def node_family_hx(state: InterviewState) -> InterviewState:
    """Family history."""
    lang = state.get("language", "hi")
    cc = state.get("chief_complaint", "")
    answers = state.get("answers", [])
    q_data = question_generator.generate_question(
        current_section="family_hx",
        chief_complaint=cc,
        context=answers,
        language=lang,
    )
    nq = NextQuestion(
        question_id="q_fam_01",
        text=q_data.get("text", "क्या परिवार में किसी को गंभीर बीमारी है?"),
        input_type="voice_touch",
        options=q_data.get("options", ["हाँ", "नहीं"]),
        section="family_hx",
        progress_pct=80.0,
        metadata=q_data.get("metadata"),
    )
    asked = list(state.get("asked_questions", []))
    asked.append(nq.model_dump())
    return {"current_node": "family_hx", "next_question": nq, "asked_questions": asked}


def node_personal_hx(state: InterviewState) -> InterviewState:
    """Personal habits (smoking, tobacco, alcohol)."""
    lang = state.get("language", "hi")
    cc = state.get("chief_complaint", "")
    answers = state.get("answers", [])
    q_data = question_generator.generate_question(
        current_section="personal_hx",
        chief_complaint=cc,
        context=answers,
        language=lang,
    )
    nq = NextQuestion(
        question_id="q_per_01",
        text=q_data.get("text", "धूम्रपान, तंबाकू या शराब का सेवन?"),
        input_type="choice",
        options=q_data.get("options", ["तंबाकू / बीड़ी", "शराब", "कोई नशा नहीं"]),
        section="personal_hx",
        progress_pct=90.0,
        metadata=q_data.get("metadata"),
    )
    asked = list(state.get("asked_questions", []))
    asked.append(nq.model_dump())
    return {"current_node": "personal_hx", "next_question": nq, "asked_questions": asked}


def node_ros(state: InterviewState) -> InterviewState:
    """Review of systems."""
    lang = state.get("language", "hi")
    cc = state.get("chief_complaint", "")
    answers = state.get("answers", [])
    q_data = question_generator.generate_question(
        current_section="ros",
        chief_complaint=cc,
        context=answers,
        language=lang,
    )
    nq = NextQuestion(
        question_id="q_ros_01",
        text=q_data.get("text", "अन्य कोई शिकायत जैसे चक्कर या कमजोरी?"),
        input_type="voice_touch",
        options=q_data.get("options", ["हाँ", "नहीं"]),
        section="ros",
        progress_pct=95.0,
        metadata=q_data.get("metadata"),
    )
    asked = list(state.get("asked_questions", []))
    asked.append(nq.model_dump())
    return {"current_node": "ros", "next_question": nq, "asked_questions": asked}


def node_complete(state: InterviewState) -> InterviewState:
    """Interview completion."""
    lang = state.get("language", "hi")
    cc = state.get("chief_complaint", "")
    answers = state.get("answers", [])
    q_data = question_generator.generate_question(
        current_section="complete",
        chief_complaint=cc,
        context=answers,
        language=lang,
    )
    nq = NextQuestion(
        question_id="q_end_01",
        text=q_data.get("text", "धन्यवाद! जानकारी दर्ज कर ली गई है।"),
        input_type="voice_touch",
        options=["ठीक है (OK)"],
        section="complete",
        progress_pct=100.0,
        metadata=q_data.get("metadata"),
    )
    asked = list(state.get("asked_questions", []))
    asked.append(nq.model_dump())
    return {
        "current_node": "complete",
        "is_complete": True,
        "next_question": nq,
        "asked_questions": asked,
    }


def build_interview_graph() -> Any:
    """
    Builds the full LangGraph state machine with adaptive SOCRATES routing and AYUSH Pariksha.
    """
    builder = StateGraph(InterviewState)

    builder.add_node("intake", node_intake)
    builder.add_node("chief_complaint", node_chief_complaint)
    builder.add_node("categorize_complaint", node_categorize_complaint)
    builder.add_node("ayush_pariksha", node_ayush_pariksha)
    builder.add_node("socrates_pain", node_socrates_pain)
    builder.add_node("socrates_general", node_socrates_general)
    builder.add_node("psych_screening", node_psych_screening)
    builder.add_node("obgyn_history", node_obgyn_history)
    builder.add_node("pmh", node_pmh)
    builder.add_node("medications", node_medications)
    builder.add_node("allergies", node_allergies)
    builder.add_node("family_hx", node_family_hx)
    builder.add_node("personal_hx", node_personal_hx)
    builder.add_node("ros", node_ros)
    builder.add_node("complete", node_complete)

    # Wiring edges
    builder.add_edge(START, "intake")
    builder.add_edge("intake", "chief_complaint")
    builder.add_edge("chief_complaint", "categorize_complaint")

    # Conditional branching from categorize_complaint
    builder.add_conditional_edges(
        "categorize_complaint",
        route_complaint,
        {
            "ayush_pariksha": "ayush_pariksha",
            "socrates_pain": "socrates_pain",
            "socrates_general": "socrates_general",
            "psych_screening": "psych_screening",
            "obgyn_history": "obgyn_history",
        }
    )

    # AYUSH flow leads directly to completion once 10 stages conclude
    builder.add_edge("ayush_pariksha", "complete")

    # All allopathic branches flow to PMH
    builder.add_edge("socrates_pain", "pmh")
    builder.add_edge("socrates_general", "pmh")
    builder.add_edge("psych_screening", "pmh")
    builder.add_edge("obgyn_history", "pmh")

    # Linear progression to completion
    builder.add_edge("pmh", "medications")
    builder.add_edge("medications", "allergies")
    builder.add_edge("allergies", "family_hx")
    builder.add_edge("family_hx", "personal_hx")
    builder.add_edge("personal_hx", "ros")
    builder.add_edge("ros", "complete")
    builder.add_edge("complete", END)

    return builder.compile()


NODE_HANDLERS = {
    "intake": node_intake,
    "chief_complaint": node_chief_complaint,
    "categorize_complaint": node_categorize_complaint,
    "ayush_pariksha": node_ayush_pariksha,
    "socrates_pain": node_socrates_pain,
    "socrates_general": node_socrates_general,
    "psych_screening": node_psych_screening,
    "obgyn_history": node_obgyn_history,
    "pmh": node_pmh,
    "medications": node_medications,
    "allergies": node_allergies,
    "family_hx": node_family_hx,
    "personal_hx": node_personal_hx,
    "ros": node_ros,
    "complete": node_complete,
}


class InterviewEngine:
    """
    Session manager orchestrating the adaptive clinical history interview.
    """
    def __init__(self):
        self.sessions: dict[str, InterviewState] = {}
        self.graph = build_interview_graph()

    def get_or_create_session(
        self,
        session_id: str,
        language: str = "hi",
        extracted_context: list[dict[str, Any]] | None = None,
    ) -> InterviewState:
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "session_id": session_id,
                "current_node": "intake",
                "language": language,
                "chief_complaint": "",
                "chief_complaint_category": "general",
                "asked_questions": [],
                "answers": [],
                "extracted_context": extracted_context or [],
                "red_flags_triggered": [],
                "confirmed_facts": [],
                "is_paused": False,
                "paused_reason": None,
                "socrates_axis_index": 0,
                "last_answer": None,
                "next_question": None,
                "is_complete": False,
                "body_map_selections": [],
                "interview_mode": "allopathic",
                "ayush_stage_index": 0,
                "ayush_answers": {},
                "prakriti_result": None,
                "is_caregiver": False,
                "caregiver_name": None,
                "caregiver_relationship": None,
            }
        elif extracted_context:
            self.sessions[session_id]["extracted_context"] = extracted_context
        return self.sessions[session_id]

    def cleanup_session(self, session_id: str) -> None:
        """Removes session state from in-memory store to prevent memory leaks."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Session {session_id}: Cleaned up in-memory interview state.")

    def set_body_map(self, session_id: str, selections: list[str]) -> None:
        """Sets body map anatomical selections and injects into LangGraph state."""
        state = self.get_or_create_session(session_id)
        state["body_map_selections"] = selections
        logger.info(f"Session {session_id}: Injected body map selections: {selections}")

    def set_interview_mode(self, session_id: str, mode: str) -> None:
        """Sets interview mode ('allopathic' or 'ayush')."""
        state = self.get_or_create_session(session_id)
        state["interview_mode"] = mode
        logger.info(f"Session {session_id}: Set interview mode to: {mode}")

    def start_interview(
        self,
        session_id: str = "dev-test-001",
        language: str = "hi",
        extracted_context: list[dict[str, Any]] | None = None,
        body_map_selections: list[str] | None = None,
        interview_mode: str = "allopathic",
        is_caregiver: bool = False,
        caregiver_name: str | None = None,
        caregiver_relationship: str | None = None,
    ) -> NextQuestion:
        state = self.get_or_create_session(session_id, language, extracted_context)
        state["language"] = language
        if extracted_context is not None:
            state["extracted_context"] = extracted_context
        if body_map_selections is not None:
            state["body_map_selections"] = body_map_selections
        if interview_mode:
            state["interview_mode"] = interview_mode
        if is_caregiver:
            state["is_caregiver"] = True
            state["caregiver_name"] = caregiver_name
            state["caregiver_relationship"] = caregiver_relationship

        # Run through intake and prompt for chief_complaint
        state.update(node_intake(state))
        cc_result = node_chief_complaint(state)
        state.update(cc_result)
        nq = state.get("next_question")
        assert nq is not None
        return nq

    def step(
        self,
        session_id: str,
        answer_text: str,
        language: str | None = None,
        verbatim_voice: str | None = None,
    ) -> NextQuestion:
        state = self.get_or_create_session(session_id)
        if language:
            state["language"] = language

        # If paused by emergency red-flag, do not advance until resumed
        paused_q = state.get("next_question")
        if state.get("is_paused") and paused_q is not None:
            return paused_q

        curr_node = state.get("current_node", "chief_complaint")
        state["last_answer"] = answer_text

        # Record answer
        answers = list(state.get("answers", []))
        last_q = state.get("next_question")

        # Track Smart Recall fact verification / confirmation
        if last_q and last_q.metadata and last_q.metadata.get("is_smart_recall"):
            target_entity = last_q.metadata.get("target_entity", "")
            is_confirmed = any(
                pos in answer_text.lower()
                for pos in ["हाँ", "yes", "still", "current", "जारी", "लेता हूँ", "हूँ", "ongoing"]
            ) and not any(
                neg in answer_text.lower()
                for neg in ["नहीं", "no", "बंद", "stopped", "not"]
            )
            confirmed_facts = list(state.get("confirmed_facts", []))
            confirmed_facts.append({
                "entity": target_entity,
                "entity_id": last_q.metadata.get("entity_id"),
                "status": "confirmed" if is_confirmed else "corrected",
                "patient_answer": answer_text,
                "recall_mode": last_q.metadata.get("recall_mode"),
            })
            state["confirmed_facts"] = confirmed_facts

        answers.append({
            "node": curr_node,
            "question_id": last_q.question_id if last_q else "unknown",
            "question_text": last_q.text if last_q else "",
            "answer_text": answer_text,
            "verbatim_voice": verbatim_voice,
            "language": state["language"],
        })
        state["answers"] = answers

        # State transitions
        if curr_node == "chief_complaint":
            state["chief_complaint"] = answer_text
            cat_result = node_categorize_complaint(state)
            state.update(cat_result)
            next_node_name = route_complaint(state)
            state["current_node"] = next_node_name
            handler = NODE_HANDLERS[next_node_name]
            result = handler(state)
            state.update(result)

        elif curr_node == "ayush_pariksha":
            ayush_answers = dict(state.get("ayush_answers", {}))
            idx = state.get("ayush_stage_index", 0)
            stage = DASHHAVIDHA_STAGES[min(idx, len(DASHHAVIDHA_STAGES) - 1)]
            ayush_answers[stage["id"]] = answer_text
            state["ayush_answers"] = ayush_answers

            if idx < len(DASHHAVIDHA_STAGES) - 1:
                state["ayush_stage_index"] = idx + 1
                state["current_node"] = "ayush_pariksha"
                result = node_ayush_pariksha(state)
                state.update(result)
            else:
                from app.services.ayush_service import evaluate_prakriti_and_dosha
                prakriti_res = evaluate_prakriti_and_dosha(ayush_answers)
                state["prakriti_result"] = prakriti_res
                state["current_node"] = "complete"
                result = node_complete(state)
                state.update(result)

        elif curr_node in ["socrates_pain", "socrates_general", "psych_screening", "obgyn_history"]:
            # Advance to PMH
            state["current_node"] = "pmh"
            result = node_pmh(state)
            state.update(result)

        elif curr_node == "pmh":
            state["current_node"] = "medications"
            result = node_medications(state)
            state.update(result)

        elif curr_node == "medications":
            state["current_node"] = "allergies"
            result = node_allergies(state)
            state.update(result)

        elif curr_node == "allergies":
            state["current_node"] = "family_hx"
            result = node_family_hx(state)
            state.update(result)

        elif curr_node == "family_hx":
            state["current_node"] = "personal_hx"
            result = node_personal_hx(state)
            state.update(result)

        elif curr_node == "personal_hx":
            state["current_node"] = "ros"
            result = node_ros(state)
            state.update(result)

        elif curr_node == "ros":
            state["current_node"] = "complete"
            result = node_complete(state)
            state.update(result)

        else:
            state["current_node"] = "complete"
            result = node_complete(state)
            state.update(result)

        nq = state.get("next_question")
        assert nq is not None
        return nq


interview_engine = InterviewEngine()
