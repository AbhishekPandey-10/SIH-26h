import React, { useState, useEffect } from 'react';
import KioskCard from './KioskCard';
import KioskButton from './KioskButton';
import { Volume2, CheckCircle2, ArrowRight, Languages, Globe, Mic, Sparkles } from 'lucide-react';
import { useSession } from '../../contexts/SessionContext';

/**
 * Pan-India OPD Language Set
 * Includes 13 major Indian languages + 1 "More Languages" staff assistance tile.
 */
export const LANGUAGES = [
  {
    code: 'hi',
    native: 'हिन्दी',
    english: 'Hindi',
    script: 'नमस्ते',
    subtext: 'उत्तर एवं मध्य भारत',
    iconColor: '#059669',
  },
  {
    code: 'en',
    native: 'English',
    english: 'English',
    script: 'Welcome',
    subtext: 'Pan-India / General',
    iconColor: '#0284C7',
  },
  {
    code: 'pa',
    native: 'ਪੰਜਾਬੀ',
    english: 'Punjabi',
    script: 'ਸਤਿ ਸ਼੍ਰੀ ਅਕਾਲ',
    subtext: 'ਪੰਜਾਬ & ਉੱਤਰੀ ਭਾਰਤ',
    iconColor: '#D97706',
  },
  {
    code: 'or',
    native: 'ଓଡ଼ିଆ',
    english: 'Odia',
    script: 'ନମସ୍କାର',
    subtext: 'ଓଡ଼ିଶਾ (Eastern India)',
    iconColor: '#059669',
  },
  {
    code: 'as',
    native: 'অসমীয়া',
    english: 'Assamese',
    script: 'নমস্কাৰ',
    subtext: 'অসম (North East)',
    iconColor: '#0284C7',
  },
  {
    code: 'ur',
    native: 'اردو',
    english: 'Urdu',
    script: 'آداب',
    subtext: 'پین انڈیا (Pan-India)',
    iconColor: '#059669',
  },
  {
    code: 'ta',
    native: 'தமிழ்',
    english: 'Tamil',
    script: 'வணக்கம்',
    subtext: 'தமிழ்நாடு & புதுச்சேரி',
    iconColor: '#D97706',
  },
  {
    code: 'te',
    native: 'తెలుగు',
    english: 'Telugu',
    script: 'నమస్కారం',
    subtext: 'ఆంధ్రప్రదేశ్ & తెలంగాణ',
    iconColor: '#0284C7',
  },
  {
    code: 'bn',
    native: 'বাংলা',
    english: 'Bengali',
    script: 'নমস্কার',
    subtext: 'পশ্চিমবঙ্গ & ত্রিপুরা',
    iconColor: '#059669',
  },
  {
    code: 'mr',
    native: 'मराठी',
    english: 'Marathi',
    script: 'नमस्कार',
    subtext: 'महाराष्ट्र & गोवा',
    iconColor: '#D97706',
  },
  {
    code: 'kn',
    native: 'ಕನ್ನಡ',
    english: 'Kannada',
    script: 'ನಮಸ್ಕಾರ',
    subtext: 'ಕರ್ನಾಟಕ (South India)',
    iconColor: '#059669',
  },
  {
    code: 'ml',
    native: 'മലയാളം',
    english: 'Malayalam',
    script: 'നਮਸ੍ਕਾਰം',
    subtext: 'കേരളം & ലക്ഷദ്വീപ്',
    iconColor: '#0284C7',
  },
  {
    code: 'gu',
    native: 'ગુજરાતી',
    english: 'Gujarati',
    script: 'નમસ્તે',
    subtext: 'ગુજરાત (Western India)',
    iconColor: '#D97706',
  },
  {
    code: 'more',
    native: '🌐 और भाषाएँ',
    english: 'More Languages',
    script: 'All 22 Languages',
    subtext: 'सहायता डेस्क (Help Desk)',
    iconColor: '#64748B',
    isSpecial: true,
  },
];

