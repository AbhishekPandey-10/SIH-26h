"""
Unit tests for Red-Flag detection service
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""

from app.services.red_flag_detector import RedFlagDetector


def test_four_mandatory_triggers():
    detector = RedFlagDetector()

    # 1. Cardiac mandatory
    ev1 = detector.scan_text("Doctor, I have chest pain with breathlessness since morning", "s1")
    assert ev1 is not None
    assert ev1.severity == "red"
    assert ev1.category == "cardiac"

    # 2. Psychiatric mandatory
    ev2 = detector.scan_text("I have severe depression and suicidal thoughts", "s2")
    assert ev2 is not None
    assert ev2.severity == "red"
    assert ev2.category == "psychiatric"

    # 3. Stroke mandatory
    ev3 = detector.scan_text("My father experienced sudden weakness one side and cannot lift his arm", "s3")
    assert ev3 is not None
    assert ev3.severity == "red"
    assert ev3.category == "stroke"

    # 4. Anaphylaxis mandatory
    ev4 = detector.scan_text("He has a severe allergic reaction after eating peanuts", "s4")
    assert ev4 is not None
    assert ev4.severity == "red"
    assert ev4.category == "anaphylaxis"


def test_hindi_triggers():
    detector = RedFlagDetector()

    # Hindi cardiac synonym
    ev = detector.scan_text("mujhe seene mein dard aur saans fulna ho raha hai", "s5")
    assert ev is not None
    assert ev.category == "cardiac"

    # Hindi stroke synonym
    ev_stroke = detector.scan_text("unke chehra tedha ho gaya hai", "s6")
    assert ev_stroke is not None
    assert ev_stroke.category == "stroke"


def test_benign_text_no_red_flag():
    detector = RedFlagDetector()
    ev = detector.scan_text("I have had mild knee pain for two weeks after walking", "s7")
    assert ev is None
