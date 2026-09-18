import React, { useState, useEffect, useRef } from 'react';
import KioskCard from './KioskCard';
import KioskButton from './KioskButton';
import { useSession } from '../../contexts/SessionContext';
import {
  ShieldCheck,
  Mic,
  Stethoscope,
  Clock,
  CheckCircle2,
  Volume2,
  ArrowRight,
  ArrowLeft,
  Lock,
  FileCheck,
  Check,
  X,
} from 'lucide-react';

// Translations for 3-Step Consent Flow
const CONSENT_TEXTS = {
  hi: {
    step1Title: 'सहमति व्याख्या (Data & Privacy Explanation)',
    step1Lead: 'आपकी गोपनीयता और सुरक्षा हमारी पहली प्राथमिकता है:',
    collectedTitle: 'क्या जानकारी एकत्र की जाएगी?',
    collectedDesc: 'आपकी आवाज में बताए गए लक्षण, पुरानी पर्चियों के फोटो, और दवाओं का विवरण।',
    whoSeesTitle: 'यह जानकारी कौन देखेगा?',
    whoSeesDesc: 'केवल आपके उपचार करने वाले डॉक्टर, ओपीडी परामर्श के दौरान।',
    retentionTitle: 'कितने समय तक रखी जाएगी?',
    retentionDesc: 'केवल आज के परामर्श तक। आपकी स्पष्ट अनुमति के बिना इसे कहीं भी स्थायी रूप से सुरक्षित नहीं किया जाएगा।',
    nextBtn: 'आगे बढ़ें (Next) →',
    backBtn: 'वापस (Back)',
    voiceNextBtn: 'आवाज पुष्टि हेतु आगे बढ़ें (Voice Confirmation) →',

    step2Title: 'सहमति विकल्प चुनें (Granular Permissions)',
    toggle1Title: 'इस परामर्श हेतु डॉक्टर के साथ मेरा इतिहास साझा करें',
    toggle1Sub: 'ओपीडी परामर्श हेतु आवश्यक (Mandatory for visit)',
    toggle2Title: 'भविष्य के परामर्श हेतु मेरे रिकॉर्ड ABDM में सुरक्षित करें',
    toggle2Sub: 'वैकल्पिक (Optional)',
    toggle3Title: 'चिकित्सा अनुसंधान हेतु अनाम डेटा का उपयोग करने दें',
    toggle3Sub: 'वैकल्पिक (Optional)',

    step3Title: 'आवाज द्वारा अंतिम पुष्टि (Voice Confirmation)',
    summaryTemplate: (t1, t2) =>
      `आपने डॉक्टर के साथ अपना इतिहास साझा करने की सहमति दी है। आपने ABDM में रिकॉर्ड ${
        t2 ? 'सुरक्षित करने का विकल्प चुना है' : 'सुरक्षित न करने का विकल्प चुना है'
      }। क्या आप पुष्टि करते हैं?`,
    speakPromptBtn: '🔊 पुनः सुनें (Listen Again)',
    listeningText: '🎙️ सुन रहे हैं... कृपया "हाँ" या "Yes" बोलें...',
    voiceCaptured: '✓ आवाज पुष्टि दर्ज: "हाँ, मैं सहमत हूँ"',
    confirmBtn: '✓ सहमति दें और शुरू करें (Confirm & Finish)',
  },
  en: {
    step1Title: 'Consent Explanation (Data & Privacy)',
    step1Lead: 'Your privacy and clinical safety are our top priorities:',
    collectedTitle: 'What data is collected?',
    collectedDesc: 'Your spoken symptoms, scanned paper prescriptions, and health intake answers.',
    whoSeesTitle: 'Who sees your data?',
    whoSeesDesc: 'Only your assigned treating doctor during this OPD consultation visit.',
    retentionTitle: 'How long is it stored?',
    retentionDesc: 'Only for this visit, unless you explicitly choose to link with ABDM.',
    nextBtn: 'Next Step →',
    backBtn: '← Back',
    voiceNextBtn: 'Proceed to Voice Confirmation →',

    step2Title: 'Granular Consent Toggles',
    toggle1Title: 'Share my history with the doctor for this visit',
    toggle1Sub: 'Mandatory for OPD consultation',
    toggle2Title: 'Store my records in ABDM for future visits',
    toggle2Sub: 'Optional',
    toggle3Title: 'Allow anonymized data for clinical research',
    toggle3Sub: 'Optional',

    step3Title: 'Voice Confirmation & Final Audit',
    summaryTemplate: (t1, t2) =>
      `You have agreed to share your history with the doctor. You have chosen ${
        t2 ? 'to store' : 'not to store'
      } records in ABDM. Do you confirm?`,
    speakPromptBtn: '🔊 Play Summary Again',
    listeningText: '🎙️ Listening... Please say "Yes" or "Haan"...',
    voiceCaptured: '✓ Voice evidence captured: "Yes, I confirm"',
    confirmBtn: '✓ Confirm Consent & Enter Kiosk',
  },
  pa: {
    step1Title: 'ਸਹਿਮਤੀ ਵੇਰਵਾ (Data & Privacy Explanation)',
    step1Lead: 'ਤੁਹਾਡੀ ਨਿੱਜਤਾ ਅਤੇ ਸੁਰੱਖਿਆ ਸਾਡੀ ਪਹਿਲੀ ਤਰਜੀਹ ਹੈ:',
    collectedTitle: 'ਕਿਹੜੀ ਜਾਣਕਾਰੀ ਇਕੱਠੀ ਕੀਤੀ ਜਾਵੇਗੀ?',
    collectedDesc: 'ਤੁਹਾਡੀ ਆਵਾਜ਼ ਵਿੱਚ ਦੱਸੇ ਗਏ ਲੱਛਣ, ਪੁਰਾਣੀਆਂ ਪਰਚੀਆਂ ਦੀਆਂ ਫ਼ੋਟੋਆਂ ਅਤੇ ਦਵਾਈਆਂ ਦਾ ਵੇਰਵਾ।',
    whoSeesTitle: 'ਇਹ ਜਾਣਕਾਰੀ ਕੌਣ ਦੇਖੇਗਾ?',
    whoSeesDesc: 'ਸਿਰਫ਼ ਤੁਹਾਡੇ ਇਲਾਜ ਕਰਨ ਵਾਲੇ ਡਾਕਟਰ, ਓਪੀਡੀ ਸਲਾਹ ਦੌਰਾਨ।',
    retentionTitle: 'ਕਿੰਨੇ ਸਮੇਂ ਲਈ ਰੱਖੀ ਜਾਵੇਗੀ?',
    retentionDesc: 'ਸਿਰਫ਼ ਅੱਜ ਦੀ ਸਲਾਹ ਤੱਕ। ਤੁਹਾਡੀ ਸਪੱਸ਼ਟ ਆਗਿਆ ਤੋਂ ਬਿਨਾਂ ਇਸਨੂੰ ਸਥਾਈ ਤੌਰ ਤੇ ਸੁਰੱਖਿਅਤ ਨਹੀਂ ਕੀਤਾ ਜਾਵੇਗਾ।',
    nextBtn: 'ਅੱਗੇ ਵਧੋ (Next) →',
    backBtn: 'ਵਾਪਸ (Back)',
    voiceNextBtn: 'ਆਵਾਜ਼ ਪੁਸ਼ਟੀ ਲਈ ਅੱਗੇ ਵਧੋ (Voice Confirmation) →',

    step2Title: 'ਸਹਿਮਤੀ ਵਿਕਲਪ ਚੁਣੋ (Granular Permissions)',
    toggle1Title: 'ਇਸ ਸਲਾਹ ਲਈ ਡਾਕਟਰ ਨਾਲ ਮੇਰਾ ਇਤਿਹਾਸ ਸਾਂਝਾ ਕਰੋ',
    toggle1Sub: 'ਓਪੀਡੀ ਸਲਾਹ ਲਈ ਲਾਜ਼ਮੀ (Mandatory for visit)',
    toggle2Title: 'ਭਵਿੱਖ ਦੀ ਸਲਾਹ ਲਈ ਮੇਰੇ ਰਿਕਾਰਡ ABDM ਵਿੱਚ ਸੁਰੱਖਿਅਤ ਕਰੋ',
    toggle2Sub: 'ਵਿਕਲਪਿਕ (Optional)',
    toggle3Title: 'ਮੈਡੀਕਲ ਖੋਜ ਲਈ ਅਗਿਆਤ ਡੇਟਾ ਦੀ ਵਰਤੋਂ ਕਰਨ ਦਿਓ',
    toggle3Sub: 'ਵਿਕਲਪਿਕ (Optional)',

    step3Title: 'ਆਵਾਜ਼ ਦੁਆਰਾ ਅੰਤਿਮ ਪੁਸ਼ਟੀ (Voice Confirmation)',
    summaryTemplate: (t1, t2) =>
      `ਤੁਸੀਂ ਡਾਕਟਰ ਨਾਲ ਆਪਣਾ ਇਤਿਹਾਸ ਸਾਂਝਾ ਕਰਨ ਦੀ ਸਹਿਮਤੀ ਦਿੱਤੀ ਹੈ। ਤੁਸੀਂ ABDM ਵਿੱਚ ਰਿਕਾਰਡ ${
        t2 ? 'ਸੁਰੱਖਿਅਤ ਕਰਨ ਦਾ ਵਿਕਲਪ ਚੁਣਿਆ ਹੈ' : 'ਸੁਰੱਖਿਅਤ ਨਾ ਕਰਨ ਦਾ ਵਿਕਲਪ ਚੁਣਿਆ ਹੈ'
      }। ਕੀ ਤੁਸੀਂ ਪੁਸ਼ਟੀ ਕਰਦੇ ਹੋ?`,
    speakPromptBtn: '🔊 ਦੁਬਾਰਾ ਸੁਣੋ (Listen Again)',
    listeningText: '🎙️ ਸੁਣ ਰਹੇ ਹਾਂ... ਕਿਰਪਾ ਕਰਕੇ "ਹਾਂ" ਜਾਂ "Yes" ਬੋਲੋ...',
    voiceCaptured: '✓ ਆਵਾਜ਼ ਪੁਸ਼ਟੀ ਦਰਜ: "ਹਾਂ, ਮੈਂ ਸਹਿਮਤ ਹਾਂ"',
    confirmBtn: '✓ ਸਹਿਮਤੀ ਦਿਓ ਅਤੇ ਸ਼ੁਰੂ ਕਰੋ (Confirm & Finish)',
  },
};

