"""
LangGraph Clinical Interview Engine
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

State machine orchestrating the clinical history-taking flow in standard medical sequence:
chief_complaint -> socrates_branch -> pmh -> medications -> allergies -> family_hx -> personal_hx -> ros -> complete
"""

import logging
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.shared.schemas import NextQuestion

logger = logging.getLogger("medikiosk.interview_engine")

InputType = Literal["voice_touch", "choice", "scale", "yes_no"]


class PromptConfig(TypedDict, total=False):
    hi: str
    en: str
    type: InputType
    options: list[str]
    progress: float


class InterviewState(TypedDict, total=False):
    session_id: str
    current_node: str
    language: str
    chief_complaint: str | None
    socrates: dict[str, Any]
    pmh: list[str]
    medications: list[str]
    allergies: list[str]
    family_hx: list[str]
    personal_hx: list[str]
    ros: dict[str, Any]
    history: list[dict[str, Any]]
    last_answer: str | None
    next_question: NextQuestion | None
    is_complete: bool


# Localized default question texts for Hindi and English
DEFAULT_PROMPTS: dict[str, PromptConfig] = {
    "chief_complaint": {
        "hi": "नमस्ते, आज आपको अस्पताल किस तकलीफ या समस्या के कारण आना पड़ा?",
        "en": "Hello, what primary symptom or health concern brings you to the hospital today?",
        "type": "voice_touch",
        "progress": 10.0,
    },
    "socrates_branch": {
        "hi": "यह दर्द या तकलीफ शरीर में ठीक किस जगह पर महसूस हो रही है, और यह कब शुरू हुई?",
        "en": "Where exactly is this pain or symptom located, and when did it first begin?",
        "type": "voice_touch",
        "progress": 25.0,
    },
    "pmh": {
        "hi": "क्या आपको पहले से कोई पुरानी बीमारी है (जैसे बीपी, शुगर, थायरॉइड, अस्थमा)?",
        "en": "Do you have any past medical conditions (such as diabetes, hypertension, thyroid, asthma)?",
        "type": "choice",
        "options": ["मधुमेह (Diabetes)", "उच्च रक्तचाप (Hypertension)", "थायरॉइड (Thyroid)", "अस्थमा (Asthma)", "कोई नहीं (None)"],
        "progress": 40.0,
    },
    "medications": {
        "hi": "क्या आप वर्तमान में नियमित रूप से कोई दवाई या गोली ले रहे हैं?",
        "en": "Are you currently taking any regular medications or tablets?",
        "type": "voice_touch",
        "progress": 55.0,
    },
    "allergies": {
        "hi": "क्या आपको किसी दवाई, इंजेक्शन या खाने की चीज़ से कोई एलर्जी है?",
        "en": "Do you have any known allergies to medicines, injections, or food?",
        "type": "yes_no",
        "options": ["हाँ (Yes)", "नहीं (No)"],
        "progress": 70.0,
    },
    "family_hx": {
        "hi": "क्या आपके परिवार (माता-पिता, भाई-बहन) में किसी को दिल की बीमारी, शुगर या कैंसर का इतिहास है?",
        "en": "Is there a family history of heart disease, diabetes, or cancer among immediate relatives?",
        "type": "voice_touch",
        "progress": 80.0,
    },
    "personal_hx": {
        "hi": "आपकी जीवनशैली से जुड़ी आदतें (धूम्रपान, तंबाकू, शराब सेवन आदि)?",
        "en": "Any personal habits (smoking, tobacco, alcohol consumption)?",
        "type": "choice",
        "options": ["तंबाकू / बीड़ी (Tobacco/Bidi)", "शराब (Alcohol)", "दोनों (Both)", "कोई नशा नहीं (None)"],
        "progress": 90.0,
    },
    "ros": {
        "hi": "क्या इनके अलावा बुखार, चक्कर आना, वजन घटना या भूख में कमी जैसी कोई अन्य शिकायत है?",
        "en": "Apart from this, any systemic symptoms like fever, dizziness, weight loss, or appetite changes?",
        "type": "voice_touch",
        "progress": 95.0,
    },
    "complete": {
        "hi": "धन्यवाद! आपकी प्राथमिक जानकारी दर्ज कर ली गई है। कृपया डॉक्टर के केबिन के बाहर प्रतीक्षा करें।",
        "en": "Thank you! Your intake is complete. A clinical summary has been generated for the doctor.",
        "type": "voice_touch",
        "progress": 100.0,
    },
}


