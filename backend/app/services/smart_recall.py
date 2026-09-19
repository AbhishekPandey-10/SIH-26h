"""
Smart Recall Service (Zero-Repeat OPD Interview Engine)
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Extracts historical clinical entities from scanned documents and past visits,
injects them into interview memory, and transforms generic intake questions into:
- <0.5: Ordinary generic question
- 0.5 to 0.8 inclusive: Rephrase verification prompt ("Our records mention X — could you verify?")
- >0.8: Confirmation prompt ("Your records show you take X — is that still current?")
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
    Injects pre-scanned prescription, lab, and history entities into interview memory.
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
        Prioritizes recency (created_at desc) so stale records are not selected over fresh ones.
        Normalizes a single canonical context dictionary shape.
        """
        # 1. Find patient_id for session
        sess_stmt = select(Session).where(Session.id == session_id)
        sess_res = await db.execute(sess_stmt)
        sess = sess_res.scalar_one_or_none()

        patient_sessions = [session_id]
        if sess and sess.patient_id:
            p_stmt = select(Session.id).where(Session.patient_id == sess.patient_id)
            p_res = await db.execute(p_stmt)
            all_sids = p_res.scalars().all()
            if all_sids:
                patient_sessions = list(all_sids)

        # 2. Fetch extracted entities ordered by recency first, then confidence
        stmt = (
            select(ExtractedEntityModel)
            .where(ExtractedEntityModel.session_id.in_(patient_sessions))
            .order_by(
                ExtractedEntityModel.created_at.desc(),
                ExtractedEntityModel.confidence.desc()
            )
        )
        res = await db.execute(stmt)
        entities = res.scalars().all()

        context: list[dict[str, Any]] = []
        for e in entities:
            # Normalize schema: both entity_type and type present
            ent_type = e.entity_type
            if ent_type and ent_type.startswith("vital_sign"):
                ent_type = "vital"

            context.append({
                "entity_id": e.id,
                "id": e.id,
                "document_id": e.document_id,
                "session_id": e.session_id,
                "entity_type": ent_type,
                "type": ent_type,
                "value": e.value,
                "generic_name": e.generic_name,
                "date": e.date,
                "confidence": float(e.confidence) if e.confidence is not None else 0.0,
                "bounding_box": e.bounding_box,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            })

        logger.info(f"Smart Recall loaded {len(context)} historical entities for encounter {session_id}")
        return context

    def adapt_question_with_recall(
        self,
        section: str,
        default_question: NextQuestion,
        extracted_context: List[Dict[str, Any]],
        language: str = "hi",
    ) -> NextQuestion:
        """
        Examines extracted_context for known facts matching current section.
        Strict confidence tiering:
        - < 0.5: Ordinary question (return default_question)
        - 0.5 <= conf <= 0.8: Verification prompt
        - > 0.8: Confirmation prompt
        """
        if not extracted_context:
            return default_question

        is_hi = (language == "hi")

        matching_entities: list[dict[str, Any]] = []
        if section == "pmh":
            matching_entities = [
                e for e in extracted_context
                if (e.get("entity_type") in ("diagnosis", "condition", "pmh")
                    or e.get("type") in ("diagnosis", "condition", "pmh"))
            ]
        elif section == "medications":
            matching_entities = [
                e for e in extracted_context
                if (e.get("entity_type") == "medication"
                    or e.get("type") == "medication"
                    or e.get("generic_name"))
            ]
        elif section == "allergies":
            matching_entities = [
                e for e in extracted_context
                if (e.get("entity_type") == "allergy"
                    or e.get("type") == "allergy")
            ]

        if not matching_entities:
            return default_question

        # Pick best entity: preserved in recency/confidence order
        top_item = matching_entities[0]
        conf = float(top_item.get("confidence", 0.0))
        val = top_item.get("generic_name") or top_item.get("value") or ""
        ent_id = top_item.get("entity_id") or top_item.get("id") or "ent"

        # Tier 1: Ordinary Question (< 0.5)
        if conf < 0.5:
            return default_question

        # Tier 2: Verification Prompt (0.5 through 0.8 inclusive)
        if 0.5 <= conf <= 0.8:
            if section == "pmh":
                text = (
                    f"अस्पताल के रिकॉर्ड में {val} की समस्या का उल्लेख है। क्या आप पुष्टि कर सकते हैं कि क्या यह सही है?"
                    if is_hi
                    else f"Our hospital records mention you may have had {val}. Could you please verify if this is accurate?"
                )
                opts = ["हाँ, यह सही है", "नहीं, यह गलत है"] if is_hi else ["Yes, accurate", "No, not accurate"]
            elif section == "medications":
                text = (
                    f"रिकॉर्ड में {val} का उल्लेख है। क्या आप पुष्टि कर सकते हैं कि आप यह दवाई लेते हैं?"
                    if is_hi
                    else f"Our hospital records mention you may be taking {val}. Could you please verify if you take this?"
                )
                opts = ["हाँ, यह दवाई लेता हूँ", "नहीं, यह नहीं लेता"] if is_hi else ["Yes, I take this", "No, I do not take this"]
            else:  # allergies
                text = (
                    f"रिकॉर्ड में {val} से एलर्जी का उल्लेख है। क्या आप पुष्टि कर सकते हैं?"
                    if is_hi
                    else f"Our hospital records mention a possible allergy to {val}. Could you please verify if you have this allergy?"
                )
                opts = ["हाँ, इससे एलर्जी है", "नहीं, इससे एलर्जी नहीं है"] if is_hi else ["Yes, allergic", "No, not allergic"]

            return NextQuestion(
                question_id=f"recall_verify_{section}_{ent_id}",
                text=text,
                input_type="choice" if section == "medications" else "yes_no",
                options=opts,
                section=section,
                progress_pct=default_question.progress_pct,
                metadata={
                    "is_smart_recall": True,
                    "recall_mode": "rephrase_verification",
                    "verification_tier": "verification",
                    "confidence": conf,
                    "target_entity": val,
                    "source_entity_id": ent_id,
                    "evidence_id": ent_id,
                    "entity_value": val,
                },
            )

        # Tier 3: Confirmation Prompt (> 0.8)
        if conf > 0.8:
            if section == "pmh":
                text = (
                    f"आपके पिछले रिकॉर्ड के अनुसार आपको {val} की समस्या रही है — क्या यह अभी भी जारी है?"
                    if is_hi
                    else f"Your medical records indicate a history of {val} — are you still experiencing this?"
                )
                opts = ["हाँ, जारी है", "नहीं, ठीक हो चुकी है"] if is_hi else ["Yes, still ongoing", "No, resolved"]
            elif section == "medications":
                text = (
                    f"आपके पिछले रिकॉर्ड के अनुसार आप {val} लेते हैं — क्या यह अभी भी जारी है? (Your records show you take {val} — is that still current?)"
                    if is_hi
                    else f"Your records show you take {val} — is that still current?"
                )
                opts = (
                    ["हाँ, अभी भी ले रहा हूँ (Yes, still current)", "नहीं, बंद कर दी है (Stopped)", "डोज़ बदल गई है (Dose changed)"]
                    if is_hi
                    else ["Yes, still taking it", "No, stopped taking it", "Dose has changed"]
                )
            else:  # allergies
                text = (
                    f"आपके रिकॉर्ड में {val} से एलर्जी दर्ज है — क्या आपको कोई अन्य एलर्जी भी है?"
                    if is_hi
                    else f"Your file notes an allergy to {val} — do you have any other drug allergies?"
                )
                opts = ["कोई अन्य एलर्जी नहीं", "हाँ, अन्य भी है"] if is_hi else ["No other allergies", "Yes, other allergies"]

            return NextQuestion(
                question_id=f"recall_{section}_{ent_id}",
                text=text,
                input_type="choice" if section == "medications" else "yes_no",
                options=opts,
                section=section,
                progress_pct=default_question.progress_pct,
                metadata={
                    "is_smart_recall": True,
                    "recall_mode": "confirm_known_fact",
                    "verification_tier": "confirmation",
                    "confidence": conf,
                    "target_entity": val,
                    "source_entity_id": ent_id,
                    "evidence_id": ent_id,
                    "entity_value": val,
                },
            )

        return default_question


smart_recall_service = SmartRecallService()