export const ConsentFlow = ({ onBack }) => {
  const { language, submitConsent, isLoading, error, patient, isCaregiver, caregiverDetails, voiceOnlyMode } = useSession();
  const [step, setStep] = useState(1);

  // Default toggles: toggle 1 is ON, toggles 2 & 3 are OFF
  const [consents, setConsents] = useState({
    share_doctor: true,
    store_abdm: false,
    anonymized_research: false,
  });

  const [voiceEvidence, setVoiceEvidence] = useState(null);
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef(null);

  const t = CONSENT_TEXTS[language] || CONSENT_TEXTS.hi;

  // Speak Step 3 summary on arrival
  useEffect(() => {
    if (step === 3 && 'speechSynthesis' in window) {
      playTtsSummary();
      startVoiceListening();
    }
  }, [step]);

  const playTtsSummary = () => {
    try {
      window.speechSynthesis.cancel();
      const text = t.summaryTemplate(consents.share_doctor, consents.store_abdm);
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = language === 'hi' ? 'hi-IN' : 'en-US';
      utterance.rate = 0.95;
      window.speechSynthesis.speak(utterance);
    } catch (err) {
      console.warn('TTS prompt failed:', err);
    }
  };

  const startVoiceListening = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      try {
        const recognition = new SpeechRecognition();
        recognition.lang = language === 'hi' ? 'hi-IN' : 'en-US';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        recognition.onstart = () => setIsListening(true);
        recognition.onend = () => setIsListening(false);
        recognition.onresult = (event) => {
          const spoken = event.results[0][0].transcript;
          setVoiceEvidence(`voice_asr_sample: "${spoken}"`);
        };
        recognition.start();
        recognitionRef.current = recognition;
      } catch (e) {
        setIsListening(false);
      }
    } else {
      // Fallback: simulated voice evidence
      setVoiceEvidence('voice_touch_confirmed_evidence_ref_01');
    }
  };

  const handleToggle = (key) => {
    if (key === 'share_doctor') return; // Mandatory for consultation
    setConsents((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleFinalSubmit = async () => {
    const voiceRef = voiceEvidence || 'voice_touch_confirmed_evidence_ref_01';
    await submitConsent(consents, voiceRef);
  };

  return (
    <div
      style={{
        width: '100%',
        maxWidth: '860px',
        margin: '0 auto',
        padding: '28px 20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '24px',
      }}
    >
      {/* Step Indicator Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <KioskButton
          variant="secondary"
          size="sm"
          icon={<ArrowLeft size={18} />}
          onClick={step > 1 ? () => setStep(step - 1) : onBack}
        >
          {t.backBtn}
        </KioskButton>

        {/* 3-Step Breadcrumb */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {[
            { num: 1, label: 'व्याख्या (Info)' },
            { num: 2, label: 'विकल्प (Options)' },
            { num: 3, label: 'पुष्टि (Confirm)' },
          ].map((s) => {
            const isActive = step === s.num;
            const isCompleted = step > s.num;
            return (
              <div
                key={s.num}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '6px 12px',
                  borderRadius: '999px',
                  background: isActive ? '#ECFDF5' : isCompleted ? '#F1F5F9' : '#FFFFFF',
                  border: `1.5px solid ${isActive ? '#059669' : isCompleted ? '#CBD5E1' : '#E2E8F0'}`,
                  color: isActive ? '#065F46' : isCompleted ? '#0F172A' : '#64748B',
                  fontSize: '13px',
                  fontWeight: 700,
                }}
              >
                <span
                  style={{
                    width: '20px',
                    height: '20px',
                    borderRadius: '50%',
                    background: isActive ? '#059669' : isCompleted ? '#0F172A' : '#CBD5E1',
                    color: '#FFFFFF',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '11px',
                  }}
                >
                  {isCompleted ? '✓' : s.num}
                </span>
                <span>{s.label}</span>
              </div>
            );
          })}
        </div>
      </div>

      {error && (
        <div
          style={{
            padding: '16px',
            background: '#FEF2F2',
            border: '2px solid #EF4444',
            borderRadius: '14px',
            color: '#991B1B',
            fontSize: '15px',
            fontWeight: 700,
          }}
        >
          ⚠️ {error}
        </div>
      )}

      {/* TASK 2: Caregiver Proxy Consent Affirmation Banner */}
      {isCaregiver && (
        <div
          style={{
            padding: '16px 20px',
            borderRadius: '14px',
            background: '#FFFBEB',
            border: '2px solid #F59E0B',
            color: '#92400E',
            display: 'flex',
            alignItems: 'center',
            gap: '14px',
            boxShadow: '0 2px 8px rgba(245, 158, 11, 0.1)',
          }}
        >
          <div style={{ fontSize: '24px' }}>🤝</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 800, fontSize: '15px' }}>
              {language === 'en'
                ? `Authorized Caregiver Consent: ${caregiverDetails.name || 'Caregiver'} (${caregiverDetails.relationship})`
                : `अधिकृत देखभालकर्ता सहमति: ${caregiverDetails.name || 'देखभालकर्ता'} (${caregiverDetails.relationship})`}
            </div>
            <div style={{ fontSize: '13px', marginTop: '3px', lineHeight: '1.4' }}>
              {language === 'en'
                ? `I confirm I am authorized to share health information and grant consent on behalf of patient ${patient?.name || 'the patient'}.`
                : `मैं पुष्टि करता/करती हूँ कि मैं मरीज ${patient?.name || 'मरीज'} की ओर से स्वास्थ्य जानकारी साझा करने और सहमति देने हेतु अधिकृत हूँ।`}
            </div>
          </div>
        </div>
      )}

      {/* STEP 1: Plain Language Privacy Explanation */}
      {step === 1 && (
        <KioskCard padding="36px">
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '8px' }}>
            <div
              style={{
                width: '48px',
                height: '48px',
                borderRadius: '12px',
                background: '#ECFDF5',
                color: '#059669',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <ShieldCheck size={28} />
            </div>
            <div>
              <h2 style={{ fontSize: '26px', fontWeight: 800, color: '#0F172A', margin: 0 }}>
                {t.step1Title}
              </h2>
              <p style={{ fontSize: '16px', color: '#475569', margin: '2px 0 0 0' }}>
                {t.step1Lead}
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', margin: '28px 0' }}>
            {/* Fact 1 */}
            <div
              style={{
                display: 'flex',
                gap: '18px',
                padding: '20px',
                background: '#F8FAFC',
                borderRadius: '14px',
                border: '1.5px solid #E2E8F0',
                alignItems: 'flex-start',
              }}
            >
              <div
                style={{
                  width: '44px',
                  height: '44px',
                  borderRadius: '12px',
                  background: '#ECFDF5',
                  color: '#059669',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}
              >
                <Mic size={24} />
              </div>
              <div>
                <h4 style={{ fontSize: '18px', fontWeight: 800, color: '#0F172A', margin: '0 0 4px 0' }}>
                  {t.collectedTitle}
                </h4>
                <p style={{ fontSize: '15px', color: '#334155', margin: 0, lineHeight: 1.4 }}>
                  {t.collectedDesc}
                </p>
              </div>
            </div>

            {/* Fact 2 */}
            <div
              style={{
                display: 'flex',
                gap: '18px',
                padding: '20px',
                background: '#F8FAFC',
                borderRadius: '14px',
                border: '1.5px solid #E2E8F0',
                alignItems: 'flex-start',
              }}
            >
              <div
                style={{
                  width: '44px',
                  height: '44px',
                  borderRadius: '12px',
                  background: '#F0F9FF',
                  color: '#0284C7',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}
              >
                <Stethoscope size={24} />
              </div>
              <div>
                <h4 style={{ fontSize: '18px', fontWeight: 800, color: '#0F172A', margin: '0 0 4px 0' }}>
                  {t.whoSeesTitle}
                </h4>
                <p style={{ fontSize: '15px', color: '#334155', margin: 0, lineHeight: 1.4 }}>
                  {t.whoSeesDesc}
                </p>
              </div>
            </div>

            {/* Fact 3 */}
            <div
              style={{
                display: 'flex',
                gap: '18px',
                padding: '20px',
                background: '#F8FAFC',
                borderRadius: '14px',
                border: '1.5px solid #E2E8F0',
                alignItems: 'flex-start',
              }}
            >
              <div
                style={{
                  width: '44px',
                  height: '44px',
                  borderRadius: '12px',
                  background: '#FFFBEB',
                  color: '#D97706',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}
              >
                <Clock size={24} />
              </div>
              <div>
                <h4 style={{ fontSize: '18px', fontWeight: 800, color: '#0F172A', margin: '0 0 4px 0' }}>
                  {t.retentionTitle}
                </h4>
                <p style={{ fontSize: '15px', color: '#334155', margin: 0, lineHeight: 1.4 }}>
                  {t.retentionDesc}
                </p>
              </div>
            </div>
          </div>

          <KioskButton
            variant="primary"
            size="xl"
            fullWidth
            icon={<ArrowRight size={26} />}
            iconPosition="right"
            onClick={() => setStep(2)}
            sublabel="Choose permissions"
          >
            {t.nextBtn}
          </KioskButton>
        </KioskCard>
      )}

      {/* STEP 2: Granular Consent Toggles */}
      {step === 2 && (
        <KioskCard padding="36px">
          <h2 style={{ fontSize: '26px', fontWeight: 800, color: '#0F172A', marginBottom: '6px' }}>
            {t.step2Title}
          </h2>
          <p style={{ fontSize: '16px', color: '#475569', marginBottom: '28px' }}>
            कृपया अपनी इच्छानुसार विकल्पों का चयन करें (Select your preferences):
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '32px' }}>
            {/* Toggle 1: Mandatory for Doctor Visit */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '20px 22px',
                borderRadius: '16px',
                background: '#ECFDF5',
                border: '2.5px solid #059669',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                <div
                  style={{
                    width: '38px',
                    height: '38px',
                    borderRadius: '10px',
                    background: '#059669',
                    color: '#FFFFFF',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <Lock size={20} />
                </div>
                <div>
                  <strong style={{ fontSize: '18px', color: '#065F46', display: 'block' }}>
                    {t.toggle1Title}
                  </strong>
                  <span style={{ fontSize: '14px', color: '#059669', fontWeight: 700 }}>
                    ✓ {t.toggle1Sub}
                  </span>
                </div>
              </div>

              <div
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  background: '#059669',
                  color: '#FFFFFF',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Check size={20} strokeWidth={3} />
              </div>
            </div>

            {/* Toggle 2: ABDM Health Locker Storage */}
            <div
              onClick={() => handleToggle('store_abdm')}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '20px 22px',
                borderRadius: '16px',
                background: consents.store_abdm ? '#F0F9FF' : '#FFFFFF',
                border: `2.5px solid ${consents.store_abdm ? '#0284C7' : '#E2E8F0'}`,
                cursor: 'pointer',
                boxShadow: '0 2px 6px rgba(15, 23, 42, 0.04)',
                transition: 'all 0.15s ease',
              }}
            >
              <div>
                <strong style={{ fontSize: '18px', color: '#0F172A', display: 'block' }}>
                  {t.toggle2Title}
                </strong>
                <span style={{ fontSize: '14px', color: '#64748B', fontWeight: 600 }}>
                  {t.toggle2Sub}
                </span>
              </div>

              <div
                style={{
                  width: '56px',
                  height: '32px',
                  borderRadius: '999px',
                  background: consents.store_abdm ? '#0284C7' : '#CBD5E1',
                  display: 'flex',
                  alignItems: 'center',
                  padding: '3px',
                  transition: 'all 0.2s ease',
                }}
              >
                <div
                  style={{
                    width: '26px',
                    height: '26px',
                    borderRadius: '50%',
                    background: '#FFFFFF',
                    transform: consents.store_abdm ? 'translateX(24px)' : 'translateX(0)',
                    transition: 'transform 0.2s ease',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
                  }}
                />
              </div>
            </div>

            {/* Toggle 3: Research Sharing */}
            <div
              onClick={() => handleToggle('anonymized_research')}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '20px 22px',
                borderRadius: '16px',
                background: consents.anonymized_research ? '#F0F9FF' : '#FFFFFF',
                border: `2.5px solid ${consents.anonymized_research ? '#0284C7' : '#E2E8F0'}`,
                cursor: 'pointer',
                boxShadow: '0 2px 6px rgba(15, 23, 42, 0.04)',
                transition: 'all 0.15s ease',
              }}
            >
              <div>
                <strong style={{ fontSize: '18px', color: '#0F172A', display: 'block' }}>
                  {t.toggle3Title}
                </strong>
                <span style={{ fontSize: '14px', color: '#64748B', fontWeight: 600 }}>
                  {t.toggle3Sub}
                </span>
              </div>

              <div
                style={{
                  width: '56px',
                  height: '32px',
                  borderRadius: '999px',
                  background: consents.anonymized_research ? '#0284C7' : '#CBD5E1',
                  display: 'flex',
                  alignItems: 'center',
                  padding: '3px',
                  transition: 'all 0.2s ease',
                }}
              >
                <div
                  style={{
                    width: '26px',
                    height: '26px',
                    borderRadius: '50%',
                    background: '#FFFFFF',
                    transform: consents.anonymized_research ? 'translateX(24px)' : 'translateX(0)',
                    transition: 'transform 0.2s ease',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
                  }}
                />
              </div>
            </div>
          </div>

          <KioskButton
            variant="primary"
            size="xl"
            fullWidth
            icon={<ArrowRight size={26} />}
            iconPosition="right"
            onClick={() => setStep(3)}
            sublabel="Audio read-back verification"
          >
            {t.voiceNextBtn}
          </KioskButton>
        </KioskCard>
      )}

      {/* STEP 3: Voice Confirmation (TTS read-back + ASR/touch confirm) */}
      {step === 3 && (
        <KioskCard padding="36px">
          <h2 style={{ fontSize: '26px', fontWeight: 800, color: '#0F172A', marginBottom: '8px' }}>
            {t.step3Title}
          </h2>

          <div
            style={{
              background: '#F8FAFC',
              borderRadius: '16px',
              padding: '24px',
              marginBottom: '24px',
              border: '2px solid #E2E8F0',
            }}
          >
            <p
              style={{
                fontSize: '20px',
                lineHeight: 1.5,
                color: '#0F172A',
                fontWeight: 600,
                margin: 0,
              }}
            >
              "{t.summaryTemplate(consents.share_doctor, consents.store_abdm)}"
            </p>

            <div style={{ marginTop: '16px', display: 'flex', gap: '12px' }}>
              <button
                onClick={playTtsSummary}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '10px 18px',
                  borderRadius: '10px',
                  background: '#FFFFFF',
                  border: '2px solid #CBD5E1',
                  color: '#0F172A',
                  fontSize: '15px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  boxShadow: '0 1px 3px rgba(15, 23, 42, 0.05)',
                }}
              >
                <Volume2 size={18} color="#0284C7" />
                <span>{t.speakPromptBtn}</span>
              </button>
            </div>
          </div>

          {/* Voice status banner */}
          <div
            style={{
              padding: '18px 22px',
              borderRadius: '14px',
              background: voiceEvidence ? '#ECFDF5' : '#F0F9FF',
              border: `2px solid ${voiceEvidence ? '#059669' : '#0284C7'}`,
              marginBottom: '28px',
              display: 'flex',
              alignItems: 'center',
              gap: '14px',
            }}
          >
            <div
              style={{
                width: '42px',
                height: '42px',
                borderRadius: '50%',
                background: voiceEvidence ? '#059669' : '#0284C7',
                color: '#FFFFFF',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              {voiceEvidence ? <CheckCircle2 size={24} /> : <Mic size={22} />}
            </div>

            <span
              style={{
                fontSize: '16px',
                fontWeight: 700,
                color: voiceEvidence ? '#065F46' : '#0369A1',
              }}
            >
              {voiceEvidence || (isListening ? t.listeningText : 'कृपया "हाँ" बोलें अथवा नीचे दिए बटन से पुष्टि करें')}
            </span>
          </div>

          <KioskButton
            variant="primary"
            size="xl"
            fullWidth
            loading={isLoading}
            icon={<CheckCircle2 size={28} />}
            onClick={handleFinalSubmit}
            sublabel="Start your medical intake"
          >
            {t.confirmBtn}
          </KioskButton>
        </KioskCard>
      )}
    </div>
  );
};

export default ConsentFlow;
