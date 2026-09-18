"""
AYUSH Dashavidha Pariksha Diagnostic Service & Prakriti Engine
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
Dev 1 Core AYUSH Clinical Module
"""

from typing import Any, Dict, List, Optional


# Classical Dashavidha Pariksha 10 Assessment Stages
DASHHAVIDHA_STAGES = [
    {
        "id": "prakriti",
        "name": "Prakriti Pariksha (Constitutional Assessment)",
        "question_en": "How do you describe your natural physical constitution and weather tolerance (cold, heat, or humidity)?",
        "question_hi": "आपकी स्वाभाविक शारीरिक प्रकृति और मौसम (ठंड, गर्मी, नमी) सहनशीलता कैसी है?",
        "options": [
            {"label_en": "Lean build, dry skin, intolerant to cold (Vata)", "label_hi": "पतला शरीर, रूखी त्वचा, ठंड बर्दाश्त नहीं (वात)", "dosha": "vata"},
            {"label_en": "Medium build, warm skin, intolerant to heat (Pitta)", "label_hi": "मध्यम शरीर, गर्म त्वचा, गर्मी बर्दाश्त नहीं (पित्त)", "dosha": "pitta"},
            {"label_en": "Heavy/solid build, oily skin, comfortable in all seasons (Kapha)", "label_hi": "मजबूत/भारी शरीर, तैलीय त्वचा, सभी मौसम में सहज (कफ)", "dosha": "kapha"}
        ]
    },
    {
        "id": "vikriti",
        "name": "Vikriti Pariksha (Pathological State / Morbidity)",
        "question_en": "Which symptoms have developed recently (e.g. sharp/burning pain, stiffness, heaviness, acidity)?",
        "question_hi": "हाल ही में कौन से नए लक्षण या तकलीफ़ें शुरू हुई हैं (जैसे चुभन/जलन, जकड़न, भारीपन, खट्टी डकारें)?",
        "options": [
            {"label_en": "Fluctuating or sharp shifting pain, tremors, restlessness", "label_hi": "बदलने वाला तेज़ दर्द, कंपन, बेचैनी", "dosha": "vata"},
            {"label_en": "Burning sensation, excessive thirst, acid reflux, feverishness", "label_hi": "जलन, अत्यधिक प्यास, एसिडिटी, गर्मी महसूस होना", "dosha": "pitta"},
            {"label_en": "Heaviness in limbs, excessive mucus, sluggishness, sweet taste in mouth", "label_hi": "अंगों में भारीपन, कफ/बलगम, सुस्ती, मुंह में मीठापन", "dosha": "kapha"}
        ]
    },
    {
        "id": "sara",
        "name": "Sara Pariksha (Tissue Excellence / Dhatu Essence)",
        "question_en": "How would you describe your overall muscle tone, bone strength, and hair/nail luster?",
        "question_hi": "आपकी मांसपेशियों की मजबूती, हड्डियों का बल और त्वचा/नाखूनों की चमक कैसी रहती है?",
        "options": [
            {"label_en": "Fragile nails, rough hair, variable vitality (Alpa Sara)", "label_hi": "कमजोर नाखून, रूखे बाल, अनिश्चित ऊर्जा (अल्प सार)", "grade": "alpa"},
            {"label_en": "Moderate vitality and firmness (Madhyama Sara)", "label_hi": "मध्यम शक्ति और स्थिरता (मध्यम सार)", "grade": "madhyama"},
            {"label_en": "Strong, firm muscles, lustrous skin and teeth (Uttama Sara)", "label_hi": "सुगठित मांसपेशियां, चमकदार त्वचा व दांत (उत्तम सार)", "grade": "uttama"}
        ]
    },
    {
        "id": "samhanana",
        "name": "Samhanana Pariksha (Compactness / Body Build)",
        "question_en": "How compact and proportionate is your skeletal and muscular structure?",
        "question_hi": "आपके शरीर और हड्डियों का गठन कैसा है?",
        "options": [
            {"label_en": "Slender, prominent joints (Sushira / Vata)", "label_hi": "पतला, उभरे हुए जोड़ (वात)", "dosha": "vata"},
            {"label_en": "Balanced, medium symmetry (Madhyama / Pitta)", "label_hi": "संतुलित और सुडौल (पित्त)", "dosha": "pitta"},
            {"label_en": "Broad, well-knit joints and broad chest (Samhata / Kapha)", "label_hi": "चौड़ी छाती, सुदृढ़ जोड़ (कफ)", "dosha": "kapha"}
        ]
    },
    {
        "id": "pramana",
        "name": "Pramana Pariksha (Anthropometric Proportions)",
        "question_en": "Are your body proportions (height, arm span, weight) within normal expected limits?",
        "question_hi": "क्या आपकी शारीरिक माप (ऊंचाई, वजन, फैलाव) सामान्य अनुपात में है?",
        "options": [
            {"label_en": "Below average weight or disproportionately tall/short", "label_hi": "कम वजन या असामान्य अनुपात", "grade": "alpa"},
            {"label_en": "Proportionate and balanced", "label_hi": "सामान्य व संतुलित", "grade": "madhyama"},
            {"label_en": "Robust, broad stature", "label_hi": "भारी या चौड़ा कद-काठी", "grade": "uttama"}
        ]
    },
    {
        "id": "satmya",
        "name": "Satmya Pariksha (Homologation / Habituation)",
        "question_en": "Which tastes (sweet, salty, spicy, bitter) and food temperatures suit your digestion best?",
        "question_hi": "आपको कौन से स्वाद (मीठा, नमकीन, तीखा, कड़वा) और कैसा भोजन सबसे ज्यादा अनुकूल पड़ता है?",
        "options": [
            {"label_en": "Warm, oily, sweet and sour foods suit best", "label_hi": "गर्म, स्निग्ध, मीठा और खट्टा भोजन अनुकूल रहता है", "dosha": "vata"},
            {"label_en": "Cool, sweet, bitter, and astringent foods suit best", "label_hi": "ठंडा, मीठा, कड़वा और हल्का भोजन अनुकूल रहता है", "dosha": "pitta"},
            {"label_en": "Warm, light, spicy and pungent foods suit best", "label_hi": "हल्का, गर्म, तीखा और पाचक भोजन अनुकूल रहता है", "dosha": "kapha"}
        ]
    },
    {
        "id": "satva",
        "name": "Satva Pariksha (Mental Stamina / Temperament)",
        "question_en": "How do you handle anxiety, stress, or unexpected illness?",
        "question_hi": "तनाव, चिंता या बीमारी के समय आपका मानसिक धैर्य कैसा रहता है?",
        "options": [
            {"label_en": "Easily worried, fearful, difficulty sleeping (Avara Satva / Vata)", "label_hi": "जल्दी घबराना, चिंता, नींद न आना (अवर सत्व)", "dosha": "vata"},
            {"label_en": "Impatience, irritability, highly focused (Madhyama Satva / Pitta)", "label_hi": "जल्दबाजी, चिड़चिड़ापन, तीव्र स्वभाव (मध्यम सत्व)", "dosha": "pitta"},
            {"label_en": "Calm, composed, tolerant, undisturbed (Pravara Satva / Kapha)", "label_hi": "शांत, धैर्यवान, अडिग (प्रवर सत्व)", "dosha": "kapha"}
        ]
    },
    {
        "id": "ahara_shakti",
        "name": "Ahara Shakti & Vihara (Dietary Habit & Digestion)",
        "question_en": "How is your appetite (Abhyavaharana) and digestive capacity (Jarana Shakti)?",
        "question_hi": "आपकी भूख और भोजन पचाने की क्षमता कैसी है?",
        "options": [
            {"label_en": "Irregular appetite, gas/bloating after meals (Vishama Agni)", "label_hi": "अनियमित भूख, खाने के बाद गैस या पेट फूलना (विषम अग्नि)", "agni": "vishama", "dosha": "vata"},
            {"label_en": "Intense appetite, cannot skip meals without acidity/irritation (Tikshna Agni)", "label_hi": "तीव्र भूख, समय पर खाना न मिलने पर सिरदर्द या जलन (तीक्ष्ण अग्नि)", "agni": "tikshna", "dosha": "pitta"},
            {"label_en": "Slow appetite, feeling heavy for many hours after eating (Manda Agni)", "label_hi": "मंद भूख, भोजन देर से पचना व भारीपन (मंद अग्नि)", "agni": "manda", "dosha": "kapha"},
            {"label_en": "Regular, comfortable digestion with on-time hunger (Sama Agni)", "label_hi": "नियमित व संतुलित पाचन (सम अग्नि)", "agni": "sama", "dosha": "balanced"}
        ]
    },
    {
        "id": "vyayama_shakti",
        "name": "Vyayama Shakti (Physical Capacity & Endurance)",
        "question_en": "How much physical exertion or walking can you do before feeling exhausted?",
        "question_hi": "आप बिना थके कितना पैदल चल सकते हैं या शारीरिक श्रम कर सकते हैं?",
        "options": [
            {"label_en": "Get exhausted quickly with shortness of breath (Heena Shakti)", "label_hi": "जल्दी सांस फूलना या तुरंत थकान (हीन शक्ति)", "grade": "alpa"},
            {"label_en": "Moderate endurance, can do daily tasks without difficulty (Madhyama Shakti)", "label_hi": "सामान्य कामकाज बिना परेशानी के कर लेते हैं (मध्यम शक्ति)", "grade": "madhyama"},
            {"label_en": "High stamina, can do strenuous work comfortably (Uttama Shakti)", "label_hi": "उच्च सहनशक्ति, कठोर परिश्रम भी आसानी से (उत्तम शक्ति)", "grade": "uttama"}
        ]
    },
    {
        "id": "vaya_koshtha",
        "name": "Vaya & Koshtha Pariksha (Age Factor & Bowel Habit)",
        "question_en": "How are your daily bowel movements (Koshtha)?",
        "question_hi": "आपका पेट साफ होने की प्रकृति (कोष्ठ) कैसी है?",
        "options": [
            {"label_en": "Hard stools, chronic tendency for constipation (Krura Koshtha)", "label_hi": "कठोर मल, कब्ज की पुरानी प्रवृत्ति (क्रूर कोष्ठ)", "koshtha": "krura", "dosha": "vata"},
            {"label_en": "Loose stools easily triggered by milk/spices (Mridu Koshtha)", "label_hi": "आसानी से दस्त या पतला पेट होना (मृदु कोष्ठ)", "koshtha": "mridu", "dosha": "pitta"},
            {"label_en": "Regular, smooth, formed stool once or twice daily (Madhyama Koshtha)", "label_hi": "नियमित, बंधा हुआ मल दिन में 1-2 बार (मध्यम कोष्ठ)", "koshtha": "madhyama", "dosha": "kapha"}
        ]
    }
]


