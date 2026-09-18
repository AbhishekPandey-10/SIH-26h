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
    extracted_context: list[dict[str, Any]]  # filled later by Smart Recall
    red_flags_triggered: list[dict[str, Any]]

    # Step navigation helpers
    socrates_axis_index: int
    last_answer: str | None
    next_question: NextQuestion | None
    is_complete: bool


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


def route_complaint(state: InterviewState) -> Literal["socrates_pain", "socrates_general", "psych_screening", "obgyn_history"]:
    """Conditional router based on categorized chief complaint."""
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
    """SOCRATES pain framework questions."""
    idx = state.get("socrates_axis_index", 0)
    axis = PAIN_AXES[min(idx, len(PAIN_AXES) - 1)]
    lang = state.get("language", "hi")
    cc = state.get("chief_complaint", "")
    answers = state.get("answers", [])

    q_data = question_generator.generate_question(
        current_section="socrates_pain",
        chief_complaint=cc,
        context=answers,
        language=lang,
        socrates_axis=axis,
    )

    nq = NextQuestion(
        question_id=q_data.get("question_id", f"soc_pain_{axis}"),
        text=q_data.get("text", "दर्द कहाँ है?"),
        input_type=q_data.get("input_type", "voice_touch"),
        options=q_data.get("options"),
        section="socrates",
        progress_pct=25.0 + min(idx * 2.0, 15.0),
        metadata=q_data.get("metadata"),
    )
    asked = list(state.get("asked_questions", []))
    asked.append(nq.model_dump())
    return {
        "current_node": "socrates_pain",
        "next_question": nq,
        "asked_questions": asked,
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
    """Past Medical History."""
    lang = state.get("language", "hi")
    cc = state.get("chief_complaint", "")
    answers = state.get("answers", [])
    q_data = question_generator.generate_question(
        current_section="pmh",
        chief_complaint=cc,
        context=answers,
        language=lang,
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
    asked = list(state.get("asked_questions", []))
    asked.append(nq.model_dump())
    return {"current_node": "pmh", "next_question": nq, "asked_questions": asked}


def node_medications(state: InterviewState) -> InterviewState:
    """Medications intake."""
    lang = state.get("language", "hi")
    cc = state.get("chief_complaint", "")
    answers = state.get("answers", [])
    q_data = question_generator.generate_question(
        current_section="medications",
        chief_complaint=cc,
        context=answers,
        language=lang,
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
    Builds the full LangGraph state machine with adaptive SOCRATES routing.
    """
    builder = StateGraph(InterviewState)

    builder.add_node("intake", node_intake)
    builder.add_node("chief_complaint", node_chief_complaint)
    builder.add_node("categorize_complaint", node_categorize_complaint)
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
            "socrates_pain": "socrates_pain",
            "socrates_general": "socrates_general",
            "psych_screening": "psych_screening",
            "obgyn_history": "obgyn_history",
        }
    )

    # All branches flow to PMH
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

    def get_or_create_session(self, session_id: str, language: str = "hi") -> InterviewState:
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "session_id": session_id,
                "current_node": "intake",
                "language": language,
                "chief_complaint": "",
                "chief_complaint_category": "general",
                "asked_questions": [],
                "answers": [],
                "extracted_context": [],
                "red_flags_triggered": [],
                "socrates_axis_index": 0,
                "last_answer": None,
                "next_question": None,
                "is_complete": False,
            }
        return self.sessions[session_id]

    def start_interview(self, session_id: str = "dev-test-001", language: str = "hi") -> NextQuestion:
        state = self.get_or_create_session(session_id, language)
        state["language"] = language
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

        curr_node = state.get("current_node", "chief_complaint")
        state["last_answer"] = answer_text

        # Record answer
        answers = list(state.get("answers", []))
        last_q = state.get("next_question")
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
