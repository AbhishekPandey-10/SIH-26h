import React, { useState } from 'react';
import KioskCard from './KioskCard';
import KioskButton from './KioskButton';

/**
 * ConsentModal — Multi-step clinical consent flow adhering to ABDM Guidelines.
 */
export const ConsentModal = ({
  isOpen = true,
  patientName = 'मरीज (Patient)',
  onAccept,
  onDecline,
}) => {
  const [step, setStep] = useState(1);
  const [consents, setConsents] = useState({
    abha_pull: true,
    voice_recording: true,
    doctor_share: true,
  });

  if (!isOpen) return null;

  const handleToggle = (key) => {
    setConsents((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleNext = () => {
    if (step < 3) {
      setStep(step + 1);
    } else {
      if (onAccept) onAccept(consents);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(15, 23, 42, 0.85)',
      backdropFilter: 'blur(12px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '20px',
    }}>
      <KioskCard
        padding="36px"
        style={{
          width: '100%',
          maxWidth: '680px',
          background: 'var(--color-surface-secondary)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
        }}
      >
        {/* Header */}
        <div style={{ marginBottom: '24px', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: '16px' }}>
          <div style={{
            fontSize: '14px',
            color: 'var(--color-blue-info)',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}>
            चरण {step} / 3 — {patientName} सहमति पत्र (Clinical Consent)
          </div>
          <h2 style={{ fontSize: '26px', fontWeight: 700, marginTop: '6px' }}>
            {step === 1 && '1. आभा स्वास्थ्य रिकॉर्ड साझाकरण (ABHA Records)'}
            {step === 2 && '2. आवाज एवं वार्तालाप रिकॉर्डिंग (Voice Intake)'}
            {step === 3 && '3. डॉक्टर के साथ सारांश साझा करना (Doctor Hand-off)'}
          </h2>
        </div>

        {/* Step Content */}
        <div style={{ minHeight: '180px', marginBottom: '32px' }}>
          {step === 1 && (
            <div>
              <p style={{ fontSize: '18px', color: 'var(--color-text-secondary)', marginBottom: '20px' }}>
                मैं अस्पताल कियोस्क को मेरी आभा (ABHA ID) से जुड़े पिछले पर्चे, टेस्ट रिपोर्ट और अस्पताल इतिहास को डॉक्टर की सहायता हेतु प्राप्त करने की अनुमति देता/देती हूँ।
              </p>
              <div
                onClick={() => handleToggle('abha_pull')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '16px',
                  padding: '16px',
                  borderRadius: '12px',
                  background: consents.abha_pull ? 'rgba(59, 130, 246, 0.15)' : 'var(--color-surface-elevated)',
                  border: `2px solid ${consents.abha_pull ? 'var(--color-blue-info)' : 'transparent'}`,
                  cursor: 'pointer',
                }}
              >
                <input
                  type="checkbox"
                  checked={consents.abha_pull}
                  onChange={() => {}}
                  style={{ width: '24px', height: '24px', accentColor: 'var(--color-blue-info)' }}
                />
                <span style={{ fontSize: '18px', fontWeight: 600 }}>हाँ, मुझे ABHA रिकॉर्ड साझा करने की सहमति है</span>
              </div>
            </div>
          )}

          {step === 2 && (
            <div>
              <p style={{ fontSize: '18px', color: 'var(--color-text-secondary)', marginBottom: '20px' }}>
                कियोस्क आपकी आवाज में कही गई तकलीफों को सुनकर समझेगा। यह वार्तालाप केवल आपके वर्तमान ओपीडी सत्र तक सुरक्षित रहेगा तथा सत्र समाप्त होने पर पूर्णतः मिटा दिया जाएगा।
              </p>
              <div
                onClick={() => handleToggle('voice_recording')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '16px',
                  padding: '16px',
                  borderRadius: '12px',
                  background: consents.voice_recording ? 'rgba(16, 185, 129, 0.15)' : 'var(--color-surface-elevated)',
                  border: `2px solid ${consents.voice_recording ? 'var(--color-green-safe)' : 'transparent'}`,
                  cursor: 'pointer',
                }}
              >
                <input
                  type="checkbox"
                  checked={consents.voice_recording}
                  onChange={() => {}}
                  style={{ width: '24px', height: '24px', accentColor: 'var(--color-green-safe)' }}
                />
                <span style={{ fontSize: '18px', fontWeight: 600 }}>हाँ, मुझे आवाज आधारित इतिहास संकलन की सहमति है</span>
              </div>
            </div>
          )}

          {step === 3 && (
            <div>
              <p style={{ fontSize: '18px', color: 'var(--color-text-secondary)', marginBottom: '20px' }}>
                कियोस्क द्वारा तैयार नैदानिक सारांश (Clinical Summary) डॉक्टर के कंप्यूटर पर भेजा जाएगा ताकि आपका परामर्श समय बच सके। डॉक्टर आपके साथ इसे अंतिम रूप देंगे।
              </p>
              <div
                onClick={() => handleToggle('doctor_share')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '16px',
                  padding: '16px',
                  borderRadius: '12px',
                  background: consents.doctor_share ? 'rgba(59, 130, 246, 0.15)' : 'var(--color-surface-elevated)',
                  border: `2px solid ${consents.doctor_share ? 'var(--color-blue-info)' : 'transparent'}`,
                  cursor: 'pointer',
                }}
              >
                <input
                  type="checkbox"
                  checked={consents.doctor_share}
                  onChange={() => {}}
                  style={{ width: '24px', height: '24px', accentColor: 'var(--color-blue-info)' }}
                />
                <span style={{ fontSize: '18px', fontWeight: 600 }}>हाँ, डॉक्टर के साथ सारांश साझा करने की सहमति है</span>
              </div>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: '16px', justifyContent: 'flex-end' }}>
          <KioskButton variant="ghost" size="md" onClick={onDecline}>
            अस्वीकार करें (Decline)
          </KioskButton>
          <KioskButton variant="primary" size="md" onClick={handleNext}>
            {step === 3 ? 'सहमति दें एवं आगे बढ़ें (Accept & Begin)' : 'आगे बढ़ें (Next) →'}
          </KioskButton>
        </div>
      </KioskCard>
    </div>
  );
};

export default ConsentModal;