def evaluate_prakriti_and_dosha(answers: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes Prakriti (Constitutional assessment) score across Vata, Pitta, Kapha
    from Dashavidha Pariksha recorded responses.
    """
    scores = {"vata": 0, "pitta": 0, "kapha": 0}
    agni = "sama"
    koshtha = "madhyama"

    for stage_id, ans in answers.items():
        ans_text = str(ans).lower()
        if "vata" in ans_text or "रूखी" in ans_text or "क्रूर" in ans_text or "vishama" in ans_text:
            scores["vata"] += 1
        if "pitta" in ans_text or "जलन" in ans_text or "गर्मी" in ans_text or "मृदु" in ans_text or "tikshna" in ans_text:
            scores["pitta"] += 1
        if "kapha" in ans_text or "भारी" in ans_text or "सुस्ती" in ans_text or "manda" in ans_text:
            scores["kapha"] += 1

        # Check explicit agni/koshtha keywords
        if "vishama" in ans_text or "विषम" in ans_text:
            agni = "vishama"
        elif "tikshna" in ans_text or "तीक्ष्ण" in ans_text:
            agni = "tikshna"
        elif "manda" in ans_text or "मंद" in ans_text:
            agni = "manda"

        if "krura" in ans_text or "क्रूर" in ans_text or "constipation" in ans_text:
            koshtha = "krura"
        elif "mridu" in ans_text or "मृदु" in ans_text or "loose" in ans_text:
            koshtha = "mridu"

    total = max(sum(scores.values()), 1)
    v_pct = round((scores["vata"] / total) * 100)
    p_pct = round((scores["pitta"] / total) * 100)
    k_pct = round((scores["kapha"] / total) * 100)

    # Determine primary and secondary dosha
    sorted_doshas = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    primary = sorted_doshas[0][0].capitalize()
    secondary = sorted_doshas[1][0].capitalize()

    if scores[sorted_doshas[0][0]] == scores[sorted_doshas[1][0]]:
        prakriti_type = f"Dwandwaja ({primary}-{secondary})"
    elif sorted_doshas[0][1] >= 4:
        prakriti_type = f"Ekadoshaja ({primary}-dominant)"
    else:
        prakriti_type = f"{primary}-{secondary}"

    return {
        "prakriti_type": prakriti_type,
        "primary_dosha": primary,
        "secondary_dosha": secondary,
        "scores": {
            "vata": v_pct,
            "pitta": p_pct,
            "kapha": k_pct
        },
        "raw_counts": scores,
        "agni": agni,
        "koshtha": koshtha
    }


def generate_ayush_clinical_lens(
    chief_complaint: str,
    hpi: Dict[str, Any],
    prakriti_result: Dict[str, Any],
    red_flags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Generates the classical Ayurvedic 8-fold diagnostic clinical summary:
    - Nidana (Aetiological factors / Root causes)
    - Purvarupa (Prodromal signs)
    - Rupa (Manifest clinical signs)
    - Upashaya / Anupashaya (Relieving / Aggravating factors)
    - Samprapti (Pathogenesis / Dosha-Dushya involvement)
    - Agni & Koshtha assessment
    - Pathya & Apathya (Dietary / lifestyle recommendations & contraindications)
    - Chikitsa Sootra (Principle of Ayurvedic line of treatment)
    """
    primary = prakriti_result.get("primary_dosha", "Vata")
    agni = prakriti_result.get("agni", "sama")
    koshtha = prakriti_result.get("koshtha", "madhyama")

    cc_lower = chief_complaint.lower() if chief_complaint else ""
    character = hpi.get("character", "")
    site = hpi.get("site", "")
    radiation = hpi.get("radiation", "")

    # 1. Nidana (Causative factors)
    nidana_list = []
    if "pain" in cc_lower or "chest" in cc_lower or "vata" in primary.lower():
        nidana_list.extend([
            "Vata-prakopaka ahara (Dry, light, cold food intake, skipping meals)",
            "Ati-vyayama or Vega-dharana (Overexertion or suppression of natural physiological urges)",
            "Chinta & Shoka (Mental anxiety and emotional stress)"
        ])
    elif "burn" in cc_lower or "acid" in cc_lower or "pitta" in primary.lower():
        nidana_list.extend([
            "Katu-Amla-Lavana ati-sevana (Excessive spicy, sour, fried and fermented food)",
            "Ushna ahara and irregular meal timings triggering Pitta vitiation",
            "Krodha (Anger) and psychological irritability"
        ])
    else:
        nidana_list.extend([
            "Guru, Snigdha, Sheeta ahara (Heavy, sweet, dairy, sluggish diet)",
            "Divaswapna (Daytime sleep and sedentary lifestyle)",
            "Manda Agni leading to Ama (undigested metabolic toxins)"
        ])

    # 2. Purvarupa (Prodromal symptoms)
    purvarupa = [
        "Aruchi (Loss of appetite or tastelessness in mouth)",
        "Gatra gourava (Heaviness in limbs or retrosternal tightness)",
        "Alasya and irregular digestion prior to episode"
    ]

    # 3. Rupa (Manifest symptoms)
    rupa_items = [f"Pradhana Vedana (Primary complaint): {chief_complaint}"]
    if site:
        rupa_items.append(f"Sthana (Anatomical site): {site}")
    if character:
        rupa_items.append(f"Lakshana swarupa (Nature of pain): {character}")
    if radiation:
        rupa_items.append(f"Prasarana (Radiation): {radiation}")

    # 4. Upashaya / Anupashaya
    upashaya = {
        "upashaya_relieving": [
            "Ushna jala pana (Warm water sips)",
            "Vishrama (Complete rest in quiet environment)",
            "Laghu deepana ahara (Light, easily digestible warm soup)"
        ],
        "anupashaya_aggravating": [
            "Ati-vyayama (Physical exertion, brisk climbing)",
            "Sheeta ahara/vihara (Cold water, exposed cold wind)",
            "Shoka / Mansik chinta (Psychological agitation)"
        ]
    }

    # 5. Samprapti (Pathogenesis)
    samprapti = {
        "dosha": f"{primary} pradhana Tridosha imbalance",
        "dushya": "Rasa, Rakta, Mamsa, Meda",
        "srotas": "Pranavaha and Annavaha Srotas",
        "sroto_dushti": "Sanga (Obstruction / Atherosclerotic/spastic block) & Vimarga Gamana",
        "udbhava_sthana": "Amashaya & Hridaya",
        "vyakta_sthana": site if site else "Hridaya / Uras (Chest region)",
        "summary": f"Vitiated {primary} dosha combined with Ama causes Srotorodha (vascular/tissue resistance) manifesting as acute distress in {site or 'target sthana'}."
    }

    # 6. Agni & Koshtha
    agni_koshtha = {
        "agni_status": f"{agni.capitalize()} Agni (Digestive/Metabolic fire status)",
        "koshtha_type": f"{koshtha.capitalize()} Koshtha (Bowel constitution)",
        "clinical_note": "Requires Deepana-Pachana (carminative-digestive) stabilization."
    }

    # 7. Pathya & Apathya (Do's & Don'ts)
    if "pitta" in primary.lower():
        pathya = [
            "Ghrita (moderate cow's ghee), Moong dal khichdi, pomegranate, coriander water",
            "Cool, serene surroundings, adequate hydration, pranayama"
        ]
        apathya = [
            "Chilli, mustard, fermented pickles, caffeine, tobacco, extreme sun exposure",
            "Suppression of hunger or anger outbursts"
        ]
    elif "kapha" in primary.lower():
        pathya = [
            "Warm barley, old rice, warm ginger water, roasted cumin, trikatu in moderation",
            "Active brisk walking, early rising before sunrise"
        ]
        apathya = [
            "Curd/yoghurt, sweets, cold ice creams, daytime sleep (Divaswapna)",
            "Excessive sedentary sitting and over-eating"
        ]
    else:  # Vata
        pathya = [
            "Warm cooked meals, sesame oil or warm milk with nutmeg at bedtime, stewed apples",
            "Warm clothing, regular quiet sleep schedule, gentle abhyanga (oil massage) if non-acute"
        ]
        apathya = [
            "Raw salads, dry snacks (chips, roasted gram), fasting, cold refrigerated drinks",
            "Strenuous late-night wakefulness (Ratri jagarana)"
        ]

    # 8. Chikitsa Sootra (Therapeutic Protocol)
    chikitsa_sootra = (
        f"1. Nidana Parivarjana (Avoid identified triggers) -> "
        f"2. Deepana-Pachana with Laghu Ahara -> "
        f"3. {primary} Shamana Chikitsa with classical formulations (e.g., Prabhakar Vati, Arjunarishta for Hridaya; Hingwashtak for Pachana) -> "
        f"4. Rasayana therapy for tissue rejuvenation once acute episode is stabilized."
    )

    return {
        "lens": "ayurvedic",
        "prakriti": prakriti_result,
        "nidana": nidana_list,
        "purvarupa": purvarupa,
        "rupa": rupa_items,
        "upashaya": upashaya,
        "samprapti": samprapti,
        "agni_koshtha": agni_koshtha,
        "pathya_apathya": {
            "pathya": pathya,
            "apathya": apathya
        },
        "chikitsa_sootra": chikitsa_sootra
    }
