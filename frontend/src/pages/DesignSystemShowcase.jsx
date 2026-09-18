import React, { useState } from 'react';
import KioskButton from '../components/kiosk/KioskButton';
import KioskCard from '../components/kiosk/KioskCard';
import LanguageSelector from '../components/kiosk/LanguageSelector';
import ConsentModal from '../components/kiosk/ConsentModal';
import ProgressBar from '../components/kiosk/ProgressBar';
import IdleTimeoutOverlay from '../components/kiosk/IdleTimeoutOverlay';
import VerificationBadge from '../components/doctor/VerificationBadge';
import useIdleTimeout from '../hooks/useIdleTimeout';

export const DesignSystemShowcase = ({ onBack }) => {
  const [selectedLang, setSelectedLang] = useState('hi');
  const [isConsentOpen, setIsConsentOpen] = useState(false);
  const [progressVal, setProgressVal] = useState(45);
  const [selectedCard, setSelectedCard] = useState('card1');
  const [btnLoading, setBtnLoading] = useState(false);
  const [fullscreenActive, setFullscreenActive] = useState(false);

  // Idle timeout hook test (30s overall timeout with 10s warning for quick demonstration)
  const { isWarningActive, secondsRemaining, extendSession } = useIdleTimeout({
    timeoutMs: 40000,
    warningMs: 15000,
    onTimeout: () => {
      alert('⚠️ Idle timeout expired! Session reset to Language Selection.');
      setSelectedLang('hi');
    },
  });

  const handleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().then(() => {
        setFullscreenActive(true);
      }).catch((err) => {
        console.warn('Fullscreen request denied:', err);
      });
    } else {
      document.exitFullscreen().then(() => {
        setFullscreenActive(false);
      });
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--color-surface-primary)',
      padding: '40px 24px',
      color: 'var(--color-text-primary)',
    }}>
      {/* Header Banner */}
      <div style={{
        maxWidth: '1200px',
        margin: '0 auto 40px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '20px',
        borderBottom: '1px solid var(--color-border-subtle)',
        paddingBottom: '24px',
      }}>
        <div>
          <div style={{
            display: 'inline-block',
            padding: '4px 12px',
            borderRadius: '9999px',
            background: 'rgba(59, 130, 246, 0.15)',
            border: '1px solid var(--color-blue-info)',
            color: 'var(--color-blue-info)',
            fontSize: '13px',
            fontWeight: 700,
            marginBottom: '8px',
          }}>
            PS ID26047 · MEDIKIOSK FOUNDATION LAYER (DEV 2)
          </div>
          <h1 style={{ fontSize: '32px', fontWeight: 800, letterSpacing: '-0.02em' }}>
            Design System & Kiosk Component Showcase
          </h1>
          <p style={{ color: 'var(--color-text-secondary)', marginTop: '4px', fontSize: '16px' }}>
            Interactive validation of public hospital OPD touch ergonomics, high-contrast themes & state tokens
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          {onBack && (
            <KioskButton
              variant="secondary"
              size="md"
              onClick={onBack}
            >
              ← Back to Live Kiosk Flow
            </KioskButton>
          )}
          <KioskButton
            variant={fullscreenActive ? 'secondary' : 'primary'}
            size="md"
            onClick={handleFullscreen}
          >
            {fullscreenActive ? '⤢ Fullscreen On' : '⤢ Enter Fullscreen PWA'}
          </KioskButton>
          <KioskButton
            variant="secondary"
            size="md"
            onClick={() => setIsConsentOpen(true)}
          >
            📋 Open Consent Modal
          </KioskButton>
        </div>
      </div>

      <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '48px' }}>

        {/* Section 1: Kiosk Buttons */}
        <section>
          <h2 style={{ fontSize: '22px', fontWeight: 700, marginBottom: '16px', color: 'var(--color-text-primary)' }}>
            1. Kiosk Buttons (Touch Target min 48px, Tactile Ripple & States)
          </h2>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', alignItems: 'center' }}>
            <KioskButton variant="primary" size="lg">
              Primary Action (बड़ा बटन)
            </KioskButton>

            <KioskButton variant="secondary" size="md">
              Secondary Option
            </KioskButton>

            <KioskButton variant="danger" size="md">
              🚨 Emergency Stop (रेड-फ्लैग)
            </KioskButton>

            <KioskButton variant="ghost" size="md">
              Ghost / Cancel
            </KioskButton>

            <KioskButton
              variant="primary"
              size="md"
              loading={btnLoading}
              onClick={() => {
                setBtnLoading(true);
                setTimeout(() => setBtnLoading(false), 2000);
              }}
            >
              Test Loading State
            </KioskButton>

            <KioskButton variant="primary" size="md" disabled>
              Disabled Button
            </KioskButton>
          </div>
        </section>

        {/* Section 2: Verification Badges */}
        <section>
          <h2 style={{ fontSize: '22px', fontWeight: 700, marginBottom: '16px', color: 'var(--color-text-primary)' }}>
            2. Summary Verification Badges (Clinical Trust & Provenance)
          </h2>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', alignItems: 'center', marginBottom: '16px' }}>
            <VerificationBadge status="patient_reported" />
            <VerificationBadge status="document_extracted" />
            <VerificationBadge status="needs_confirmation" />
            <VerificationBadge status="conflicting" />
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'center' }}>
            <span style={{ fontSize: '14px', color: 'var(--color-text-muted)' }}>Compact variants:</span>
            <VerificationBadge status="patient_reported" compact />
            <VerificationBadge status="document_extracted" compact />
            <VerificationBadge status="needs_confirmation" compact />
            <VerificationBadge status="conflicting" compact />
          </div>
        </section>

        {/* Section 3: Progress Indicators */}
        <section>
          <h2 style={{ fontSize: '22px', fontWeight: 700, marginBottom: '16px', color: 'var(--color-text-primary)' }}>
            3. Kiosk Progress Bar
          </h2>
          <div style={{
            background: 'var(--color-surface-secondary)',
            padding: '24px',
            borderRadius: 'var(--border-radius-card)',
            display: 'flex',
            flexDirection: 'column',
            gap: '20px',
          }}>
            <ProgressBar
              progress={progressVal}
              label="दस्तावेज़ स्कैनिंग एवं विश्लेषण (OCR Document Processing)"
              color="gradient"
              height="16px"
            />
            <div style={{ display: 'flex', gap: '12px' }}>
              <KioskButton size="sm" variant="secondary" onClick={() => setProgressVal(Math.max(0, progressVal - 15))}>
                -15% Step
              </KioskButton>
              <KioskButton size="sm" variant="secondary" onClick={() => setProgressVal(Math.min(100, progressVal + 15))}>
                +15% Step
              </KioskButton>
            </div>
          </div>
        </section>

        {/* Section 4: Kiosk Elevated Cards */}
        <section>
          <h2 style={{ fontSize: '22px', fontWeight: 700, marginBottom: '16px', color: 'var(--color-text-primary)' }}>
            4. Kiosk Cards (Elevated Surfaces, Active Borders & Highlights)
          </h2>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
            gap: '20px',
          }}>
            <KioskCard
              selected={selectedCard === 'card1'}
              onClick={() => setSelectedCard('card1')}
            >
              <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '6px' }}>Selectable Card 1</h3>
              <p style={{ color: 'var(--color-text-secondary)', fontSize: '15px' }}>
                Tap to select. Displays blue glow and focused border.
              </p>
            </KioskCard>

            <KioskCard
              selected={selectedCard === 'card2'}
              onClick={() => setSelectedCard('card2')}
            >
              <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '6px' }}>Selectable Card 2</h3>
              <p style={{ color: 'var(--color-text-secondary)', fontSize: '15px' }}>
                Tactile micro-animation on press.
              </p>
            </KioskCard>

            <KioskCard highlight="green">
              <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--color-green-safe)', marginBottom: '6px' }}>
                Safe / Completed
              </h3>
              <p style={{ color: 'var(--color-text-secondary)', fontSize: '15px' }}>
                Green highlight token for verified records.
              </p>
            </KioskCard>

            <KioskCard highlight="red">
              <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--color-red-flag)', marginBottom: '6px' }}>
                Emergency Alert
              </h3>
              <p style={{ color: 'var(--color-text-secondary)', fontSize: '15px' }}>
                Red glow highlight token for acute danger signs.
              </p>
            </KioskCard>
          </div>
        </section>

        {/* Section 5: Language Selector Grid */}
        <section>
          <h2 style={{ fontSize: '22px', fontWeight: 700, marginBottom: '16px', color: 'var(--color-text-primary)' }}>
            5. Language Selector Grid (9 Indic Languages)
          </h2>
          <div style={{
            background: 'var(--color-surface-secondary)',
            borderRadius: 'var(--border-radius-card)',
            border: '1px solid var(--color-border-subtle)',
          }}>
            <LanguageSelector
              selectedLanguage={selectedLang}
              onSelectLanguage={(code) => setSelectedLang(code)}
            />
          </div>
        </section>

      </div>

      {/* Modals & Overlays */}
      <ConsentModal
        isOpen={isConsentOpen}
        onAccept={(consents) => {
          setIsConsentOpen(false);
          alert(`✅ Consent accepted: ${JSON.stringify(consents)}`);
        }}
        onDecline={() => setIsConsentOpen(false)}
      />

      <IdleTimeoutOverlay
        isOpen={isWarningActive}
        secondsRemaining={secondsRemaining}
        onExtend={extendSession}
        onResetNow={() => {
          extendSession();
          setSelectedLang('hi');
        }}
      />
    </div>
  );
};

export default DesignSystemShowcase;
