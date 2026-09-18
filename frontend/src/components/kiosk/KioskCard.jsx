import React from 'react';

/**
 * KioskCard — High-contrast container surface with rounded corners and elevation.
 */
export const KioskCard = ({
  children,
  onClick = null,
  selected = false,
  highlight = null, // 'blue' | 'red' | 'amber' | 'green'
  padding = '24px',
  className = '',
  style = {},
  ...props
}) => {
  const isInteractive = Boolean(onClick);

  const getBorderColor = () => {
    if (selected) return 'var(--color-blue-info)';
    if (highlight === 'red') return 'var(--color-red-flag)';
    if (highlight === 'amber') return 'var(--color-amber-warning)';
    if (highlight === 'green') return 'var(--color-green-safe)';
    if (highlight === 'blue') return 'var(--color-blue-info)';
    return 'var(--color-border-subtle)';
  };

  const getGlow = () => {
    if (selected) return 'var(--shadow-glow-blue)';
    if (highlight === 'red') return 'var(--shadow-glow-red)';
    return 'var(--shadow-md)';
  };

  const cardStyle = {
    background: 'var(--color-surface-secondary)',
    borderRadius: 'var(--border-radius-card)',
    border: `2px solid ${getBorderColor()}`,
    boxShadow: getGlow(),
    padding: padding,
    transition: 'all var(--transition-bounce)',
    cursor: isInteractive ? 'pointer' : 'default',
    position: 'relative',
    overflow: 'hidden',
    backdropFilter: 'blur(10px)',
    ...style,
  };

  return (
    <div
      style={cardStyle}
      onClick={onClick}
      className={`kiosk-card ${isInteractive ? 'interactive' : ''} ${className}`}
      {...props}
    >
      {children}
      <style>{`
        .kiosk-card.interactive:hover {
          background: var(--color-surface-elevated);
          transform: translateY(-2px);
        }
        .kiosk-card.interactive:active {
          transform: scale(0.98);
        }
      `}</style>
    </div>
  );
};

export default KioskCard;
