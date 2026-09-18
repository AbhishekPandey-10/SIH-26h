"""
B2. Red-Flag False Positive Audit — 50 Non-Emergency Transcripts
PS ID26047 — Final Phase Evaluation

Target: <5% false positive rate (<2.5/50).
"""

import pytest

from app.services.red_flag_detector import detector

# 50 benign, non-emergency patient statements
BENIGN_STATEMENTS = [
    "मुझे हल्का सिरदर्द है",
    "पेट में गैस बन रही है",
    "थोड़ा सा बुखार है",
    "कमर में दर्द है",
    "खांसी आ रही है 3 दिन से",
    "भूख कम लग रही है",
    "नींद नहीं आती कभी कभी",
    "I have mild body ache",
    "My back hurts when I sit too long",
    "I feel tired after work",
    "थोड़ी कमजोरी लग रही है",
    "दस्त लग रहे हैं",
    "उल्टी आई एक बार",
    "गला खराब है",
    "नाक बंद है",
    "आंखों में जलन है",
    "पैरों में सूजन है थोड़ी",
    "घुटने में दर्द है चलने में",
    "कान में दर्द है हल्का",
    "दांत में दर्द है",
    "I have mild acidity after eating",
    "मुझे constipation की समस्या है",
    "बालों का झड़ना बढ़ गया है",
    "स्किन पर दाने हैं खुजली है",
    "नाखून कमजोर हो गए हैं",
    "I feel bloated after meals",
    "मेरी आंखें कमजोर हो गई हैं",
    "कमर में अकड़न है सुबह",
    "पैर की उंगली में मोच आ गई",
    "हाथ में चोट लग गई थी",
    "I have a runny nose",
    "मुझे सर्दी लग गई",
    "गर्मी में बहुत पसीना आता है",
    "रात को बार बार पेशाब आता है",
    "I feel dizzy sometimes when I stand up quickly",
    "पीठ में जकड़न है",
    "मेरा वजन बढ़ रहा है",
    "आंखों के नीचे काले गड्ढे हैं",
    "मुझे एलर्जी है धूल से",
    "I have mild joint stiffness in morning",
    "पेट में हल्का दर्द रहता है",
    "कभी कभी सीने में जलन होती है खाने के बाद",
    "I sometimes feel nauseous in the car",
    "मेरे बच्चे को सर्दी-जुकाम है",
    "गला सूखता रहता है",
    "हाथों में झनझनाहट होती है",
    "I have dandruff problem",
    "मेरी कमर में चोट लगी थी पुरानी",
    "I have seasonal allergies",
    "मुझे gas की problem है raat ko",
]


def test_benign_statements_count():
    """Verify we have 50 test statements."""
    assert len(BENIGN_STATEMENTS) == 50


def test_red_flag_false_positive_rate():
    """
    Run 50 non-emergency statements through red-flag detector.
    Target: <5% false positive rate (<2.5 out of 50 → max 2 false positives).
    """
    false_positives = []

    for idx, statement in enumerate(BENIGN_STATEMENTS):
        result = detector.scan_text(statement, session_id=f"audit_{idx}")
        if result is not None:
            false_positives.append({
                "index": idx,
                "statement": statement,
                "trigger": result.trigger_phrase,
                "rule": result.matched_rule,
                "severity": result.severity,
            })

    fp_rate = len(false_positives) / len(BENIGN_STATEMENTS) * 100

    print(f"\n{'='*60}")
    print(f"RED-FLAG FALSE POSITIVE AUDIT")
    print(f"Total statements: {len(BENIGN_STATEMENTS)}")
    print(f"False positives: {len(false_positives)}")
    print(f"False positive rate: {fp_rate:.1f}%")
    print(f"Target: <5% (<2.5/50)")
    print(f"{'='*60}")

    if false_positives:
        print(f"\nFalse positives detected:")
        for fp in false_positives:
            print(f"  [{fp['index']}] '{fp['statement']}' → triggered '{fp['trigger']}' (rule: {fp['rule']})")

    assert fp_rate < 5.0, f"False positive rate {fp_rate:.1f}% exceeds 5% target"
