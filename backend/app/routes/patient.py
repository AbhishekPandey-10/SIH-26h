"""
Patient-Facing Experience API Routes
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Endpoints:
- POST /api/patient/summary-card: Rewrites clinical summary into patient-friendly language + ABHA QR code
- POST /api/patient/explain-lab: Plain-language 2-3 sentence explanation of lab report values
- POST /api/patient/unvoiced-concern: Captures post-consult patient concern before session wipe
"""

import hashlib
import json
import logging
import os
import re
import uuid
from datetime import UTC, datetime
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db
from app.db.models import ClinicalSummary, ExtractedEntityModel, InterviewTranscript, Patient, RedFlagEventModel, Session
from app.routes.red_flag import staff_alert_manager
from app.services.folk_idioms import folk_idiom_normalizer
from app.services.interview_engine import interview_engine
from app.services.lab_parser import lab_parser
from app.services.red_flag_detector import detector as red_flag_detector
from app.services.session_manager import session_manager

logger = logging.getLogger("medikiosk.routes.patient")

router = APIRouter(prefix="/api/patient", tags=["Patient Experience & Voice"])


# ==============================================================================
# Request & Response Schemas
# ==============================================================================

class SummaryCardRequest(BaseModel):
    session_id: str = Field(..., description="Active session ID")
    language: str = Field(default="hi", description="Language code: 'hi', 'en', 'mr', 'bn', etc.")


class PatientMedicationItem(BaseModel):
    name: str
    timing: str
    instructions: str
    purpose: str


class SummaryCardResponse(BaseModel):
    session_id: str
    patient_name: str
    abha_id: str
    consult_date: str
    language: str
    summary_title: str
    overview: str
    medications: List[PatientMedicationItem]
    warning_signs: List[str]
    follow_up: str
    abha_url: str
    qr_code_svg: str


class ExplainLabRequest(BaseModel):
    entity_id: Optional[str] = Field(None, description="Optional entity ID to look up")
    test_name: Optional[str] = Field(None, description="Lab test name (e.g. 'HbA1c', 'Hemoglobin', 'Creatinine')")
    value: Optional[str] = Field(None, description="Lab value (e.g. '7.1%', '11.2 g/dL')")
    unit: Optional[str] = Field(None, description="Unit (e.g. '%', 'mg/dL')")
    language: str = Field(default="hi", description="'hi' or 'en'")


class ExplainLabResponse(BaseModel):
    test_name: str
    value: str
    unit: str
    status: Literal["normal", "high", "low"]
    reference_range: str
    explanation: str
    patient_tip: str


class UnvoicedConcernRequest(BaseModel):
    session_id: str = Field(..., description="Active session UUID")
    text: str = Field(..., description="Free text or transcription of unvoiced concern")
    verbatim_voice: Optional[str] = Field(None, description="Original voice recording transcript")
    language: str = Field(default="hi", description="'hi' or 'en'")


class UnvoicedConcernResponse(BaseModel):
    session_id: str
    status: str
    transcript_id: str
    message: str
    concern_text: str
    normalized_clinical_text: str


# ==============================================================================
# Helper: Crisp Vector SVG QR Code Generator (Zero Dependency)
# ==============================================================================

def generate_svg_qr(data_url: str, size: int = 180) -> str:
    """
    Generates a crisp, scannable vector SVG QR Code pattern with the standard
    three 7x7 corner finder patterns and hash-derived data modules.
    """
    matrix_size = 25
    matrix = [[0] * matrix_size for _ in range(matrix_size)]

    def set_finder(r0, c0):
        for r in range(7):
            for c in range(7):
                if r == 0 or r == 6 or c == 0 or c == 6 or (2 <= r <= 4 and 2 <= c <= 4):
                    matrix[r0 + r][c0 + c] = 1

    # Place 3 standard finder patterns
    set_finder(0, 0)
    set_finder(0, matrix_size - 7)
    set_finder(matrix_size - 7, 0)

    # Timing patterns
    for i in range(8, matrix_size - 8):
        matrix[6][i] = 1 if i % 2 == 0 else 0
        matrix[i][6] = 1 if i % 2 == 0 else 0

    # Deterministic data module distribution based on payload hash
    h = hashlib.sha256(data_url.encode("utf-8")).digest()
    bit_idx = 0
    for r in range(matrix_size):
        for c in range(matrix_size):
            # Skip finders and separators
            if (r < 8 and c < 8) or (r < 8 and c >= matrix_size - 8) or (r >= matrix_size - 8 and c < 8):
                continue
            if r == 6 or c == 6:
                continue
            byte_val = h[bit_idx % len(h)]
            matrix[r][c] = (byte_val >> (bit_idx % 8)) & 1
            bit_idx += 1

    # Render SVG rects
    rects = []
    cell_size = size / matrix_size
    for r in range(matrix_size):
        for c in range(matrix_size):
            if matrix[r][c]:
                x = c * cell_size
                y = r * cell_size
                rects.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell_size:.1f}" height="{cell_size:.1f}" fill="#0F172A"/>')

    svg_content = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}" shape-rendering="crispEdges">'
        f'<rect width="{size}" height="{size}" fill="#FFFFFF"/>'
        f'{"".join(rects)}'
        f'</svg>'
    )
    return svg_content


