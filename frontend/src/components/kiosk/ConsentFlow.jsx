import React, { useState, useEffect, useRef } from 'react';
import KioskCard from './KioskCard';
import KioskButton from './KioskButton';
import { useSession } from '../../contexts/SessionContext';

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

    step2Title: 'सहमति विकल्प चुनें (Granular Permissions)',
    toggle1Title: 'इस परामर्श हेतु डॉक्टर के साथ मेरा इतिहास साझा करें',
    toggle1Sub: 'ओपीडी परामर्श हेतु आवश्यक (Mandatory for visit)',
    toggle2Title: 'भविष्य के परामर्श हेतु मेरे रिकॉर्ड ABDM में सुरक्षित करें',
    toggle2Sub: 'वैकल्पिक (Optional)',
    toggle3Title: 'चिकित्सा अनुसंधान हेतु अनाम डेटा का उपयोग करने दें',
    toggle3Sub: 'वैकल्पिक (Optional)',

    step3Title: 'आवाज द्वारा अंतिम पुष्टि (Voice Confirmation)',
    summaryTemplate: (t1, t2) =>
      `आपने डॉक्टर के साथ अपना इतिहास साझा करने की सहमति दी है। आपने ABDM में रिकॉर्ड ${t2 ? 'सुरक्षित करने का विकल्प चुना है' : 'सुरक्षित न करने का विकल्प चुना है'}। क्या आप पुष्टि करते हैं?`,
    speakPromptBtn: '🔊 पुनः सुनें (Listen Again)',
    listeningText: '🎙️ सुन रहे हैं... कृपया "हाँ" या "Yes" बोलें...',
    voiceCaptured: '✓ आवाज पुष्टि दर्ज: "हाँ, मैं सहमत हूँ"',
    confirmBtn: '✓ हाँ, मैं पुष्टि करता/करती हूँ (Confirm & Finish)',
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

    step2Title: 'Granular Consent Toggles',
    toggle1Title: 'Share my history with the doctor for this visit',
    toggle1Sub: 'Mandatory for OPD consultation',
    toggle2Title: 'Store my records in ABDM for future visits',
    toggle2Sub: 'Optional',
    toggle3Title: 'Allow anonymized data for clinical research',
    toggle3Sub: 'Optional',

    step3Title: 'Voice Confirmation & Final Audit',
    summaryTemplate: (t1, t2) =>
      `You have agreed to share your history with the doctor. You have chosen ${t2 ? 'to store' : 'not to store'} records in ABDM. Do you confirm?`,
    speakPromptBtn: '🔊 Play Summary Again',
    listeningText: '🎙️ Listening... Please say "Yes" or "Haan"...',
    voiceCaptured: '✓ Voice evidence captured: "Yes, I confirm"',
    confirmBtn: '✓ Confirm Consent & Enter Kiosk',
  },
};

