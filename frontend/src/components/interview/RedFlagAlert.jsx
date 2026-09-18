import React, { useEffect } from 'react';
import { ShieldAlert, HeartHandshake, PhoneCall, CheckCircle } from 'lucide-react';

/**
 * <RedFlagAlert />
 * PS ID26047 — Emergency Red Flag Patient Safety Overlay
 * 
 * Reassures patient, pauses kiosk intake, and waits for triage nurse override.
 */
export const RedFlagAlert = ({
  alertData,
  onDismiss,
}) => {
  if (!alertData) return null;

  const severity = alertData?.severity || 'red';
  const isRed = severity === 'red';

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(15, 23, 42, 0.88)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 99999,
        padding: '24px',
        animation: 'fadeIn 0.2s ease',
      }}
    >
      <div
        style={{
          background: '#FFFFFF',
          borderRadius: '24px',
          padding: '36px 32px',
          maxWidth: '560px',
          width: '100%',
          textAlign: 'center',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
          border: isRed ? '3px solid #EF4444' : '3px solid #F59E0B',
        }}
      >
        {/* Pulsing Safety Icon */}
        <div
          style={{
            width: '80px',
            height: '80px',
            borderRadius: '50%',
            background: isRed ? '#FEE2E2' : '#FEF3C7',
            color: isRed ? '#DC2626' : '#D97706',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 20px',
            boxShadow: `0 0 0 12px ${isRed ? 'rgba(239, 68, 68, 0.15)' : 'rgba(245, 158, 11, 0.15)'}`,
          }}
        >
          <ShieldAlert size={44} />
        </div>

        {/* Calming Reassurance Heading */}
        <h2 style={{ fontSize: '24px', fontWeight: 800, color: '#0F172A', margin: '0 0 12px' }}>
          कृपया शांति बनाए रखें (Please stay comfortable)
        </h2>

        {/* Reassurance Message */}
        <p style={{ fontSize: '16px', lineHeight: 1.6, color: '#475569', margin: '0 0 24px' }}>
          We're making sure you get the right care quickly. A staff member has been notified and is attending to you immediately.
        </p>

        {/* Calming Notice Box */}
        <div
          style={{
            background: '#F8FAFC',
            borderRadius: '14px',
            padding: '16px 20px',
            border: '1px solid #E2E8F0',
            marginBottom: '24px',
            textAlign: 'left',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#0284C7', fontWeight: 700, fontSize: '14px' }}>
            <HeartHandshake size={20} />
            <span>Triage Priority Hold Active</span>
          </div>
          <div style={{ fontSize: '13px', color: '#64748B', marginTop: '6px' }}>
            Category: <strong>{alertData.category || 'High Priority Clinical Observation'}</strong>
            {alertData.trigger_phrase && (
              <span> • Detected symptom: <em>"{alertData.trigger_phrase}"</em></span>
            )}
          </div>
        </div>

        {/* Staff Help Button / Demo Override */}
        {onDismiss && (
          <button
            onClick={onDismiss}
            style={{
              padding: '10px 24px',
              borderRadius: '10px',
              border: '1px solid #CBD5E1',
              background: '#F1F5F9',
              color: '#334155',
              fontSize: '13px',
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            Staff Override: Resume Interview
          </button>
        )}
      </div>
    </div>
  );
};

export default RedFlagAlert;