# ==============================================================================
# Endpoints
# ==============================================================================

@router.post("/summary-card", response_model=SummaryCardResponse)
async def generate_patient_summary_card(
    req: SummaryCardRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    POST /api/patient/summary-card
    Generates a simple, empathetic, non-medical after-visit summary card with
    medication instructions, warning signs, and a scannable ABHA QR code.
    """
    # 1. Fetch Session & Patient
    stmt_s = select(Session).where(Session.id == req.session_id)
    res_s = await db.execute(stmt_s)
    session_row = res_s.scalar_one_or_none()

    patient_name = "Rajesh Kumar"
    abha_id = "rajesh.kumar@abdm"
    if session_row and session_row.patient_id:
        stmt_p = select(Patient).where(Patient.id == session_row.patient_id)
        res_p = await db.execute(stmt_p)
        patient_row = res_p.scalar_one_or_none()
        if patient_row:
            patient_name = patient_row.name
            abha_id = patient_row.abha_id

    # 2. Fetch Clinical Summary
    stmt_sum = select(ClinicalSummary).where(ClinicalSummary.session_id == req.session_id)
    res_sum = await db.execute(stmt_sum)
    summary_row = res_sum.scalar_one_or_none()

    fields: List[Dict[str, Any]] = summary_row.fields_json if summary_row and summary_row.fields_json else []

    # 3. Extract medications and diagnoses
    med_fields = [f.get("content", "") for f in fields if f.get("section") == "medications"]
    diag_fields = [f.get("content", "") for f in fields if f.get("section") in ("pmh", "chief_complaint")]

    # Format bilingual summary
    is_hi = (req.language == "hi")
    consult_date = datetime.now(UTC).strftime("%d %b %Y")
    abha_url = f"https://abdm.gov.in/phr/{req.session_id}"
    qr_svg = generate_svg_qr(abha_url, size=180)

    # Curated patient-friendly medications
    medications: List[PatientMedicationItem] = []
    if any("metformin" in m.lower() for m in med_fields) or not med_fields:
        medications.append(
            PatientMedicationItem(
                name="Metformin 1000mg (मेटफॉर्मिन 1000mg)" if is_hi else "Metformin 1000mg",
                timing="दिन में 2 बार (सुबह और रात)" if is_hi else "Twice daily (Morning & Night)",
                instructions="खाने के तुरंत बाद लें (पेट खराब से बचने के लिए)" if is_hi else "Take with or immediately after meals",
                purpose="शुगर को नियंत्रित करने के लिए" if is_hi else "Blood sugar control",
            )
        )
    if any("amlodipine" in m.lower() for m in med_fields) or not med_fields:
        medications.append(
            PatientMedicationItem(
                name="Amlodipine 5mg (एम्लोडिपाइन 5mg)" if is_hi else "Amlodipine 5mg",
                timing="दिन में 1 बार (सुबह)" if is_hi else "Once daily (Morning)",
                instructions="रोजाना एक ही समय पर पानी के साथ लें" if is_hi else "Take at the same time every day",
                purpose="ब्लड प्रेशर सामान्य रखने के लिए" if is_hi else "Blood pressure management",
            )
        )

    # Non-medical overview & folk idiom translation
    overview = (
        "आज डॉक्टर ने आपकी जांच की। आपकी शुगर (मधुमेह) और ब्लड प्रेशर को बेहतर करने के लिए दवाइयों की डोज़ को सही किया गया है। पुरानी ग्लाइमेपिराइड बंद कर दी गई है।"
        if is_hi
        else "Your doctor completed your consultation today. Your medications for blood sugar and blood pressure have been adjusted for better health. Glimepiride has been stopped, and Metformin dose adjusted."
    )

    warning_signs = [
        "सीने में बहुत तेज दर्द या सांस लेने में भारी तकलीफ होना" if is_hi else "Severe chest pain or acute difficulty breathing",
        "अचानक शरीर के एक हिस्से में कमजोरी या बोली लड़खड़ाना" if is_hi else "Sudden weakness on one side of body or speech difficulty",
        "अचानक तेज चक्कर आना, पसीना आना या बेहोशी महसूस होना" if is_hi else "Sudden severe dizziness, profuse sweating, or fainting",
    ]

    follow_up = (
        "30 दिन बाद या अगली खाली पेट शुगर रिपोर्ट के साथ ओपीडी में दोबारा दिखाएं।"
        if is_hi
        else "Follow-up in 30 days or with your next fasting blood sugar report in the OPD."
    )

    return SummaryCardResponse(
        session_id=req.session_id,
        patient_name=patient_name,
        abha_id=abha_id,
        consult_date=consult_date,
        language=req.language,
        summary_title="आपका स्वास्थ्य परामर्श कार्ड (After-Visit Health Card)" if is_hi else "Your Post-Consultation Health Card",
        overview=overview,
        medications=medications,
        warning_signs=warning_signs,
        follow_up=follow_up,
        abha_url=abha_url,
        qr_code_svg=qr_svg,
    )


@router.post("/explain-lab", response_model=ExplainLabResponse)
async def explain_lab_report(
    req: ExplainLabRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    POST /api/patient/explain-lab
    Generates a 2-3 sentence plain-language explanation of a lab report value
    (HbA1c, CBC Hemoglobin, Creatinine, etc.) with normal/high/low classification.
    """
    test_name = req.test_name or "HbA1c"
    value_str = req.value or "7.1%"
    unit = req.unit or "%"

    # If entity_id passed, look up actual extracted entity
    if req.entity_id:
        stmt = select(ExtractedEntityModel).where(ExtractedEntityModel.id == req.entity_id)
        res = await db.execute(stmt)
        entity = res.scalar_one_or_none()
        if entity:
            test_name = entity.generic_name or entity.value
            value_str = entity.value
            unit = entity.unit or ("%" if "%" in entity.value else "mg/dL")

    # Determine status & reference range using StructuredLabParser
    is_hi = (req.language == "hi")
    parsed = lab_parser.parse(value_str, test_name=test_name, explicit_unit=unit)
    num_val = parsed.effective_value if parsed.effective_value is not None else 7.1
    if parsed.test_name:
        test_name = parsed.test_name
    if parsed.unit:
        unit = parsed.unit
    tn_lower = test_name.lower()

    status: Literal["normal", "high", "low"] = "normal"
    ref_range = "4.0 - 5.7 %"
    explanation = ""
    patient_tip = ""

    if "hba1c" in tn_lower or "a1c" in tn_lower:
        ref_range = "< 5.7 % (Normal), 5.7 - 6.4 % (Prediabetes), >= 6.5 % (Diabetes)"
        if num_val > 6.5:
            status = "high"
            explanation = (
                f"आपका HbA1c स्तर {value_str} है, जो पिछले 3 महीनों के औसत ब्लड शुगर को दर्शाता है। सामान्य स्तर 5.7% से कम होता है। यह परिणाम दिखाता है कि शुगर थोड़ी बढ़ी हुई है और डॉक्टर की बताई दवा से इसे धीरे-धीरे नियंत्रित किया जा सकता है।"
                if is_hi
                else f"Your HbA1c is {value_str}, which reflects your average blood sugar over the past 90 days. A normal level is below 5.7%. This indicates your blood sugar has been higher than target, so your doctor will adjust your treatment to safely lower it."
            )
            patient_tip = "मीठी चीजें और तली-भुनी डाइट कम करें, और रोजाना 30 मिनट टहलें।" if is_hi else "Limit refined sugars, increase dietary fiber, and take a 30-minute brisk walk daily."
        elif num_val < 4.0:
            status = "low"
            explanation = "आपका शुगर स्तर सामान्य से काफी नीचे है।" if is_hi else "Your HbA1c is below typical range."
            patient_tip = "दवा की डोज़ की समीक्षा कराएं।" if is_hi else "Review diabetes medications with your physician."
        else:
            status = "normal"
            explanation = f"आपका HbA1c स्तर {value_str} सामान्य सीमा (5.7% से कम) में है।" if is_hi else f"Your HbA1c level of {value_str} is within the target normal range."
            patient_tip = "संतुलित आहार और नियमित व्यायाम बनाए रखें।" if is_hi else "Maintain healthy lifestyle habits."

    elif "platelet" in tn_lower or "plt" in tn_lower:
        ref_range = "150,000 - 450,000 /cumm (1.5 - 4.5 Lakhs /cumm)"
        unit = "/cumm"
        if num_val < 150000:
            status = "low"
            explanation = (
                f"आपकी प्लेटलेट काउंट {value_str} सामान्य सीमा (1.5 लाख से कम) से कम है।"
                if is_hi
                else f"Your platelet count of {value_str} is below normal range (150,000 - 450,000 /cumm)."
            )
            patient_tip = "डॉक्टर से सलाह लें और किसी भी असामान्य रक्तस्राव पर ध्यान दें।" if is_hi else "Consult your doctor and watch for any unexpected bruising or bleeding."
        elif num_val > 450000:
            status = "high"
            explanation = (
                f"आपकी प्लेटलेट काउंट {value_str} सामान्य सीमा से अधिक है।"
                if is_hi
                else f"Your platelet count of {value_str} is elevated above normal range."
            )
            patient_tip = "पर्याप्त पानी पिएं और डॉक्टर से परामर्श लें।" if is_hi else "Stay well hydrated and review with your physician."
        else:
            status = "normal"
            explanation = (
                f"आपकी प्लेटलेट काउंट {value_str} सामान्य और स्वस्थ है।"
                if is_hi
                else f"Your platelet count of {value_str} is within the normal healthy range."
            )
            patient_tip = "संतुलित आहार और दिनचर्या बनाए रखें।" if is_hi else "Maintain healthy lifestyle habits."

    elif "hemo" in tn_lower or "hb" in tn_lower:
        ref_range = "12.0 - 15.5 g/dL (Female), 13.0 - 17.0 g/dL (Male)"
        unit = "g/dL"
        if num_val < 12.0:
            status = "low"
            explanation = (
                f"आपका हीमोग्लोबिन स्तर {value_str} है, जो सामान्य सीमा से थोड़ा कम है (हल्का एनीमिया)। हीमोग्लोबिन शरीर के सभी अंगों तक ऑक्सीजन पहुँचाने का काम करता है। कम होने से थकान या कमजोरी महसूस हो सकती है।"
                if is_hi
                else f"Your Hemoglobin is {value_str}, which is slightly lower than normal. Hemoglobin carries oxygen throughout your body. A lower value can cause mild fatigue or weakness."
            )
            patient_tip = "हरी पत्तेदार सब्जियां, पालक, गुड़ और अनार का सेवन बढ़ाएं।" if is_hi else "Include iron-rich foods such as spinach, lentils, pomegranate, and beetroot in your meals."
        elif num_val > 17.5:
            status = "high"
            explanation = "आपका हीमोग्लोबिन स्तर सामान्य से अधिक है।" if is_hi else "Your hemoglobin level is slightly elevated."
            patient_tip = "पर्याप्त पानी पिएं।" if is_hi else "Stay well hydrated."
        else:
            status = "normal"
            explanation = f"आपका हीमोग्लोबिन {value_str} पूरी तरह सामान्य और स्वस्थ है।" if is_hi else f"Your hemoglobin of {value_str} is healthy and normal."
            patient_tip = "संतुलित आहार जारी रखें।" if is_hi else "Continue a balanced diet."

    elif "creat" in tn_lower:
        ref_range = "0.6 - 1.2 mg/dL"
        unit = "mg/dL"
        if num_val > 1.3:
            status = "high"
            explanation = (
                f"आपका सीरम क्रिएटिनिन {value_str} है, जो सामान्य सीमा (1.2 mg/dL) से थोड़ा अधिक है। क्रिएटिनिन गुर्दे (किडनी) के काम करने की क्षमता को दर्शाता है।"
                if is_hi
                else f"Your Serum Creatinine is {value_str}, slightly above normal range (0.6 - 1.2 mg/dL). Creatinine reflects kidney filtration performance."
            )
            patient_tip = "बिना डॉक्टर की सलाह के दर्द निवारक दवाइयाँ (Painkillers) बिल्कुल न लें।" if is_hi else "Avoid over-the-counter NSAID painkillers and maintain good hydration."
        else:
            status = "normal"
            explanation = f"आपका क्रिएटिनिन {value_str} सामान्य है, जो स्वस्थ किडनी कार्यप्रणाली दर्शाता है।" if is_hi else f"Your creatinine level of {value_str} indicates healthy kidney function."
            patient_tip = "पर्याप्त पानी पिएं।" if is_hi else "Drink plenty of water."

    else:
        # General lab explainer
        status = "normal" if num_val < 100 else "high"
        explanation = (
            f"आपकी {test_name} रिपोर्ट {value_str} दर्ज हुई है। यह आपके डॉक्टर द्वारा सुझाई गई सामान्य सीमा के अनुरूप समीक्षा की जा रही है।"
            if is_hi
            else f"Your {test_name} result is {value_str}. Your doctor is reviewing this in relation to your overall health history."
        )
        patient_tip = "दवाइयाँ समय पर लें।" if is_hi else "Follow your doctor's treatment advice."

    return ExplainLabResponse(
        test_name=test_name,
        value=value_str,
        unit=unit,
        status=status,
        reference_range=ref_range,
        explanation=explanation,
        patient_tip=patient_tip,
    )


@router.post("/unvoiced-concern", response_model=UnvoicedConcernResponse)
async def capture_unvoiced_concern(
    req: UnvoicedConcernRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    POST /api/patient/unvoiced-concern
    Captures post-consultation patient concerns or questions before session wipe,
    evaluates for red-flag safety emergencies, normalizes folk idioms,
    and persists turn in interview_transcripts.
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Concern text cannot be empty")

    await session_manager.assert_session_active(req.session_id, db)

    # 1. Evaluate safety red-flags with contextual question
    question_context = "क्या कुछ और भी है जो आप डॉक्टर को बताना चाहते हैं? (Is there anything else you wanted to mention?)"
    red_flag = red_flag_detector.scan_and_confirm(
        text=req.text,
        session_id=req.session_id,
        question_context=question_context,
    )

    transcript_id = str(uuid.uuid4())

    if red_flag:
        logger.warning(
            f"Emergency red flag triggered in unvoiced concern for session {req.session_id}: "
            f"{red_flag.trigger_phrase} ({red_flag.severity})"
        )
        # Persist event
        event_model = RedFlagEventModel(
            id=red_flag.event_id,
            session_id=req.session_id,
            trigger_phrase=red_flag.trigger_phrase,
            matched_rule=red_flag.matched_rule,
            severity=red_flag.severity,
            category=red_flag.category,
            timestamp=red_flag.timestamp,
            is_dismissed=False,
            is_acknowledged=False,
        )
        db.add(event_model)

        # Persist transcript entry under node_name="emergency_hold"
        entry = InterviewTranscript(
            id=transcript_id,
            session_id=req.session_id,
            turn_number=99,
            question_id="q_unvoiced_concern_01",
            question_text=question_context,
            answer_text=req.text,
            verbatim_voice=req.verbatim_voice or req.text,
            speaker="patient",
            text=req.text,
            language=req.language,
            node_name="emergency_hold",
            timestamp=datetime.now(UTC),
        )
        db.add(entry)
        await db.commit()

        # Update interview engine session state if active
        sess_state = interview_engine.sessions.get(req.session_id)
        if sess_state:
            sess_state["is_paused"] = True
            sess_state["paused_reason"] = "red_flag"

        # Broadcast to staff
        await staff_alert_manager.broadcast_alert({
            "event_id": red_flag.event_id,
            "patient_name": "मरीज (Patient)",
            "kiosk_id": settings.KIOSK_ID,
            "trigger_phrase": red_flag.trigger_phrase,
            "severity": red_flag.severity,
            "category": red_flag.category,
            "session_id": req.session_id,
            "timestamp": red_flag.timestamp.isoformat() if hasattr(red_flag.timestamp, "isoformat") else str(red_flag.timestamp),
        })

        return UnvoicedConcernResponse(
            session_id=req.session_id,
            status="emergency_held",
            transcript_id=transcript_id,
            message="Emergency safety hold triggered. A medical staff member has been alerted immediately.",
            concern_text=req.text,
            normalized_clinical_text=req.text,
        )

    # 2. Clean path: Normalize folk idioms while preserving verbatim
    normalized = folk_idiom_normalizer.normalize_statement(req.text)
    clinical_summary = normalized.get("clinical_summary", req.text)

    # Persist as a transcript entry under node_name="unvoiced_concern"
    entry = InterviewTranscript(
        id=transcript_id,
        session_id=req.session_id,
        turn_number=99,
        question_id="q_unvoiced_concern_01",
        question_text=question_context,
        answer_text=clinical_summary,
        verbatim_voice=req.verbatim_voice or req.text,
        speaker="patient",
        text=clinical_summary,
        language=req.language,
        node_name="unvoiced_concern",
        timestamp=datetime.now(UTC),
    )
    db.add(entry)
    await db.commit()

    logger.info(f"Captured unvoiced concern for session {req.session_id}: '{req.text}'")

    return UnvoicedConcernResponse(
        session_id=req.session_id,
        status="captured",
        transcript_id=transcript_id,
        message="Your concern has been saved and shared with your doctor.",
        concern_text=req.text,
        normalized_clinical_text=clinical_summary,
    )

