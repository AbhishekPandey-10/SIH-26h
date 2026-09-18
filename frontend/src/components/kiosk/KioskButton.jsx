import React, { useState } from 'react';

/**
 * KioskButton — High-affordance touch button for public hospital kiosks.
 * Ensures minimum 48x48px touch target, tactile active depression, and loading state.
 */
export const KioskButton = ({
  children,
  onClick,
  variant = 'primary', // 'primary' | 'secondary' | 'danger' | 'ghost'
  size = 'md',        // 'sm' | 'md' | 'lg'
  disabled = false,
  loading = false,
  icon = null,
  className = '',
  fullWidth = false,
  type = 'button',
  ...props
}) => {
  const [ripples, setRipples] = useState([]);

  const handleTouch = (e) => {
    if (disabled || loading) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX || (e.touches && e.touches[0].clientX)) - rect.left;
    const y = (e.clientY || (e.touches && e.touches[0].clientY)) - rect.top;
    const id = Date.now();

    setRipples((prev) => [...prev, { id, x, y }]);
    setTimeout(() => {
      setRipples((prev) => prev.filter((r) => r.id !== id));
    }, 600);

    if (onClick) onClick(e);
  };

  // Base styles
  const baseStyle = {
    position: 'relative',
    overflow: 'hidden',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
    fontFamily: 'var(--font-family)',
    fontWeight: 600,
    borderRadius: 'var(--border-radius-button)',
    border: 'none',
    cursor: disabled || loading ? 'not-allowed' : 'pointer',
    transition: 'all var(--transition-fast)',
    outline: 'none',
    width: fullWidth ? '100%' : 'auto',
    opacity: disabled ? 0.5 : 1,
    minHeight: 'var(--touch-target-min)',
    minWidth: 'var(--touch-target-min)',
  };

  // Size styles
  const sizeStyles = {
    sm: { padding: '10px 18px', fontSize: '15px' },
    md: { padding: '14px 28px', fontSize: '18px' },
    lg: { padding: '18px 36px', fontSize: '22px', minHeight: '60px' },
  };

  // Variant styles
  const variantStyles = {
    primary: {
      background: 'linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%)',
      color: '#FFFFFF',
      boxShadow: '0 4px 14px rgba(59, 130, 246, 0.4)',
    },
    secondary: {
      background: 'var(--color-surface-elevated)',
      color: 'var(--color-text-primary)',
      border: '1px solid var(--color-border-subtle)',
    },
    danger: {
      background: 'linear-gradient(135deg, #DC2626 0%, #991B1B 100%)',
      color: '#FFFFFF',
      boxShadow: '0 4px 14px rgba(220, 38, 38, 0.4)',
    },
    ghost: {
      background: 'transparent',
      color: 'var(--color-text-secondary)',
      border: '1px solid rgba(255, 255, 255, 0.1)',
    },
  };

  const combinedStyle = {
    ...baseStyle,
    ...sizeStyles[size],
    ...variantStyles[variant],
  };

  return (
    <button
      type={type}
      style={combinedStyle}
      onClick={handleTouch}
      disabled={disabled || loading}
      className={`kiosk-btn ${className}`}
      {...props}
    >
      {loading ? (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
          <svg style={{ animation: 'spin 1s linear infinite', width: '22px', height: '22px' }} viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" strokeDasharray="30 60" />
          </svg>
          <span>कृपया प्रतीक्षा करें...</span>
        </span>
      ) : (
        <>
          {icon && <span style={{ display: 'flex', alignItems: 'center' }}>{icon}</span>}
          <span>{children}</span>
        </>
      )}

      {/* Touch ripple effect */}
      {ripples.map((ripple) => (
        <span
          key={ripple.id}
          style={{
            position: 'absolute',
            left: ripple.x - 20,
            top: ripple.y - 20,
            width: '40px',
            height: '40px',
            borderRadius: '50%',
            background: 'rgba(255, 255, 255, 0.4)',
            transform: 'scale(1)',
            animation: 'ripple 600ms ease-out forwards',
            pointerEvents: 'none',
          }}
        />
      ))}
      <style>{`
        @keyframes ripple {
          to { transform: scale(8); opacity: 0; }
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        .kiosk-btn:active {
          transform: scale(0.97);
        }
      `}</style>
    </button>
  );
};

export default KioskButton;
