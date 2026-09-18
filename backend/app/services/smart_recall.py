"""
Smart Recall Service (Zero-Repeat OPD Interview Engine)
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Extracts historical clinical entities from scanned documents and past visits,
injects them into the LangGraph interview state, and transforms generic intake questions
into confirmation prompts ("Your records show you take Metformin 500mg — is that still current?").
"""

import logging
from typing import Any, Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ExtractedEntityModel, Session
from app.shared.schemas import NextQuestion

logger = logging.getLogger("medikiosk.smart_recall")


class SmartRecallService:
    """
    Injects pre-scanned prescription and lab entities into interview memory.
    Prevents redundant questioning and verifies existing treatments.
    """

    async def load_patient_extracted_context(
        self,
        session_id: str,
        db: AsyncSession,
    ) -> List[Dict[str, Any]]:
        """
        Loads all extracted entities linked to this session, or to the same patient
        across historical visits.
        """
        # Find patient_id for session
        sess_stmt = select(Session).where(Session.id == session_id)
        sess_res = await db.execute(sess_stmt)
        sess = sess_res.scalar_one_or_none()

        patient_sessions = [session_id]
        if sess and sess.patient_id:
            # Find all sessions for this patient
            p_stmt = select(Session.id).where(Session.patient_id == sess.patient_id)
            p_res = await db.execute(p_stmt)
            patient_sessions = list(p_res.scalars().all()) or [session_id]

        # Fetch extracted entities
        stmt = (
            select(ExtractedEntityModel)
            .where(ExtractedEntityModel.session_id.in_(patient_sessions))
            .order_by(ExtractedEntityModel.confidence.desc())
        )
        res = await db.execute(stmt)
        entities = res.scalars().all()

        context = []
        for e in entities:
            context.append({
                "entity_id": e.id,
                "document_id": e.document_id,
                "type": e.entity_type,
                "value": e.value,
                "generic_name": e.generic_name,
                "date": e.date,
                "confidence": e.confidence,
                "bounding_box": e.bounding_box,
            })

        logger.info(f"Smart Recall injected {len(context)} historical entities into session {session_id}")
        return context

    def adapt_question_with_recall(
        self,
        section: str,
        default_question: NextQuestion,
        extracted_context: List[Dict[str, Any]],
        language: str = "hi",
    ) -> NextQuestion:
        """
        Examines extracted_context for known facts matching the current section.
        If high-confidence (>0.8) entity exists, replaces generic question with confirmation prompt.
        """
        if not extracted_context:
            return default_question

        is_hi = (language == "hi")

        if section == "pmh":
            # Check for known diagnoses
            known_diag = [e for e in extracted_context if e.get("type") == "diagnosis" and e.get("confidence", 0) >= 0.8]
            if known_diag:
                top_diag = known_diag[0]
                val = top_diag.get("value")
                text = (
                    f"आपके पिछले रिकॉर्ड के अनुसार आपको {val} की समस्या रही है — क्या यह अभी भी जारी है?"
                    if is_hi
                    else f"Your medical records indicate a history of {val} — are you still experiencing this?"
                )
                return NextQuestion(
                    question_id=f"recall_pmh_{top_diag.get('entity_id', 'diag')}",
                    text=text,
                    input_type="yes_no",
                    options=["हाँ (Yes, still continuing)", "नहीं (No, resolved)"] if is_hi else ["Yes", "No"],
                    section="pmh",
                    progress_pct=default_question.progress_pct,
                    metadata={
                        "is_smart_recall": True,
                        "source_entity_id": top_diag.get("entity_id"),
                        "entity_value": val,
                    },
                )

        elif section == "medications":
            # Check for known medications
            known_meds = [e for e in extracted_context if e.get("type") == "medication" and e.get("confidence", 0) >= 0.8]
            if known_meds:
                top_med = known_meds[0]
                med_name = top_med.get("value")
                text = (
                    f"आपके पर्चे में {med_name} दर्ज है — क्या आप अभी भी यह दवा नियमित ले रहे हैं?"
                    if is_hi
                    else f"Your records show you take {med_name} — is that still current?"
                )
                return NextQuestion(
                    question_id=f"recall_med_{top_med.get('entity_id', 'med')}",
                    text=text,
                    input_type="yes_no",
                    options=["हाँ, नियमित ले रहा हूँ (Yes, taking regularly)", "नहीं, बंद कर दी है (No, stopped)"] if is_hi else ["Yes, taking regularly", "No, stopped"],
                    section="medications",
                    progress_pct=default_question.progress_pct,
                    metadata={
                        "is_smart_recall": True,
                        "source_entity_id": top_med.get("entity_id"),
                        "entity_value": med_name,
                    },
                )

        elif section == "allergies":
            # Check for known allergies
            known_allergies = [e for e in extracted_context if e.get("type") == "allergy" and e.get("confidence", 0) >= 0.8]
            if known_allergies:
                top_al = known_allergies[0]
                al_name = top_al.get("value")
                text = (
                    f"आपके रिकॉर्ड में {al_name} से एलर्जी दर्ज है — क्या आपको कोई अन्य एलर्जी भी है?"
                    if is_hi
                    else f"Your file notes an allergy to {al_name} — do you have any other drug allergies?"
                )
                return NextQuestion(
                    question_id=f"recall_all_{top_al.get('entity_id', 'all')}",
                    text=text,
                    input_type="voice_touch",
                    options=["कोई अन्य एलर्जी नहीं (No other allergies)", "हाँ, अन्य भी है (Yes, other allergies)"] if is_hi else ["No other allergies", "Yes, other allergies"],
                    section="allergies",
                    progress_pct=default_question.progress_pct,
                    metadata={
                        "is_smart_recall": True,
                        "source_entity_id": top_al.get("entity_id"),
                        "entity_value": al_name,
                    },
                )

        return default_question


smart_recall_service = SmartRecallService()
