import React, { useState, useEffect } from 'react';
import { SessionProvider, useSession } from './contexts/SessionContext';
import LanguageSelector from './components/kiosk/LanguageSelector';
import IdentityScreen from './components/kiosk/IdentityScreen';
import ConsentFlow from './components/kiosk/ConsentFlow';
import KioskDashboard from './components/kiosk/KioskDashboard';
import IdleTimeoutOverlay from './components/kiosk/IdleTimeoutOverlay';
import DesignSystemShowcase from './pages/DesignSystemShowcase';
import useIdleTimeout from './hooks/useIdleTimeout';
import KioskButton from './components/kiosk/KioskButton';

function KioskApp() {
  const {
    language,
    selectLanguage,
    flowStep,
    setFlowStep,
    wipePrivacyData,
    session,
    patient,
  } = useSession();

  const [viewMode, setViewMode] = useState('kiosk'); // 'kiosk' | 'showcase'
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [timeStr, setTimeStr] = useState(() =>
    new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  );

  // Update clock
  useEffect(() => {
    const timer = setInterval(() => {
      setTimeStr(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
    }, 10000);
    return () => clearInterval(timer);
  }, []);

  // Idle timeout: 180s total (3 min), warning at 150s (30s remaining / at 2:30)
  const { isWarningActive, secondsRemaining, extendSession } = useIdleTimeout({
    timeoutMs: 180000,
    warningMs: 30000,
    onTimeout: () => {
      console.warn('[MediKiosk] Inactivity timeout reached. Wiping patient privacy data.');
      wipePrivacyData();
    },
  });

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().then(() => setIsFullscreen(true)).catch(() => {});
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false)).catch(() => {});
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--color-surface-primary)',
      color: 'var(--color-text-primary)',
      position: 'relative',
    }}>
      {/* Top Kiosk System Bar */}
      <header style={{
        height: '64px',
        padding: '0 24px',
        background: 'var(--color-surface-secondary)',
        borderBottom: '1px solid var(--color-border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}>
        {/* Hospital & Project Branding */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '38px',
            height: '38px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '20px',
            boxShadow: '0 2px 8px rgba(59,130,246,0.3)',
          }}>
            🏥
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '17px', fontWeight: 800, letterSpacing: '-0.01em' }}>
                मेडीकियोस्क | MediKiosk OPD
              </span>
              <span style={{
                fontSize: '11px',
                fontWeight: 700,
                color: 'var(--color-blue-info)',
                padding: '2px 8px',
                borderRadius: '999px',
                background: 'rgba(59,130,246,0.15)',
              }}>
                PS ID26047
              </span>
            </div>
            <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '1px' }}>
              AI Clinical History-Taking Software for Indian Hospital OPDs
            </div>
          </div>
        </div>

        {/* Right Status Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {/* Active Session Indicator */}
          {session && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '8px',
              background: 'rgba(16,185,129,0.15)',
              border: '1px solid var(--color-green-safe)',
              fontSize: '13px',
              color: 'var(--color-green-safe)',
              fontWeight: 600,
            }}>
              <span style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: 'var(--color-green-safe)',
                animation: 'pulse 2s infinite',
              }} />
              <span>सत्र सक्रिय: {patient?.name || session.patient_name || 'मरीज'}</span>
            </div>
          )}

          {/* Clock */}
          <span style={{ fontSize: '14px', color: 'var(--color-text-secondary)', fontWeight: 600 }}>
            🕒 {timeStr}
          </span>

          {/* Fullscreen Button */}
          <button
            onClick={toggleFullscreen}
            style={{
              background: 'transparent',
              border: '1px solid var(--color-border-subtle)',
              color: 'var(--color-text-secondary)',
              borderRadius: '8px',
              padding: '6px 12px',
              fontSize: '13px',
              cursor: 'pointer',
              fontWeight: 600,
            }}
            title="Toggle Fullscreen"
          >
            {isFullscreen ? '⤡ Exit' : '⤢ Fullscreen'}
          </button>

          {/* Mode Switcher */}
          <button
            onClick={() => setViewMode(viewMode === 'kiosk' ? 'showcase' : 'kiosk')}
            style={{
              background: viewMode === 'showcase' ? 'var(--color-blue-info)' : 'rgba(255,255,255,0.06)',
              border: '1px solid var(--color-border-subtle)',
              color: '#FFFFFF',
              borderRadius: '8px',
              padding: '6px 12px',
              fontSize: '13px',
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            {viewMode === 'kiosk' ? '🎨 Design Showcase' : '🏥 Live Kiosk Flow'}
          </button>
        </div>
      </header>

      {/* Main Kiosk Flow Canvas */}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {viewMode === 'showcase' ? (
          <DesignSystemShowcase onBack={() => setViewMode('kiosk')} />
        ) : (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            {flowStep === 'language' && (
              <LanguageSelector
                selectedLanguage={language}
                onSelectLanguage={selectLanguage}
              />
            )}

            {flowStep === 'identity' && (
              <IdentityScreen
                onBack={() => setFlowStep('language')}
              />
            )}

            {flowStep === 'consent' && (
              <ConsentFlow
                onBack={() => setFlowStep('identity')}
              />
            )}

            {flowStep === 'active' && (
              <KioskDashboard />
            )}
          </div>
        )}
      </main>

      {/* Privacy Guarantee Footer */}
      <footer style={{
        padding: '14px 24px',
        background: 'var(--color-surface-secondary)',
        borderTop: '1px solid var(--color-border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontSize: '13px',
        color: 'var(--color-text-muted)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>🔒 100% On-Premise OPD Kiosk</span>
          <span>•</span>
          <span>DISHA & ISO 27799 Compliant</span>
          <span>•</span>
          <span>ABDM M2 Milestone Validated</span>
        </div>
        <div>
          <span>Auto-Purge Inactivity: 3:00 min</span>
          {session?.session_id && (
            <span style={{ marginLeft: '12px', fontFamily: 'monospace', color: 'var(--color-blue-info)' }}>
              ID: {session.session_id}
            </span>
          )}
        </div>
      </footer>

      {/* Screen-blocking Idle Timeout Overlay */}
      <IdleTimeoutOverlay
        isOpen={isWarningActive}
        secondsRemaining={secondsRemaining}
        onExtend={extendSession}
        onResetNow={wipePrivacyData}
      />
    </div>
  );
}

export function App() {
  return (
    <SessionProvider>
      <KioskApp />
    </SessionProvider>
  );
}

export default App;
