import React from 'react';

/**
 * ProgressBar — High-contrast clinical progress indicator for Kiosk workflows.
 */
export const ProgressBar = ({
  progress = 0, // 0 to 100
  label = '',
  color = 'green', // 'green' | 'blue' | 'amber' | 'red'
  height = '12px',
  showPercentage = true,
  className = '',
}) => {
  const clamped = Math.min(Math.max(progress, 0), 100);

  const getBarColor = () => {
    switch (color) {
      case 'blue':
        return '#0284C7';
      case 'amber':
        return '#D97706';
      case 'red':
        return '#DC2626';
      case 'green':
      default:
        return '#059669';
    }
  };

  return (
    <div className={`kiosk-progress-container ${className}`} style={{ width: '100%' }}>
      {(label || showPercentage) && (
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '8px',
            fontSize: '15px',
            fontWeight: 700,
            color: 'var(--color-text-secondary, #334155)',
          }}
        >
          <span>{label}</span>
          {showPercentage && (
            <span style={{ color: getBarColor(), fontWeight: 800 }}>
              {Math.round(clamped)}%
            </span>
          )}
        </div>
      )}

      <div
        role="progressbar"
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={100}
        style={{
          width: '100%',
          height: height,
          background: 'var(--color-border-subtle, #E2E8F0)',
          borderRadius: 'var(--border-radius-pill, 9999px)',
          overflow: 'hidden',
          position: 'relative',
        }}
      >
        <div
          style={{
            width: `${clamped}%`,
            height: '100%',
            background: getBarColor(),
            borderRadius: 'var(--border-radius-pill, 9999px)',
            transition: 'width 350ms cubic-bezier(0.4, 0, 0.2, 1)',
          }}
        />
      </div>
    </div>
  );
};

export default ProgressBar;
