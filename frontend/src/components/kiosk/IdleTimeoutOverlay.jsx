import React from 'react';
import KioskCard from './KioskCard';
import KioskButton from './KioskButton';
import { Clock, CheckCircle, LogOut } from 'lucide-react';

const OVERLAY_TEXT = {
  en: {
    title: 'Are you still here?',
    desc: 'To protect your privacy in the queue, this screen will reset automatically in:',
    resetBtn: 'End Session Now',
    resetSub: 'Reset screen',
    extendBtn: 'Yes, Keep Active',
    extendSub: 'Continue my session',
  },
  hi: {
    title: 'क्या आप अभी भी यहाँ हैं?',
    desc: 'आपकी गोपनीयता की सुरक्षा हेतु यह कियोस्क स्क्रीन स्वतः बंद हो जाएगी:',
    resetBtn: 'सत्र समाप्त करें',
    resetSub: 'Reset screen',
    extendBtn: 'हाँ, जारी रखें',
    extendSub: 'Keep session active',
  },
  pa: {
    title: 'ਕੀ ਤੁਸੀਂ ਅਜੇ ਵੀ ਇੱਥੇ ਹੋ?',
    desc: 'ਤੁਹਾਡੀ ਨਿੱਜਤਾ ਦੀ ਸੁਰੱਖਿਆ ਲਈ ਇਹ ਸਕ੍ਰੀਨ ਆਪਣੇ ਆਪ ਬੰਦ ਹੋ ਜਾਵੇਗੀ:',
    resetBtn: 'ਸੈਸ਼ਨ ਸਮਾਪਤ ਕਰੋ',
    resetSub: 'ਸਕ੍ਰੀਨ ਰੀਸੈੱਟ ਕਰੋ',
    extendBtn: 'ਹਾਂ, ਜਾਰੀ ਰੱਖੋ',
    extendSub: 'ਸੈਸ਼ਨ ਚਾਲੂ ਰੱਖੋ',
  },
};

/**
 * IdleTimeoutOverlay — High-contrast screen overlay warning patient 30s before automatic privacy wipe.
 */
export const IdleTimeoutOverlay = ({
  isOpen = false,
  secondsRemaining = 30,
  language = 'hi',
  onExtend,
  onResetNow,
}) => {
  if (!isOpen) return null;

  const t = OVERLAY_TEXT[language] || OVERLAY_TEXT.hi;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(15, 23, 42, 0.65)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 2000,
        padding: '20px',
      }}
    >
      <KioskCard
        padding="40px"
        highlight={secondsRemaining <= 10 ? 'red' : 'amber'}
        style={{
          width: '100%',
          maxWidth: '560px',
          textAlign: 'center',
          background: '#FFFFFF',
          borderWidth: '3px',
          boxShadow: '0 20px 40px -8px rgba(15, 23, 42, 0.25)',
        }}
      >
        <div
          style={{
            width: '84px',
            height: '84px',
            borderRadius: '50%',
            background: secondsRemaining <= 10 ? '#FEE2E2' : '#FEF3C7',
            border: `3px solid ${secondsRemaining <= 10 ? '#DC2626' : '#D97706'}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 20px',
            color: secondsRemaining <= 10 ? '#DC2626' : '#D97706',
          }}
        >
          <Clock size={44} strokeWidth={2.5} />
        </div>

        <h2 style={{ fontSize: '28px', fontWeight: 800, color: '#0F172A', marginBottom: '8px' }}>
          {t.title}
        </h2>
        <p style={{ fontSize: '17px', color: '#475569', marginBottom: '24px', lineHeight: 1.4 }}>
          {t.desc}
        </p>

        <div
          style={{
            fontSize: '56px',
            fontWeight: 900,
            color: secondsRemaining <= 10 ? '#DC2626' : '#D97706',
            marginBottom: '32px',
            fontFamily: 'monospace',
            letterSpacing: '2px',
          }}
        >
          00:{String(secondsRemaining).padStart(2, '0')}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.3fr', gap: '16px' }}>
          <KioskButton
            variant="danger"
            size="lg"
            icon={<LogOut size={22} />}
            onClick={onResetNow}
            sublabel={t.resetSub}
          >
            {t.resetBtn}
          </KioskButton>

          <KioskButton
            variant="primary"
            size="lg"
            icon={<CheckCircle size={24} />}
            onClick={onExtend}
            sublabel={t.extendSub}
          >
            {t.extendBtn}
          </KioskButton>
        </div>
      </KioskCard>
    </div>
  );
};

export default IdleTimeoutOverlay;
