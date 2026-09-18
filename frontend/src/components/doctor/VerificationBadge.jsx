import React from 'react';

/**
 * VerificationBadge — Trust and provenance badge for Doctor Summary view.
 * Color-codes clinical facts based on source confidence:
 * - patient_reported: Blue
 * - document_extracted: Green
 * - needs_confirmation: Amber
 * - conflicting: Red
 */
export const STATUS_CONFIG = {
  patient_reported: {
    label: 'मरीज द्वारा कथित (Patient Reported)',
    short: 'Patient',
    color: 'var(--color-patient-reported)',
    bg: 'rgba(59, 130, 246, 0.12)',
    border: 'rgba(59, 130, 246, 0.4)',
    icon: '🗣️',
  },
  document_extracted: {
    label: 'दस्तावेज़ से सत्यापित (Doc Verified)',
    short: 'Doc Crop',
    color: 'var(--color-document-extracted)',
    bg: 'rgba(16, 185, 129, 0.12)',
    border: 'rgba(16, 185, 129, 0.4)',
    icon: '📄',
  },
  needs_confirmation: {
    label: 'पुष्टि अपेक्षित (Needs Confirmation)',
    short: 'Confirm?',
    color: 'var(--color-needs-confirmation)',
    bg: 'rgba(245, 158, 11, 0.12)',
    border: 'rgba(245, 158, 11, 0.4)',
    icon: '⚠️',
  },
  conflicting: {
    label: 'परस्पर विरोधी (Conflicting)',
    short: 'Conflict!',
    color: 'var(--color-conflicting)',
    bg: 'rgba(220, 38, 38, 0.12)',
    border: 'rgba(220, 38, 38, 0.4)',
    icon: '⚡',
  },
};

export const VerificationBadge = ({
  status = 'patient_reported',
  onClick = null,
  compact = false,
  className = '',
}) => {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.patient_reported;

  return (
    <span
      onClick={onClick}
      className={`verification-badge ${className}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: compact ? '4px 10px' : '6px 14px',
        borderRadius: 'var(--border-radius-pill)',
        background: config.bg,
        border: `1px solid ${config.border}`,
        color: config.color,
        fontSize: compact ? '12px' : '14px',
        fontWeight: 600,
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all var(--transition-fast)',
      }}
      title={config.label}
    >
      <span style={{ fontSize: '13px' }}>{config.icon}</span>
      <span>{compact ? config.short : config.label}</span>
    </span>
  );
};

export default VerificationBadge;
