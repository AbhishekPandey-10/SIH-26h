import React, { useState } from 'react';

/**
 * KioskButton — High-affordance, tactile touch button for public hospital kiosks.
 * Features large touch targets, crisp solid colors (NO murky gradients),
 * prominent SVG/image slots, and optional secondary subtext for non-tech patients.
 */
export const KioskButton = ({
  children,
  sublabel = null,
  onClick,
  variant = 'primary', // 'primary' | 'secondary' | 'danger' | 'info' | 'amber' | 'outline' | 'ghost'
  size = 'md',        // 'sm' | 'md' | 'lg' | 'xl'
  disabled = false,
  loading = false,
  icon = null,
  iconPosition = 'left', // 'left' | 'right'
  badge = null,
  className = '',
  fullWidth = false,
  type = 'button',
  style = {},
  ...props
}) => {
  const [ripples, setRipples] = useState([]);

  const handleTouch = (e) => {
    if (disabled || loading) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX || (e.touches && e.touches[0].clientX) || rect.width / 2) - rect.left;
    const y = (e.clientY || (e.touches && e.touches[0].clientY) || rect.height / 2) - rect.top;
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
    fontWeight: 700,
    borderRadius: 'var(--border-radius-button, 14px)',
    cursor: disabled || loading ? 'not-allowed' : 'pointer',
    transition: 'all 0.15s cubic-bezier(0.4, 0, 0.2, 1)',
    outline: 'none',
    width: fullWidth ? '100%' : 'auto',
    opacity: disabled ? 0.55 : 1,
    letterSpacing: '-0.01em',
    textDecoration: 'none',
    userSelect: 'none',
    WebkitTapHighlightColor: 'transparent',
    ...style,
  };

  // Sizing ergonomics
  const sizeStyles = {
    sm: { padding: '10px 18px', fontSize: '15px', minHeight: '48px', minWidth: '48px' },
    md: { padding: '14px 26px', fontSize: '17px', minHeight: '56px', minWidth: '56px' },
    lg: { padding: '18px 32px', fontSize: '20px', minHeight: '66px', minWidth: '66px' },
    xl: { padding: '22px 38px', fontSize: '22px', minHeight: '76px', minWidth: '76px' },
  };

  // High-Contrast Solid Variants (NO purple/blue gradients)
  const variantStyles = {
    primary: {
      background: 'var(--color-action-primary, #059669)',
      color: '#FFFFFF',
      border: '2px solid #047857',
      boxShadow: '0 4px 10px rgba(5, 150, 105, 0.25), 0 2px 4px rgba(15, 23, 42, 0.08)',
    },
    secondary: {
      background: '#FFFFFF',
      color: 'var(--color-text-primary, #0F172A)',
      border: '2px solid var(--color-border-strong, #CBD5E1)',
      boxShadow: '0 2px 6px rgba(15, 23, 42, 0.06)',
    },
    danger: {
      background: 'var(--color-action-danger, #DC2626)',
      color: '#FFFFFF',
      border: '2px solid #B91C1C',
      boxShadow: '0 4px 10px rgba(220, 38, 38, 0.25), 0 2px 4px rgba(15, 23, 42, 0.08)',
    },
    info: {
      background: 'var(--color-action-info, #0284C7)',
      color: '#FFFFFF',
      border: '2px solid #0369A1',
      boxShadow: '0 4px 10px rgba(2, 132, 199, 0.25), 0 2px 4px rgba(15, 23, 42, 0.08)',
    },
    amber: {
      background: 'var(--color-amber-warning, #D97706)',
      color: '#FFFFFF',
      border: '2px solid #B45309',
      boxShadow: '0 4px 10px rgba(217, 119, 6, 0.25)',
    },
    outline: {
      background: '#FFFFFF',
      color: 'var(--color-action-primary, #059669)',
      border: '2px solid var(--color-action-primary, #059669)',
      boxShadow: '0 2px 6px rgba(15, 23, 42, 0.04)',
    },
    ghost: {
      background: 'transparent',
      color: 'var(--color-text-secondary, #334155)',
      border: '2px solid transparent',
      boxShadow: 'none',
    },
  };

  const currentSize = sizeStyles[size] || sizeStyles.md;
  const currentVariant = variantStyles[variant] || variantStyles.primary;

  const combinedStyle = {
    ...baseStyle,
    ...currentSize,
    ...currentVariant,
    ...style,
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
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '10px' }}>
          <svg
            style={{ animation: 'spin 1s linear infinite', width: '24px', height: '24px' }}
            viewBox="0 0 24 24"
            fill="none"
          >
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" opacity="0.25" />
            <path
              d="M12 2a10 10 0 0 1 10 10"
              stroke="currentColor"
              strokeWidth="4"
              strokeLinecap="round"
            />
          </svg>
          <span>कृपया प्रतीक्षा करें... (Please wait)</span>
        </span>
      ) : (
        <>
          {icon && iconPosition === 'left' && (
            <span
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              {icon}
            </span>
          )}

          <span
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: fullWidth ? 'center' : 'flex-start',
              textAlign: fullWidth ? 'center' : 'left',
              lineHeight: 1.25,
            }}
          >
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
              {children}
              {badge && (
                <span
                  style={{
                    fontSize: '11px',
                    padding: '2px 8px',
                    borderRadius: '999px',
                    background: 'rgba(255, 255, 255, 0.25)',
                    fontWeight: 800,
                  }}
                >
                  {badge}
                </span>
              )}
            </span>
            {sublabel && (
              <span
                style={{
                  fontSize: '12px',
                  fontWeight: 500,
                  opacity: 0.88,
                  marginTop: '2px',
                }}
              >
                {sublabel}
              </span>
            )}
          </span>

          {icon && iconPosition === 'right' && (
            <span
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              {icon}
            </span>
          )}
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
            animation: 'touchRipple 600ms ease-out forwards',
            pointerEvents: 'none',
          }}
        />
      ))}
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </button>
  );
};

export default KioskButton;