def node_chief_complaint(state: InterviewState) -> InterviewState:
    lang = state.get("language", "hi")
    prompt_cfg = DEFAULT_PROMPTS["chief_complaint"]
    text = prompt_cfg.get("en", "") if lang == "en" else prompt_cfg["hi"]
    q = NextQuestion(
        question_id="q_cc_01",
        text=text,
        input_type=prompt_cfg.get("type", "voice_touch"),
        section="chief_complaint",
        progress_pct=prompt_cfg.get("progress", 10.0),
    )
    cc = state.get("last_answer") or state.get("chief_complaint")
    return {
        "current_node": "chief_complaint",
        "chief_complaint": cc,
        "next_question": q,
    }


def node_socrates_branch(state: InterviewState) -> InterviewState:
    lang = state.get("language", "hi")
    prompt_cfg = DEFAULT_PROMPTS["socrates_branch"]
    text = prompt_cfg.get("en", "") if lang == "en" else prompt_cfg["hi"]
    q = NextQuestion(
        question_id="q_soc_01",
        text=text,
        input_type=prompt_cfg.get("type", "voice_touch"),
        section="socrates",
        progress_pct=prompt_cfg.get("progress", 25.0),
    )
    socrates = dict(state.get("socrates", {}))
    ans = state.get("last_answer")
    if ans:
        socrates["site_onset"] = ans
    return {
        "current_node": "socrates_branch",
        "socrates": socrates,
        "next_question": q,
    }


def node_pmh(state: InterviewState) -> InterviewState:
    lang = state.get("language", "hi")
    prompt_cfg = DEFAULT_PROMPTS["pmh"]
    text = prompt_cfg.get("en", "") if lang == "en" else prompt_cfg["hi"]
    q = NextQuestion(
        question_id="q_pmh_01",
        text=text,
        input_type=prompt_cfg.get("type", "choice"),
        options=prompt_cfg.get("options"),
        section="pmh",
        progress_pct=prompt_cfg.get("progress", 40.0),
    )
    pmh = list(state.get("pmh", []))
    ans = state.get("last_answer")
    if ans:
        pmh.append(ans)
    return {
        "current_node": "pmh",
        "pmh": pmh,
        "next_question": q,
    }


def node_medications(state: InterviewState) -> InterviewState:
    lang = state.get("language", "hi")
    prompt_cfg = DEFAULT_PROMPTS["medications"]
    text = prompt_cfg.get("en", "") if lang == "en" else prompt_cfg["hi"]
    q = NextQuestion(
        question_id="q_med_01",
        text=text,
        input_type=prompt_cfg.get("type", "voice_touch"),
        section="medications",
        progress_pct=prompt_cfg.get("progress", 55.0),
    )
    meds = list(state.get("medications", []))
    ans = state.get("last_answer")
    if ans:
        meds.append(ans)
    return {
        "current_node": "medications",
        "medications": meds,
        "next_question": q,
    }


def node_allergies(state: InterviewState) -> InterviewState:
    lang = state.get("language", "hi")
    prompt_cfg = DEFAULT_PROMPTS["allergies"]
    text = prompt_cfg.get("en", "") if lang == "en" else prompt_cfg["hi"]
    q = NextQuestion(
        question_id="q_all_01",
        text=text,
        input_type=prompt_cfg.get("type", "yes_no"),
        options=prompt_cfg.get("options"),
        section="allergies",
        progress_pct=prompt_cfg.get("progress", 70.0),
    )
    allergies = list(state.get("allergies", []))
    ans = state.get("last_answer")
    if ans:
        allergies.append(ans)
    return {
        "current_node": "allergies",
        "allergies": allergies,
        "next_question": q,
    }


def node_family_hx(state: InterviewState) -> InterviewState:
    lang = state.get("language", "hi")
    prompt_cfg = DEFAULT_PROMPTS["family_hx"]
    text = prompt_cfg.get("en", "") if lang == "en" else prompt_cfg["hi"]
    q = NextQuestion(
        question_id="q_fam_01",
        text=text,
        input_type=prompt_cfg.get("type", "voice_touch"),
        section="family_hx",
        progress_pct=prompt_cfg.get("progress", 80.0),
    )
    fam = list(state.get("family_hx", []))
    ans = state.get("last_answer")
    if ans:
        fam.append(ans)
    return {
        "current_node": "family_hx",
        "family_hx": fam,
        "next_question": q,
    }


def node_personal_hx(state: InterviewState) -> InterviewState:
    lang = state.get("language", "hi")
    prompt_cfg = DEFAULT_PROMPTS["personal_hx"]
    text = prompt_cfg.get("en", "") if lang == "en" else prompt_cfg["hi"]
    q = NextQuestion(
        question_id="q_per_01",
        text=text,
        input_type=prompt_cfg.get("type", "choice"),
        options=prompt_cfg.get("options"),
        section="personal_hx",
        progress_pct=prompt_cfg.get("progress", 90.0),
    )
    per = list(state.get("personal_hx", []))
    ans = state.get("last_answer")
    if ans:
        per.append(ans)
    return {
        "current_node": "personal_hx",
        "personal_hx": per,
        "next_question": q,
    }