export const ConsentFlow = ({ onBack }) => {
  const { language, submitConsent, isLoading, error, patient } = useSession();
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
    <div style={{
      width: '100%',
      maxWidth: '800px',
      margin: '0 auto',
      padding: '24px 20px',
      display: 'flex',
      flexDirection: 'column',
      gap: '24px',
    }}>
      {/* Step Indicator Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <button
          onClick={step > 1 ? () => setStep(step - 1) : onBack}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--color-text-secondary)',
            fontSize: '16px',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          ← वापस (Back)
        </button>
        <span style={{
          fontSize: '14px',
          fontWeight: 700,
          color: 'var(--color-blue-info)',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
        }}>
          सहमति पत्र (Step {step} of 3)
        </span>
      </div>

      {error && (
        <div style={{
          padding: '16px',
          background: 'rgba(220, 38, 38, 0.15)',
          border: '1px solid var(--color-red-flag)',
          borderRadius: '12px',
          color: '#FCA5A5',
          fontSize: '15px',
        }}>
          ⚠️ {error}
        </div>
      )}

      {/* STEP 1: Full-screen Plain Language Explanation */}
      {step === 1 && (
        <KioskCard padding="32px">
          <h2 style={{ fontSize: '26px', fontWeight: 800, marginBottom: '8px' }}>
            {t.step1Title}
          </h2>
          <p style={{ fontSize: '16px', color: 'var(--color-text-secondary)', marginBottom: '24px' }}>
            {t.step1Lead}
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', marginBottom: '32px' }}>
            <div style={{
              display: 'flex',
              gap: '16px',
              padding: '18px',
              background: 'var(--color-surface-primary)',
              borderRadius: '14px',
              border: '1px solid rgba(255,255,255,0.06)',
            }}>
              <div style={{ fontSize: '32px' }}>🎙️</div>
              <div>
                <h4 style={{ fontSize: '18px', fontWeight: 700 }}>{t.collectedTitle}</h4>
                <p style={{ fontSize: '15px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
                  {t.collectedDesc}
                </p>
              </div>
            </div>

            <div style={{
              display: 'flex',
              gap: '16px',
              padding: '18px',
              background: 'var(--color-surface-primary)',
              borderRadius: '14px',
              border: '1px solid rgba(255,255,255,0.06)',
            }}>
              <div style={{ fontSize: '32px' }}>👨‍⚕️</div>
              <div>
                <h4 style={{ fontSize: '18px', fontWeight: 700 }}>{t.whoSeesTitle}</h4>
                <p style={{ fontSize: '15px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
                  {t.whoSeesDesc}
                </p>
              </div>
            </div>

            <div style={{
              display: 'flex',
              gap: '16px',
              padding: '18px',
              background: 'var(--color-surface-primary)',
              borderRadius: '14px',
              border: '1px solid rgba(255,255,255,0.06)',
            }}>
              <div style={{ fontSize: '32px' }}>⏱️</div>
              <div>
                <h4 style={{ fontSize: '18px', fontWeight: 700 }}>{t.retentionTitle}</h4>
                <p style={{ fontSize: '15px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
                  {t.retentionDesc}
                </p>
              </div>
            </div>
          </div>

          <KioskButton
            variant="primary"
            size="large"
            style={{ width: '100%' }}
            onClick={() => setStep(2)}
          >
            {t.nextBtn}
          </KioskButton>
        </KioskCard>
      )}

      {/* STEP 2: Granular Consent Toggles */}
      {step === 2 && (
        <KioskCard padding="32px">
          <h2 style={{ fontSize: '26px', fontWeight: 800, marginBottom: '8px' }}>
            {t.step2Title}
          </h2>
          <p style={{ fontSize: '15px', color: 'var(--color-text-secondary)', marginBottom: '24px' }}>
            कृपया अपनी इच्छानुसार विकल्पों का चयन करें (Select your preferences):
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '32px' }}>
            {/* Toggle 1: Default ON (Mandatory) */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '18px',
                borderRadius: '14px',
                background: 'rgba(59, 130, 246, 0.12)',
                border: '2px solid var(--color-blue-info)',
                cursor: 'not-allowed',
              }}
            >
              <div>
                <strong style={{ fontSize: '17px', display: 'block' }}>{t.toggle1Title}</strong>
                <span style={{ fontSize: '13px', color: 'var(--color-blue-info)', fontWeight: 600 }}>
                  ✓ {t.toggle1Sub}
                </span>
              </div>
              <input
                type="checkbox"
                checked={consents.share_doctor}
                readOnly
                style={{ width: '24px', height: '24px', accentColor: 'var(--color-blue-info)' }}
              />
            </div>

            {/* Toggle 2: Default OFF */}
            <div
              onClick={() => handleToggle('store_abdm')}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '18px',
                borderRadius: '14px',
                background: consents.store_abdm ? 'rgba(59, 130, 246, 0.12)' : 'var(--color-surface-primary)',
                border: `2px solid ${consents.store_abdm ? 'var(--color-blue-info)' : 'rgba(255,255,255,0.1)'}`,
                cursor: 'pointer',
              }}
            >
              <div>
                <strong style={{ fontSize: '17px', display: 'block' }}>{t.toggle2Title}</strong>
                <span style={{ fontSize: '13px', color: 'var(--color-text-muted)' }}>{t.toggle2Sub}</span>
              </div>
              <input
                type="checkbox"
                checked={consents.store_abdm}
                onChange={() => {}}
                style={{ width: '24px', height: '24px', accentColor: 'var(--color-blue-info)' }}
              />
            </div>

            {/* Toggle 3: Default OFF */}
            <div
              onClick={() => handleToggle('anonymized_research')}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '18px',
                borderRadius: '14px',
                background: consents.anonymized_research ? 'rgba(59, 130, 246, 0.12)' : 'var(--color-surface-primary)',
                border: `2px solid ${consents.anonymized_research ? 'var(--color-blue-info)' : 'rgba(255,255,255,0.1)'}`,
                cursor: 'pointer',
              }}
            >
              <div>
                <strong style={{ fontSize: '17px', display: 'block' }}>{t.toggle3Title}</strong>
                <span style={{ fontSize: '13px', color: 'var(--color-text-muted)' }}>{t.toggle3Sub}</span>
              </div>
              <input
                type="checkbox"
                checked={consents.anonymized_research}
                onChange={() => {}}
                style={{ width: '24px', height: '24px', accentColor: 'var(--color-blue-info)' }}
              />
            </div>
          </div>

          <KioskButton
            variant="primary"
            size="large"
            style={{ width: '100%' }}
            onClick={() => setStep(3)}
          >
            आवाज पुष्टि हेतु आगे बढ़ें (Voice Confirmation) →
          </KioskButton>
        </KioskCard>
      )}

      {/* STEP 3: Voice Confirmation (TTS read-back + ASR/touch confirm) */}
      {step === 3 && (
        <KioskCard padding="32px">
          <h2 style={{ fontSize: '26px', fontWeight: 800, marginBottom: '8px' }}>
            {t.step3Title}
          </h2>

          <div style={{
            background: 'var(--color-surface-primary)',
            borderRadius: '16px',
            padding: '24px',
            marginBottom: '24px',
            border: '1px solid rgba(255,255,255,0.08)',
          }}>
            <p style={{ fontSize: '18px', lineHeight: 1.5, color: 'var(--color-text-primary)' }}>
              "{t.summaryTemplate(consents.share_doctor, consents.store_abdm)}"
            </p>
            <div style={{ marginTop: '16px', display: 'flex', gap: '12px' }}>
              <button
                onClick={playTtsSummary}
                style={{
                  padding: '8px 16px',
                  borderRadius: '8px',
                  background: 'rgba(255,255,255,0.08)',
                  border: '1px solid rgba(255,255,255,0.15)',
                  color: 'var(--color-text-primary)',
                  fontSize: '14px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                {t.speakPromptBtn}
              </button>
            </div>
          </div>

          {/* Voice status banner */}
          <div style={{
            padding: '16px',
            borderRadius: '12px',
            background: voiceEvidence ? 'rgba(16, 185, 129, 0.15)' : 'rgba(59, 130, 246, 0.15)',
            border: `1px solid ${voiceEvidence ? 'var(--color-green-safe)' : 'var(--color-blue-info)'}`,
            marginBottom: '24px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
          }}>
            <span style={{ fontSize: '20px' }}>{voiceEvidence ? '✅' : '🎙️'}</span>
            <span style={{ fontSize: '15px', fontWeight: 600, color: voiceEvidence ? '#6EE7B7' : 'var(--color-blue-info)' }}>
              {voiceEvidence || (isListening ? t.listeningText : 'कृपया "हाँ" बोलें अथवा नीचे दिए बटन से पुष्टि करें')}
            </span>
          </div>

          <KioskButton
            variant="primary"
            size="large"
            loading={isLoading}
            style={{
              width: '100%',
              background: 'var(--color-green-safe)',
              borderColor: 'var(--color-green-safe)',
            }}
            onClick={handleFinalSubmit}
          >
            {t.confirmBtn}
          </KioskButton>
        </KioskCard>
      )}
    </div>
  );
};

export default ConsentFlow;
