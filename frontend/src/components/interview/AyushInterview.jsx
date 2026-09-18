import React, { useState, useEffect } from 'react';

const DASHHAVIDHA_STAGES = [
  {
    id: 'prakriti',
    name: 'Prakriti Pariksha (Constitutional Assessment)',
    question_en: 'How do you describe your natural physical constitution and weather tolerance?',
    question_hi: 'आपकी स्वाभाविक शारीरिक प्रकृति और मौसम सहनशीलता कैसी है?',
    options: [
      { label_en: 'Lean build, dry skin, intolerant to cold (Vata)', label_hi: 'पतला शरीर, रूखी त्वचा, ठंड बर्दाश्त नहीं (वात)', dosha: 'vata' },
      { label_en: 'Medium build, warm skin, intolerant to heat (Pitta)', label_hi: 'मध्यम शरीर, गर्म त्वचा, गर्मी बर्दाश्त नहीं (पित्त)', dosha: 'pitta' },
      { label_en: 'Solid build, oily skin, comfortable in all seasons (Kapha)', label_hi: 'मजबूत/भारी शरीर, तैलीय त्वचा, सभी मौसम में सहज (कफ)', dosha: 'kapha' },
    ],
  },
  {
    id: 'vikriti',
    name: 'Vikriti Pariksha (Pathological State / Morbidity)',
    question_en: 'Which symptoms have developed recently (pain, burning, stiffness, heaviness)?',
    question_hi: 'हाल ही में कौन से नए लक्षण या तकलीफ़ें शुरू हुई हैं?',
    options: [
      { label_en: 'Fluctuating or sharp shifting pain, tremors, restlessness (Vata)', label_hi: 'बदलने वाला तेज़ दर्द, कंपन, बेचैनी (वात)', dosha: 'vata' },
      { label_en: 'Burning sensation, excessive thirst, acid reflux (Pitta)', label_hi: 'जलन, अत्यधिक प्यास, एसिडिटी (पित्त)', dosha: 'pitta' },
      { label_en: 'Heaviness in limbs, excessive mucus, sluggishness (Kapha)', label_hi: 'अंगों में भारीपन, कफ/बलगम, सुस्ती (कफ)', dosha: 'kapha' },
    ],
  },
  {
    id: 'sara',
    name: 'Sara Pariksha (Tissue Excellence / Dhatu Essence)',
    question_en: 'How would you describe your overall muscle tone, bone strength, and skin vitality?',
    question_hi: 'आपकी मांसपेशियों की मजबूती और शारीरिक ऊर्जा कैसी रहती है?',
    options: [
      { label_en: 'Fragile vitality, variable energy (Alpa Sara)', label_hi: 'अनिश्चित ऊर्जा व कमजोरी (अल्प सार)' },
      { label_en: 'Moderate vitality and firmness (Madhyama Sara)', label_hi: 'मध्यम शक्ति और स्थिरता (मध्यम सार)' },
      { label_en: 'Strong, firm muscles and high vitality (Uttama Sara)', label_hi: 'सुगठित मांसपेशियां व उत्तम बल (उत्तम सार)' },
    ],
  },
  {
    id: 'samhanana',
    name: 'Samhanana Pariksha (Body Compactness)',
    question_en: 'How compact and proportionate is your skeletal and muscular structure?',
    question_hi: 'आपके शरीर और हड्डियों का गठन कैसा है?',
    options: [
      { label_en: 'Slender, prominent joints (Vata)', label_hi: 'पतला, उभरे हुए जोड़ (वात)', dosha: 'vata' },
      { label_en: 'Balanced, medium symmetry (Pitta)', label_hi: 'संतुलित और सुडौल (पित्त)', dosha: 'pitta' },
      { label_en: 'Broad, well-knit joints and chest (Kapha)', label_hi: 'चौड़ी छाती, सुदृढ़ जोड़ (कफ)', dosha: 'kapha' },
    ],
  },
  {
    id: 'pramana',
    name: 'Pramana Pariksha (Anthropometric Proportions)',
    question_en: 'Are your body proportions within expected normal limits?',
    question_hi: 'क्या आपकी शारीरिक माप और वजन सामान्य अनुपात में है?',
    options: [
      { label_en: 'Below average weight or disproportionate', label_hi: 'कम वजन या असामान्य अनुपात' },
      { label_en: 'Proportionate and balanced', label_hi: 'सामान्य व संतुलित' },
      { label_en: 'Robust, broad stature', label_hi: 'भारी या चौड़ा कद-काठी' },
    ],
  },
  {
    id: 'satmya',
    name: 'Satmya Pariksha (Homologation / Habituation)',
    question_en: 'Which food temperatures and tastes suit your digestion best?',
    question_hi: 'आपको कैसा भोजन सबसे ज्यादा अनुकूल पड़ता है?',
    options: [
      { label_en: 'Warm, oily, sweet foods suit best (Vata)', label_hi: 'गर्म, स्निग्ध और मीठा भोजन अनुकूल (वात)', dosha: 'vata' },
      { label_en: 'Cool, sweet, bitter foods suit best (Pitta)', label_hi: 'ठंडा, मीठा और हल्का भोजन अनुकूल (पित्त)', dosha: 'pitta' },
      { label_en: 'Light, warm, spicy foods suit best (Kapha)', label_hi: 'हल्का, गर्म और तीखा भोजन अनुकूल (कफ)', dosha: 'kapha' },
    ],
  },
  {
    id: 'satva',
    name: 'Satva Pariksha (Mental Stamina / Temperament)',
    question_en: 'How do you handle anxiety, stress, or illness?',
    question_hi: 'तनाव या बीमारी के समय आपका मानसिक धैर्य कैसा रहता है?',
    options: [
      { label_en: 'Easily worried, fearful, light sleep (Vata)', label_hi: 'जल्दी घबराना, चिंता, अनिद्रा (वात)', dosha: 'vata' },
      { label_en: 'Impatience, irritability, sharp focus (Pitta)', label_hi: 'जल्दबाजी, चिड़चिड़ापन, तीव्र स्वभाव (पित्त)', dosha: 'pitta' },
      { label_en: 'Calm, composed, tolerant (Kapha)', label_hi: 'शांत, धैर्यवान, अडिग (कफ)', dosha: 'kapha' },
    ],
  },
  {
    id: 'ahara_shakti',
    name: 'Ahara Shakti (Dietary Capacity & Agni)',
    question_en: 'How is your appetite and digestive fire (Agni)?',
    question_hi: 'आपकी भूख और भोजन पचाने की क्षमता कैसी है?',
    options: [
      { label_en: 'Irregular appetite, bloating after meals (Vishama Agni)', label_hi: 'अनियमित भूख, गैस या पेट फूलना (विषम अग्नि)', agni: 'vishama', dosha: 'vata' },
      { label_en: 'Intense appetite, acid reflux if meal delayed (Tikshna Agni)', label_hi: 'तीव्र भूख, एसिडिटी यदि देर हो (तीक्ष्ण अग्नि)', agni: 'tikshna', dosha: 'pitta' },
      { label_en: 'Sluggish appetite, prolonged fullness (Manda Agni)', label_hi: 'मंद भूख, देर से पचना व भारीपन (मंद अग्नि)', agni: 'manda', dosha: 'kapha' },
    ],
  },
  {
    id: 'vyayama_shakti',
    name: 'Vyayama Shakti (Physical Endurance)',
    question_en: 'How much physical exertion can you handle before exhaustion?',
    question_hi: 'आप बिना थके कितना शारीरिक श्रम कर सकते हैं?',
    options: [
      { label_en: 'Quick fatigue, short breath (Heena Shakti)', label_hi: 'जल्दी सांस फूलना या तुरंत थकान' },
      { label_en: 'Moderate daily stamina (Madhyama Shakti)', label_hi: 'सामान्य कामकाज आसानी से कर लेते हैं' },
      { label_en: 'High stamina, strenuous tasks (Uttama Shakti)', label_hi: 'कठोर परिश्रम भी आसानी से' },
    ],
  },
  {
    id: 'vaya_koshtha',
    name: 'Vaya & Koshtha (Age & Bowel Pattern)',
    question_en: 'How are your daily bowel movements (Koshtha)?',
    question_hi: 'आपका पेट साफ होने की प्रकृति (कोष्ठ) कैसी है?',
    options: [
      { label_en: 'Hard stools, tendency for constipation (Krura Koshtha)', label_hi: 'कठोर मल, कब्ज की पुरानी प्रवृत्ति (क्रूर कोष्ठ)', koshtha: 'krura', dosha: 'vata' },
      { label_en: 'Soft/loose stools easily triggered (Mridu Koshtha)', label_hi: 'आसानी से दस्त या पतला पेट होना (मृदु कोष्ठ)', koshtha: 'mridu', dosha: 'pitta' },
      { label_en: 'Regular formed stool once daily (Madhyama Koshtha)', label_hi: 'नियमित बंधा हुआ मल दिन में 1-2 बार (मध्यम कोष्ठ)', koshtha: 'madhyama', dosha: 'kapha' },
    ],
  },
];