def node_ros(state: InterviewState) -> InterviewState:
    lang = state.get("language", "hi")
    prompt_cfg = DEFAULT_PROMPTS["ros"]
    text = prompt_cfg.get("en", "") if lang == "en" else prompt_cfg["hi"]
    q = NextQuestion(
        question_id="q_ros_01",
        text=text,
        input_type=prompt_cfg.get("type", "voice_touch"),
        section="ros",
        progress_pct=prompt_cfg.get("progress", 95.0),
    )
    ros = dict(state.get("ros", {}))
    ans = state.get("last_answer")
    if ans:
        ros["general"] = ans
    return {
        "current_node": "ros",
        "ros": ros,
        "next_question": q,
    }


def node_complete(state: InterviewState) -> InterviewState:
    lang = state.get("language", "hi")
    prompt_cfg = DEFAULT_PROMPTS["complete"]
    text = prompt_cfg.get("en", "") if lang == "en" else prompt_cfg["hi"]
    q = NextQuestion(
        question_id="q_end_01",
        text=text,
        input_type=prompt_cfg.get("type", "voice_touch"),
        section="complete",
        progress_pct=prompt_cfg.get("progress", 100.0),
    )
    return {
        "current_node": "complete",
        "is_complete": True,
        "next_question": q,
    }


def build_interview_graph() -> Any:
    """
    Builds the compiled LangGraph StateGraph connecting all 9 nodes in sequence.
    """
    builder = StateGraph(InterviewState)

    # 1. Add all 9 nodes
    builder.add_node("chief_complaint", node_chief_complaint)
    builder.add_node("socrates_branch", node_socrates_branch)
    builder.add_node("pmh", node_pmh)
    builder.add_node("medications", node_medications)
    builder.add_node("allergies", node_allergies)
    builder.add_node("family_hx", node_family_hx)
    builder.add_node("personal_hx", node_personal_hx)
    builder.add_node("ros", node_ros)
    builder.add_node("complete", node_complete)

    # 2. Add sequential edges as requested
    builder.add_edge(START, "chief_complaint")
    builder.add_edge("chief_complaint", "socrates_branch")
    builder.add_edge("socrates_branch", "pmh")
    builder.add_edge("pmh", "medications")
    builder.add_edge("medications", "allergies")
    builder.add_edge("allergies", "family_hx")
    builder.add_edge("family_hx", "personal_hx")
    builder.add_edge("personal_hx", "ros")
    builder.add_edge("ros", "complete")
    builder.add_edge("complete", END)

    return builder.compile()


# Sequence list for step navigation
NODE_SEQUENCE = [
    "chief_complaint",
    "socrates_branch",
    "pmh",
    "medications",
    "allergies",
    "family_hx",
    "personal_hx",
    "ros",
    "complete",
]

NODE_HANDLERS = {
    "chief_complaint": node_chief_complaint,
    "socrates_branch": node_socrates_branch,
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
    Stateful manager for active Kiosk interview sessions.
    """
    def __init__(self):
        self.sessions: dict[str, InterviewState] = {}
        self.graph = build_interview_graph()

    def get_or_create_session(self, session_id: str, language: str = "hi") -> InterviewState:
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "session_id": session_id,
                "current_node": "",
                "language": language,
                "chief_complaint": None,
                "socrates": {},
                "pmh": [],
                "medications": [],
                "allergies": [],
                "family_hx": [],
                "personal_hx": [],
                "ros": {},
                "history": [],
                "last_answer": None,
                "next_question": None,
                "is_complete": False,
            }
        return self.sessions[session_id]

    def start_interview(self, session_id: str, language: str = "hi") -> NextQuestion:
        state = self.get_or_create_session(session_id, language)
        state["language"] = language
        result = node_chief_complaint(state)
        state.update(result)
        nq = state.get("next_question")
        assert nq is not None
        return nq

    def step(self, session_id: str, answer_text: str, language: str | None = None) -> NextQuestion:
        state = self.get_or_create_session(session_id)
        if language:
            state["language"] = language

        curr = state.get("current_node", "")
        state["last_answer"] = answer_text

        # Record into history
        if "history" not in state:
            state["history"] = []
        state["history"].append({
            "node": curr,
            "answer": answer_text,
        })

        # Advance to next node in NODE_SEQUENCE
        if curr in NODE_SEQUENCE:
            idx = NODE_SEQUENCE.index(curr)
            next_idx = min(idx + 1, len(NODE_SEQUENCE) - 1)
            next_node_name = NODE_SEQUENCE[next_idx]
        else:
            next_node_name = "chief_complaint"

        handler = NODE_HANDLERS[next_node_name]
        result = handler(state)
        state.update(result)
        nq = state.get("next_question")
        assert nq is not None
        return nq


# Global engine instance
interview_engine = InterviewEngine()
