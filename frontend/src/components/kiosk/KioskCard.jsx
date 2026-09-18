import React from 'react';

/**
 * KioskCard — Crisp high-contrast white container surface for hospital kiosks.
 * Features 16px radius, subtle border, accessible depth, and tactile hover/press states.
 */
export const KioskCard = ({
  children,
  onClick = null,
  selected = false,
  highlight = null, // 'green' | 'blue' | 'amber' | 'red'
  padding = '24px',
  className = '',
  style = {},
  ...props
}) => {
  const isInteractive = Boolean(onClick);

  const getBorderColor = () => {
    if (selected) return 'var(--color-action-primary, #059669)';
    if (highlight === 'green') return 'var(--color-green-safe, #059669)';
    if (highlight === 'blue') return 'var(--color-blue-info, #0284C7)';
    if (highlight === 'amber') return 'var(--color-amber-warning, #D97706)';
    if (highlight === 'red') return 'var(--color-red-flag, #DC2626)';
    return 'var(--color-border-subtle, #E2E8F0)';
  };

  const getShadow = () => {
    if (selected) return '0 0 0 3px rgba(5, 150, 105, 0.25), 0 8px 20px rgba(15, 23, 42, 0.08)';
    if (highlight === 'green') return '0 0 0 2px rgba(5, 150, 105, 0.2), 0 6px 16px rgba(15, 23, 42, 0.06)';
    if (highlight === 'blue') return '0 0 0 2px rgba(2, 132, 199, 0.2), 0 6px 16px rgba(15, 23, 42, 0.06)';
    if (highlight === 'red') return '0 0 0 2px rgba(220, 38, 38, 0.2), 0 6px 16px rgba(15, 23, 42, 0.06)';
    return 'var(--shadow-card, 0 4px 16px 0 rgba(15, 23, 42, 0.06), 0 1px 4px 0 rgba(15, 23, 42, 0.04))';
  };

  const cardStyle = {
    background: '#FFFFFF',
    borderRadius: 'var(--border-radius-card, 16px)',
    border: `2px solid ${getBorderColor()}`,
    boxShadow: getShadow(),
    padding: padding,
    transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
    cursor: isInteractive ? 'pointer' : 'default',
    position: 'relative',
    overflow: 'hidden',
    color: 'var(--color-text-primary, #0F172A)',
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
    </div>
  );
};

export default KioskCard;
