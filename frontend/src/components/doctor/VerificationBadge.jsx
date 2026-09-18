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
  doctor_edited: {
    label: 'डॉक्टर द्वारा संपादित (Doctor-edited)',
    short: 'Doctor-edited',
    color: '#9333EA',
    bg: 'rgba(147, 51, 234, 0.12)',
    border: 'rgba(147, 51, 234, 0.4)',
    icon: '✍️',
  },
};

export const VerificationBadge = ({
  status = 'patient_reported',
  sourceCount = 0,
  onClick = null,
  compact = false,
  className = '',
}) => {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.patient_reported;
  const tooltipText = `${config.label}${sourceCount > 0 ? ` • ${sourceCount} verified source citation(s)` : ''}`;

  return (
    <span
      onClick={onClick}
      className={`verification-badge ${className}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: compact ? '3px 8px' : '5px 12px',
        borderRadius: '20px',
        background: config.bg,
        border: `1px solid ${config.border}`,
        color: config.color,
        fontSize: compact ? '11px' : '13px',
        fontWeight: 700,
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.15s ease',
      }}
      title={tooltipText}
    >
      <span style={{ fontSize: '13px' }}>{config.icon}</span>
      <span>{compact ? config.short : config.label}</span>
      {sourceCount > 0 && (
        <span
          style={{
            fontSize: '10px',
            opacity: 0.85,
            background: 'rgba(0,0,0,0.1)',
            padding: '1px 5px',
            borderRadius: '10px',
          }}
        >
          {sourceCount} src
        </span>
      )}
    </span>
  );
};

export default VerificationBadge;
