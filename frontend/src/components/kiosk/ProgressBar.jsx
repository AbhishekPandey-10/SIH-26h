import React from 'react';

/**
 * ProgressBar — Smooth animated progress indicator for Kiosk workflows.
 */
export const ProgressBar = ({
  progress = 0, // 0 to 100
  label = '',
  color = 'blue', // 'blue' | 'green' | 'amber' | 'gradient'
  height = '12px',
  showPercentage = true,
  className = '',
}) => {
  const clamped = Math.min(Math.max(progress, 0), 100);

  const getBackground = () => {
    switch (color) {
      case 'green':
        return 'linear-gradient(90deg, #10B981 0%, #059669 100%)';
      case 'amber':
        return 'linear-gradient(90deg, #F59E0B 0%, #D97706 100%)';
      case 'gradient':
        return 'linear-gradient(90deg, #3B82F6 0%, #06B6D4 50%, #10B981 100%)';
      case 'blue':
      default:
        return 'linear-gradient(90deg, #3B82F6 0%, #2563EB 100%)';
    }
  };

  return (
    <div className={`kiosk-progress-container ${className}`} style={{ width: '100%' }}>
      {(label || showPercentage) && (
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '8px',
          fontSize: '15px',
          fontWeight: 600,
          color: 'var(--color-text-secondary)',
        }}>
          <span>{label}</span>
          {showPercentage && <span>{Math.round(clamped)}%</span>}
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
          background: 'rgba(255, 255, 255, 0.08)',
          borderRadius: 'var(--border-radius-pill)',
          overflow: 'hidden',
          position: 'relative',
        }}
      >
        <div
          style={{
            width: `${clamped}%`,
            height: '100%',
            background: getBackground(),
            borderRadius: 'var(--border-radius-pill)',
            transition: 'width 400ms cubic-bezier(0.4, 0, 0.2, 1)',
            boxShadow: '0 0 10px rgba(59, 130, 246, 0.5)',
          }}
        />
      </div>
    </div>
  );
};

export default ProgressBar;