const UI_TEXT = {
  en: {
    stepBadge: 'Step 1 / 3 · Language Selection',
    title: 'Choose Your Language / अपनी भाषा चुनें',
    subtitle: 'Touch your preferred language card on the screen to proceed.',
    hearBtn: 'Hear Instructions in English',
    speaking: 'Speaking instructions...',
    continueBtn: 'Continue in English (आगे बढ़ें) →',
    continueSub: 'Proceed to patient identity verification',
    selectedBadge: 'Selected',
    moreModalTitle: 'All 22 Scheduled Indian Languages',
    moreModalDesc: 'Assistance for all 22 official languages and regional dialects is available at the OPD Help Desk. Bhashini AI voice translation is also available in the consultation room.',
    moreModalClose: 'Understood / Back to Language Grid',
  },
  hi: {
    stepBadge: 'कदम 1 / 3 · भाषा चयन (Language Selection)',
    title: 'अपनी भाषा चुनें / Choose Your Language',
    subtitle: 'डॉक्टर से बात करने से पहले स्क्रीन पर अपनी पसंदीदा भाषा का कार्ड छुएं।',
    hearBtn: 'बोलकर निर्देश सुनें (Hear Instructions)',
    speaking: 'बोल रहे हैं... (Speaking)',
    continueBtn: 'हिन्दी में आगे बढ़ें (Continue) →',
    continueSub: 'मरीज पहचान सत्यापन हेतु आगे बढ़ें',
    selectedBadge: 'चयनित',
    moreModalTitle: 'अन्य भारतीय भाषाएँ एवं बोलियाँ',
    moreModalDesc: 'संविधान की 8वीं अनुसूची की अन्य सभी भाषाओं (मैथिली, कश्मीरी, नेपाली, संथाली, सिंधी आदि) तथा स्थानीय बोलियों में सहायता हेतु ओपीडी हेल्पडेस्क से संपर्क करें।',
    moreModalClose: 'समझ गया / Back to Language Grid',
  },
  pa: {
    stepBadge: 'ਕਦਮ 1 / 3 · ਭਾਸ਼ਾ ਚੋਣ (Language Selection)',
    title: 'ਆਪਣੀ ਭਾਸ਼ਾ ਚੁਣੋ / Choose Your Language',
    subtitle: 'ਡਾਕਟਰ ਨਾਲ ਗੱਲ ਕਰਨ ਤੋਂ ਪਹਿਲਾਂ ਸਕ੍ਰੀਨ ਤੇ ਆਪਣੀ ਪਸੰਦੀਦਾ ਭਾਸ਼ਾ ਦਾ ਕਾਰਡ ਛੂਹੋ।',
    hearBtn: 'ਬੋਲ ਕੇ ਹਦਾਇਤਾਂ ਸੁਣੋ (Hear Instructions)',
    speaking: 'ਬੋਲ ਰਹੇ ਹਾਂ... (Speaking)',
    continueBtn: 'ਪੰਜਾਬੀ ਵਿੱਚ ਅੱਗੇ ਵਧੋ (Continue) →',
    continueSub: 'ਮਰੀਜ਼ ਦੀ ਪਛਾਣ ਲਈ ਅੱਗੇ ਵਧੋ',
    selectedBadge: 'ਚੁਣਿਆ ਗਿਆ',
    moreModalTitle: 'ਹੋਰ ਭਾਰਤੀ ਭਾਸ਼ਾਵਾਂ ਅਤੇ ਬੋਲੀਆਂ',
    moreModalDesc: 'ਹੋਰ ਸਾਰੀਆਂ ਭਾਸ਼ਾਵਾਂ ਅਤੇ ਸਥਾਨਕ ਬੋਲੀਆਂ ਵਿੱਚ ਸਹਾਇਤਾ ਲਈ ਓਪੀਡੀ ਹੈਲਪ ਡੈਸਕ ਨਾਲ ਸੰਪਰਕ ਕਰੋ।',
    moreModalClose: 'ਸਮਝ ਗਿਆ / Back to Language Grid',
  },
};

