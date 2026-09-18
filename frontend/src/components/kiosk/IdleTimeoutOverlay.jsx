import React from 'react';
import KioskCard from './KioskCard';
import KioskButton from './KioskButton';

/**
 * IdleTimeoutOverlay — Screen-blocking overlay warning patient 30s before privacy wipe.
 */
export const IdleTimeoutOverlay = ({
  isOpen = false,
  secondsRemaining = 30,
  onExtend,
  onResetNow,
}) => {
  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(15, 23, 42, 0.92)',
      backdropFilter: 'blur(16px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 2000,
      padding: '20px',
    }}>
      <KioskCard
        padding="40px"
        highlight="amber"
        style={{
          width: '100%',
          maxWidth: '560px',
          textAlign: 'center',
          background: 'var(--color-surface-secondary)',
        }}
      >
        <div style={{
          width: '80px',
          height: '80px',
          borderRadius: '50%',
          background: 'rgba(245, 158, 11, 0.15)',
          border: '2px solid var(--color-amber-warning)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '36px',
          margin: '0 auto 20px',
        }}>
          ⏳
        </div>

        <h2 style={{ fontSize: '28px', fontWeight: 800, marginBottom: '8px' }}>
          क्या आप अभी भी यहाँ हैं?
        </h2>
        <p style={{ fontSize: '18px', color: 'var(--color-text-secondary)', marginBottom: '24px' }}>
          Are you still there? Kiosk will reset to protect your medical privacy in:
        </p>

        <div style={{
          fontSize: '48px',
          fontWeight: 900,
          color: secondsRemaining <= 10 ? 'var(--color-red-flag)' : 'var(--color-amber-warning)',
          marginBottom: '32px',
          fontFamily: 'monospace',
        }}>
          00:{String(secondsRemaining).padStart(2, '0')}
        </div>

        <div style={{ display: 'flex', gap: '16px', justifyContent: 'center' }}>
          <KioskButton variant="secondary" size="md" onClick={onResetNow}>
            सत्र समाप्त करें (Exit Now)
          </KioskButton>
          <KioskButton variant="primary" size="lg" onClick={onExtend}>
            हाँ, जारी रखें (Continue)
          </KioskButton>
        </div>
      </KioskCard>
    </div>
  );
};

export default IdleTimeoutOverlay;