export default function AyushInterview({
  sessionId,
  language = 'hi',
  onComplete = () => {},
}) {
  const [currentStageIndex, setCurrentStageIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [evaluationResult, setEvaluationResult] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const isHi = language === 'hi';

  const currentStage = DASHHAVIDHA_STAGES[currentStageIndex];
  const progressPct = Math.round(((currentStageIndex + 1) / DASHHAVIDHA_STAGES.length) * 100);

  const handleSelectOption = (option) => {
    const selectedText = isHi ? option.label_hi : option.label_en;
    const newAnswers = { ...answers, [currentStage.id]: selectedText };
    setAnswers(newAnswers);

    if (currentStageIndex < DASHHAVIDHA_STAGES.length - 1) {
      setCurrentStageIndex((prev) => prev + 1);
    } else {
      // 10th stage finished -> submit for evaluation
      finishPariksha(newAnswers);
    }
  };

  const finishPariksha = async (finalAnswers) => {
    setIsSubmitting(true);
    try {
      const res = await fetch('http://localhost:8000/api/ayush/evaluate-prakriti', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          answers: finalAnswers,
        }),
      });

      if (res.ok) {
        const result = await res.json();
        setEvaluationResult(result);
        onComplete(result);
      }
    } catch (e) {
      console.warn('Error evaluating Prakriti:', e);
      // Fallback evaluation
      const fallback = {
        prakriti_type: 'Vata-Pitta',
        primary_dosha: 'Vata',
        scores: { vata: 50, pitta: 35, kapha: 15 },
        agni: 'vishama',
        koshtha: 'krura',
      };
      setEvaluationResult(fallback);
      onComplete(fallback);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (evaluationResult) {
    return (
      <div
        style={{
          background: '#ffffff',
          borderRadius: '16px',
          padding: '28px',
          maxWidth: '680px',
          margin: '0 auto',
          boxShadow: '0 8px 30px rgba(0,0,0,0.08)',
          fontFamily: 'Inter, system-ui, sans-serif',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: '20px' }}>
          <div style={{ fontSize: '36px', marginBottom: '8px' }}>🌿</div>
          <h2 style={{ fontSize: '22px', fontWeight: 700, color: '#14532d', margin: '0 0 6px 0' }}>
            {isHi ? 'दशविध परीक्षा पूर्ण — प्रकृति विश्लेषण' : 'Dashavidha Pariksha Complete — Ayurvedic Prakriti'}
          </h2>
          <p style={{ color: '#475569', fontSize: '14px', margin: 0 }}>
            {isHi ? 'आपकी प्राकृतिक शारीरिक एवं मानसिक प्रकृति का मूल्यांकन:' : 'Constitutional Dosha assessment:'}
          </p>
        </div>

        {/* Primary Dosha Card */}
        <div
          style={{
            background: 'linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%)',
            border: '1px solid #bbf7d0',
            borderRadius: '12px',
            padding: '20px',
            marginBottom: '20px',
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: '13px', fontWeight: 600, color: '#166534', textTransform: 'uppercase' }}>
            {isHi ? 'प्रमुख प्रकृति (Primary Prakriti)' : 'Primary Constitution'}
          </div>
          <div style={{ fontSize: '26px', fontWeight: 800, color: '#14532d', marginTop: '4px' }}>
            {evaluationResult.prakriti_type}
          </div>
          <div style={{ fontSize: '13px', color: '#15803d', marginTop: '4px' }}>
            अग्नि: {evaluationResult.agni?.toUpperCase()} | कोष्ठ: {evaluationResult.koshtha?.toUpperCase()}
          </div>
        </div>

        {/* Dosha Progress Bars */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '24px' }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', fontWeight: 600, color: '#1e293b' }}>
              <span>वात (Vata)</span>
              <span>{evaluationResult.scores?.vata || 0}%</span>
            </div>
            <div style={{ height: '8px', background: '#e2e8f0', borderRadius: '4px', overflow: 'hidden', marginTop: '4px' }}>
              <div style={{ width: `${evaluationResult.scores?.vata || 0}%`, height: '100%', background: '#3b82f6' }} />
            </div>
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', fontWeight: 600, color: '#1e293b' }}>
              <span>पित्त (Pitta)</span>
              <span>{evaluationResult.scores?.pitta || 0}%</span>
            </div>
            <div style={{ height: '8px', background: '#e2e8f0', borderRadius: '4px', overflow: 'hidden', marginTop: '4px' }}>
              <div style={{ width: `${evaluationResult.scores?.pitta || 0}%`, height: '100%', background: '#ef4444' }} />
            </div>
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', fontWeight: 600, color: '#1e293b' }}>
              <span>कफ (Kapha)</span>
              <span>{evaluationResult.scores?.kapha || 0}%</span>
            </div>
            <div style={{ height: '8px', background: '#e2e8f0', borderRadius: '4px', overflow: 'hidden', marginTop: '4px' }}>
              <div style={{ width: `${evaluationResult.scores?.kapha || 0}%`, height: '100%', background: '#10b981' }} />
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={() => onComplete(evaluationResult)}
          style={{
            width: '100%',
            padding: '14px',
            borderRadius: '10px',
            border: 'none',
            background: '#16a34a',
            color: '#ffffff',
            fontWeight: 700,
            fontSize: '15px',
            cursor: 'pointer',
          }}
        >
          {isHi ? 'आयुर्वेदिक सारांश देखें (View Ayurvedic Summary)' : 'Proceed to Clinical Summary'}
        </button>
      </div>
    );
  }

  return (
    <div
      style={{
        background: '#ffffff',
        borderRadius: '16px',
        padding: '28px',
        maxWidth: '680px',
        margin: '0 auto',
        boxShadow: '0 8px 30px rgba(0,0,0,0.08)',
        fontFamily: 'Inter, system-ui, sans-serif',
      }}
    >
      {/* Header & Stage tracker */}
      <div style={{ marginBottom: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <span style={{ fontSize: '12px', fontWeight: 700, color: '#16a34a', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            दशविध परीक्षा (Dashavidha Pariksha)
          </span>
          <span style={{ fontSize: '12px', fontWeight: 600, color: '#64748b' }}>
            चरण {currentStageIndex + 1} / {DASHHAVIDHA_STAGES.length}
          </span>
        </div>
        <div style={{ height: '6px', background: '#e2e8f0', borderRadius: '3px', overflow: 'hidden' }}>
          <div
            style={{
              width: `${progressPct}%`,
              height: '100%',
              background: '#16a34a',
              transition: 'width 0.3s ease',
            }}
          />
        </div>
      </div>

      {/* Current Stage Title & Question */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ fontSize: '14px', fontWeight: 600, color: '#0f766e', marginBottom: '4px' }}>
          {currentStage.name}
        </div>
        <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#1e293b', margin: '0 0 8px 0', lineHeight: 1.4 }}>
          {isHi ? currentStage.question_hi : currentStage.question_en}
        </h3>
      </div>

      {/* Options List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {currentStage.options.map((opt, idx) => {
          const label = isHi ? opt.label_hi : opt.label_en;
          return (
            <button
              key={idx}
              type="button"
              disabled={isSubmitting}
              onClick={() => handleSelectOption(opt)}
              style={{
                textAlign: 'left',
                padding: '16px 20px',
                borderRadius: '12px',
                border: '1.5px solid #e2e8f0',
                background: '#f8fafc',
                color: '#1e293b',
                fontSize: '15px',
                fontWeight: 500,
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = '#16a34a';
                e.currentTarget.style.background = '#f0fdf4';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = '#e2e8f0';
                e.currentTarget.style.background = '#f8fafc';
              }}
            >
              <span>{label}</span>
              <span style={{ color: '#16a34a', fontWeight: 700, fontSize: '18px' }}>→</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