export const LanguageSelector = ({
  selectedLanguage = 'hi',
  onSelectLanguage,
  className = '',
}) => {
  const { voiceOnlyMode, setVoiceOnlyMode, language } = useSession();
  const [currentLang, setCurrentLang] = useState(selectedLanguage || 'hi');
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [showMoreModal, setShowMoreModal] = useState(false);
  const [showIdleSuggestion, setShowIdleSuggestion] = useState(false);

  // 15-Second Inactivity Auto-Detection for Voice-Only Mode suggestion
  useEffect(() => {
    const timer = setTimeout(() => {
      setShowIdleSuggestion(true);
    }, 15000);

    const cancelTimer = () => {
      clearTimeout(timer);
      setShowIdleSuggestion(false);
    };

    window.addEventListener('pointerdown', cancelTimer, { once: true });
    window.addEventListener('keydown', cancelTimer, { once: true });

    return () => {
      clearTimeout(timer);
      window.removeEventListener('pointerdown', cancelTimer);
      window.removeEventListener('keydown', cancelTimer);
    };
  }, []);

  const t = UI_TEXT[currentLang] || UI_TEXT.hi;

  const handleChoose = (code) => {
    if (code === 'more') {
      setShowMoreModal(true);
      return;
    }
    // Update local state and immediately advance to identity verification
    setCurrentLang(code);
    if (onSelectLanguage) {
      onSelectLanguage(code);
    }
  };

  const handleProceed = (langCode) => {
    const target = langCode || currentLang;
    if (onSelectLanguage) {
      onSelectLanguage(target);
    }
  };

  const playVoiceInstruction = () => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      setIsPlayingAudio(true);
      let text = 'Please choose your preferred language and press continue';
      let langCode = 'en-IN';
      if (currentLang === 'hi') {
        text = 'कृपया अपनी पसंदीदा भाषा चुनें और आगे बढ़ें';
        langCode = 'hi-IN';
      } else if (currentLang === 'pa') {
        text = 'ਕਿਰਪਾ ਕਰਕੇ ਆਪਣੀ ਪਸੰਦੀਦਾ ਭਾਸ਼ਾ ਚੁਣੋ ਅਤੇ ਅੱਗੇ ਵਧੋ';
        langCode = 'pa-IN';
      }
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = langCode;
      utterance.rate = 0.9;
      utterance.onend = () => setIsPlayingAudio(false);
      utterance.onerror = () => setIsPlayingAudio(false);
      window.speechSynthesis.speak(utterance);
    }
  };

  return (
    <div
      style={{
        width: '100%',
        maxWidth: '1160px',
        margin: '0 auto',
        padding: '28px 20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '28px',
      }}
      className={className}
    >
      {/* Header with Title & Audio Guidance Button */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
          gap: '12px',
        }}
      >
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 14px',
            background: '#ECFDF5',
            border: '1.5px solid #A7F3D0',
            borderRadius: '999px',
            color: '#065F46',
            fontSize: '14px',
            fontWeight: 800,
          }}
        >
          <Languages size={18} />
          <span>{t.stepBadge}</span>
        </div>

        <h1
          style={{
            fontSize: '34px',
            fontWeight: 800,
            color: '#0F172A',
            letterSpacing: '-0.02em',
            margin: 0,
          }}
        >
          {t.title}
        </h1>

        <p style={{ fontSize: '18px', color: '#334155', maxWidth: '680px', margin: 0, fontWeight: 600 }}>
          {t.subtitle}
        </p>

        {/* Audio instruction button with single clean speaker icon */}
        <button
          type="button"
          onClick={playVoiceInstruction}
          style={{
            marginTop: '6px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '10px',
            padding: '12px 24px',
            borderRadius: '12px',
            background: isPlayingAudio ? '#DCFCE7' : '#FFFFFF',
            border: `2px solid ${isPlayingAudio ? '#059669' : '#CBD5E1'}`,
            color: isPlayingAudio ? '#065F46' : '#0F172A',
            fontSize: '17px',
            fontWeight: 700,
            cursor: 'pointer',
            boxShadow: '0 2px 6px rgba(15, 23, 42, 0.05)',
            minHeight: '52px',
          }}
        >
          <Volume2 size={22} color={isPlayingAudio ? '#059669' : '#0284C7'} />
          <span>{isPlayingAudio ? t.speaking : t.hearBtn}</span>
        </button>
      </div>

      {/* TASK 1: Voice-Only Mode Large Toggle Button */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px', width: '100%', maxWidth: '720px', margin: '0 auto' }}>
        <button
          type="button"
          onClick={() => {
            setVoiceOnlyMode(true);
            handleProceed(currentLang);
          }}
          style={{
            width: '100%',
            padding: '16px 24px',
            borderRadius: '16px',
            background: 'linear-gradient(135deg, #1E1B4B 0%, #312E81 100%)',
            border: '2.5px solid #818CF8',
            color: '#FFFFFF',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '16px',
            cursor: 'pointer',
            boxShadow: '0 8px 24px rgba(49, 46, 129, 0.25)',
            transition: 'transform 0.15s ease',
          }}
        >
          <div style={{ background: '#4F46E5', borderRadius: '50%', padding: '10px', display: 'flex' }}>
            <Mic size={26} color="#FFFFFF" />
          </div>
          <div style={{ textAlign: 'left' }}>
            <div style={{ fontSize: '18px', fontWeight: 800 }}>
              {language === 'en' ? 'Voice-Only Mode (No touch needed)' : 'बोलकर चलाएं (Voice-Only Mode · स्पर्श की जरूरत नहीं)'}
            </div>
            <div style={{ fontSize: '13px', color: '#C7D2FE', marginTop: '2px' }}>
              {language === 'en' ? 'Hands-free clinical intake via voice commands & audio prompts' : 'बिना स्क्रीन छुए पूरी प्रक्रिया बोलकर पूरी करें'}
            </div>
          </div>
        </button>

        {/* 15-second Inactivity Auto-Detection Suggestion Banner */}
        {showIdleSuggestion && (
          <div
            style={{
              width: '100%',
              padding: '12px 18px',
              borderRadius: '12px',
              background: '#FEF3C7',
              border: '1.5px solid #F59E0B',
              color: '#92400E',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '12px',
            }}
          >
            <div style={{ fontSize: '13px', fontWeight: 700 }}>
              💡 15 सेकंड से कोई स्पर्श नहीं: क्या आप केवल आवाज़ से संचालन (Voice-Only Mode) चाहते हैं?
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                type="button"
                onClick={() => {
                  setVoiceOnlyMode(true);
                  handleProceed(currentLang);
                }}
                style={{
                  padding: '6px 14px',
                  borderRadius: '8px',
                  background: '#D97706',
                  color: '#FFFFFF',
                  border: 'none',
                  fontWeight: 800,
                  fontSize: '12px',
                  cursor: 'pointer',
                }}
              >
                हाँ, चालू करें
              </button>
              <button
                type="button"
                onClick={() => setShowIdleSuggestion(false)}
                style={{
                  padding: '6px 14px',
                  borderRadius: '8px',
                  background: '#FDE68A',
                  color: '#78350F',
                  border: 'none',
                  fontWeight: 700,
                  fontSize: '12px',
                  cursor: 'pointer',
                }}
              >
                खारिज करें
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Grid of Languages with Fixed Uniform Height (142px) */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: '18px',
        }}
      >
        {LANGUAGES.map((lang) => {
          const isSelected = currentLang === lang.code;
          return (
            <div
              key={lang.code}
              role="button"
              tabIndex={0}
              aria-label={`Select ${lang.english} / ${lang.native}`}
              onClick={() => {
                handleChoose(lang.code);
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  handleChoose(lang.code);
                }
              }}
              style={{
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                minHeight: '142px',
                padding: '20px 22px',
                borderRadius: '16px',
                background: isSelected ? '#ECFDF5' : '#FFFFFF',
                border: `3.5px solid ${isSelected ? '#059669' : '#E2E8F0'}`,
                boxShadow: isSelected
                  ? '0 0 0 2px rgba(5, 150, 105, 0.3), 0 8px 20px rgba(15, 23, 42, 0.08)'
                  : '0 2px 6px rgba(15, 23, 42, 0.04)',
                cursor: 'pointer',
                position: 'relative',
                transition: 'all 0.15s ease',
              }}
              className="kiosk-card interactive"
            >
              {/* Top Row: Native Script + Persistent Selection Badge Slot */}
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                <div>
                  <div
                    style={{
                      fontSize: '27px',
                      fontWeight: 800,
                      color: isSelected ? '#065F46' : '#0F172A',
                      lineHeight: 1.15,
                    }}
                  >
                    {lang.native}
                  </div>
                  <div
                    style={{
                      fontSize: '17px',
                      fontWeight: 700,
                      color: isSelected ? '#047857' : '#1E293B',
                      marginTop: '2px',
                    }}
                  >
                    {lang.english}
                  </div>
                </div>

                {/* Persistent Selection Indicator Slot (No layout shift) */}
                <div
                  style={{
                    minHeight: '26px',
                    display: 'flex',
                    alignItems: 'center',
                  }}
                >
                  {isSelected ? (
                    <span
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        padding: '4px 8px',
                        borderRadius: '6px',
                        background: '#059669',
                        color: '#FFFFFF',
                        fontSize: '12px',
                        fontWeight: 800,
                        textTransform: 'uppercase',
                        letterSpacing: '0.02em',
                      }}
                    >
                      <CheckCircle2 size={14} />
                      <span>{t.selectedBadge}</span>
                    </span>
                  ) : (
                    <span
                      style={{
                        display: 'inline-block',
                        width: '18px',
                        height: '18px',
                        borderRadius: '50%',
                        border: '2px solid #CBD5E1',
                      }}
                    />
                  )}
                </div>
              </div>

              {/* Bottom Row: Non-Button Greeting Plain Text + Darkened Region Label */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'flex-end',
                  justifyContent: 'space-between',
                  marginTop: '12px',
                  borderTop: '1px solid #E2E8F0',
                  paddingTop: '8px',
                }}
              >
                {/* Secondary Region Label (Darkened for Presbyopia) */}
                <span
                  style={{
                    fontSize: '15px',
                    color: '#1E293B',
                    fontWeight: 600,
                    maxWidth: '160px',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {lang.subtext}
                </span>

                {/* Greeting rendered as plain text script caption (NOT a button chip) */}
                <span
                  style={{
                    fontSize: '15px',
                    color: isSelected ? '#047857' : '#475569',
                    fontWeight: 700,
                    fontStyle: 'italic',
                  }}
                >
                  {lang.script}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Primary Proceed Action Bar (Standardized Unified Emerald Green #059669) */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          marginTop: '8px',
        }}
      >
        <KioskButton
          variant="primary"
          size="xl"
          icon={<ArrowRight size={28} />}
          iconPosition="right"
          onClick={() => handleProceed(currentLang)}
          sublabel={t.continueSub}
          style={{ minWidth: '420px' }}
        >
          {t.continueBtn}
        </KioskButton>
      </div>

      {/* "More Languages" Staff Modal */}
      {showMoreModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(15, 23, 42, 0.65)',
            backdropFilter: 'blur(6px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '20px',
          }}
        >
          <KioskCard
            padding="36px"
            style={{
              maxWidth: '540px',
              width: '100%',
              background: '#FFFFFF',
              border: '3px solid #0284C7',
              textAlign: 'center',
            }}
          >
            <div
              style={{
                width: '64px',
                height: '64px',
                borderRadius: '50%',
                background: '#F0F9FF',
                color: '#0284C7',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 16px',
              }}
            >
              <Globe size={36} />
            </div>

            <h3 style={{ fontSize: '24px', fontWeight: 800, color: '#0F172A', marginBottom: '8px' }}>
              {t.moreModalTitle}
            </h3>
            <p style={{ fontSize: '16px', color: '#334155', lineHeight: 1.5, marginBottom: '24px' }}>
              {t.moreModalDesc}
            </p>

            <KioskButton
              variant="primary"
              size="lg"
              fullWidth
              onClick={() => setShowMoreModal(false)}
            >
              {t.moreModalClose}
            </KioskButton>
          </KioskCard>
        </div>
      )}
    </div>
  );
};

export default LanguageSelector;
