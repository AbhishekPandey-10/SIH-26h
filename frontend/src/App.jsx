import React, { useState, useEffect } from 'react';
import { SessionProvider, useSession } from './contexts/SessionContext';
import LanguageSelector from './components/kiosk/LanguageSelector';
import IdentityScreen from './components/kiosk/IdentityScreen';
import ConsentFlow from './components/kiosk/ConsentFlow';
import KioskDashboard from './components/kiosk/KioskDashboard';
import IdleTimeoutOverlay from './components/kiosk/IdleTimeoutOverlay';
import InterviewScreen from './components/interview/InterviewScreen';
import DesignSystemShowcase from './pages/DesignSystemShowcase';
import DoctorDashboard from './pages/DoctorDashboard';
import DocumentWorkflow from './components/documents/DocumentWorkflow';
import useIdleTimeout from './hooks/useIdleTimeout';
import KioskButton from './components/kiosk/KioskButton';
import OfflineIndicator from './components/common/OfflineIndicator';
import BodyMap from './components/kiosk/BodyMap';
import AyushInterview from './components/interview/AyushInterview';
import { registerSpacebarFallback } from './services/voiceNavigation';
import {
  Maximize,
  Minimize,
  Palette,
  LayoutGrid,
  Clock,
  ShieldCheck,
  CheckCircle2,
  ArrowLeft,
  LogOut,
  Hospital,
  Activity,
  Type,
  Sun,
  Timer,
  Eye,
  Key,
} from 'lucide-react';

function KioskApp() {
  const {
    language,
    selectLanguage,
    flowStep,
    setFlowStep,
    wipePrivacyData,
    session,
    patient,
    isLargeText,
    setIsLargeText,
    isHighContrast,
    setIsHighContrast,
    isStaffMode,
    setIsStaffMode,
    voiceOnlyMode,
    bodyMapSelections,
    setBodyMapSelections,
  } = useSession();

  const [viewMode, setViewMode] = useState('kiosk'); // 'kiosk' | 'showcase'
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [logoTapCount, setLogoTapCount] = useState(0);
  const [timeStr, setTimeStr] = useState(() =>
    new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  );

  // TASK 1: Voice-Only Mode Physical Spacebar Fallback
  useEffect(() => {
    if (voiceOnlyMode) {
      const unregister = registerSpacebarFallback(() => {
        console.log('[MediKiosk] Spacebar physical fallback confirm executed');
      });
      return unregister;
    }
  }, [voiceOnlyMode]);

  // Update clock every 10s
  useEffect(() => {
    const timer = setInterval(() => {
      setTimeStr(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
    }, 10000);
    return () => clearInterval(timer);
  }, []);

  // Queue-Safe Inactivity Timeout: 90s total (warning at 30s remaining)
  const { isWarningActive, secondsRemaining, totalSecondsLeft, extendSession } = useIdleTimeout({
    timeoutMs: 90000,
    warningMs: 30000,
    onTimeout: () => {
      console.warn('[MediKiosk] Session inactivity timeout reached. Resetting kiosk.');
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

  // Secret 3-tap on hospital logo enables Staff/Dev Mode
  const handleLogoTap = () => {
    setLogoTapCount((prev) => {
      const next = prev + 1;
      if (next >= 3) {
        setIsStaffMode(!isStaffMode);
        return 0;
      }
      return next;
    });
  };

  const formatTimer = (totalSeconds) => {
    const m = Math.floor(totalSeconds / 60);
    const s = totalSeconds % 60;
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        background: '#F8FAFC',
        color: '#0F172A',
        position: 'relative',
      }}
    >
      {/* PHASE 5: Sticky Offline Indicator Banner */}
      <OfflineIndicator />

      {/* Top Kiosk System Bar */}
      <header
        style={{
          height: '74px',
          padding: '0 20px',
          background: '#FFFFFF',
          borderBottom: '2.5px solid #E2E8F0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          position: 'sticky',
          top: 0,
          zIndex: 100,
          boxShadow: '0 2px 8px rgba(15, 23, 42, 0.04)',
        }}
      >
        {/* Hospital & Project Branding (3 taps to toggle staff mode) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div
            onClick={handleLogoTap}
            title="Hospital OPD Kiosk (Tap 3x for staff mode)"
            style={{
              width: '46px',
              height: '46px',
              borderRadius: '12px',
              background: '#059669',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#FFFFFF',
              boxShadow: '0 4px 10px rgba(5, 150, 105, 0.25)',
              cursor: 'pointer',
              userSelect: 'none',
            }}
          >
            <Hospital size={28} strokeWidth={2.5} />
          </div>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '18px', fontWeight: 800, color: '#0F172A', letterSpacing: '-0.02em' }}>
                मेडीकियोस्क | MediKiosk OPD
              </span>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 800,
                  color: '#0284C7',
                  padding: '2px 8px',
                  borderRadius: '999px',
                  background: '#F0F9FF',
                  border: '1px solid #BAE6FD',
                }}
              >
                PS ID26047
              </span>

              {isStaffMode && (
                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: 800,
                    color: '#92400E',
                    padding: '2px 8px',
                    borderRadius: '999px',
                    background: '#FEF3C7',
                    border: '1px solid #F59E0B',
                  }}
                >
                  🛠️ STAFF MODE
                </span>
              )}
            </div>
            <div style={{ fontSize: '12px', color: '#475569', fontWeight: 600 }}>
              AI Clinical History-Taking & Triage for Indian Hospital OPDs
            </div>
          </div>
        </div>

        {/* Center/Right: Accessibility Toggles, Live Countdown & Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {/* 1. Large Text Accessibility Toggle */}
          <button
            type="button"
            onClick={() => setIsLargeText(!isLargeText)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 12px',
              borderRadius: '10px',
              background: isLargeText ? '#ECFDF5' : '#FFFFFF',
              border: `2px solid ${isLargeText ? '#059669' : '#CBD5E1'}`,
              color: isLargeText ? '#065F46' : '#0F172A',
              fontSize: '13px',
              fontWeight: 800,
              cursor: 'pointer',
              boxShadow: '0 1px 3px rgba(15, 23, 42, 0.04)',
            }}
            title="Toggle Large Text"
          >
            <Type size={16} color={isLargeText ? '#059669' : '#475569'} />
            <span>
              {language === 'en'
                ? isLargeText
                  ? 'Large Text (ON)'
                  : 'Large Text (A+)'
                : language === 'pa'
                ? isLargeText
                  ? 'ਵੱਡਾ ਟੈਕਸਟ (ON)'
                  : 'ਵੱਡਾ ਟੈਕਸਟ (A+)'
                : isLargeText
                ? 'बड़ा टेक्स्ट (ON)'
                : 'बड़ा टेक्स्ट (A+)'}
            </span>
          </button>

          {/* 2. High Contrast Medical Mode Toggle */}
          <button
            type="button"
            onClick={() => setIsHighContrast(!isHighContrast)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 12px',
              borderRadius: '10px',
              background: isHighContrast ? '#0F172A' : '#FFFFFF',
              border: `2px solid ${isHighContrast ? '#FDE047' : '#CBD5E1'}`,
              color: isHighContrast ? '#FDE047' : '#0F172A',
              fontSize: '13px',
              fontWeight: 800,
              cursor: 'pointer',
              boxShadow: '0 1px 3px rgba(15, 23, 42, 0.04)',
            }}
            title="Toggle High Contrast Mode"
          >
            <Sun size={16} color={isHighContrast ? '#FDE047' : '#475569'} />
            <span>
              {language === 'en'
                ? isHighContrast
                  ? 'High Contrast (ON)'
                  : 'High Contrast'
                : language === 'pa'
                ? isHighContrast
                  ? 'ਹਾਈ ਕੰਟਰਾਸਟ (ON)'
                  : 'ਹਾਈ ਕੰਟਰਾਸਟ'
                : isHighContrast
                ? 'हाई कंट्रास्ट (ON)'
                : 'हाई कंट्रास्ट'}
            </span>
          </button>

          {/* 3. Live Inactivity Reset Countdown Ticker */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 12px',
              borderRadius: '10px',
              background: totalSecondsLeft <= 30 ? '#FEF2F2' : '#F1F5F9',
              border: `1.5px solid ${totalSecondsLeft <= 30 ? '#EF4444' : '#E2E8F0'}`,
              color: totalSecondsLeft <= 30 ? '#991B1B' : '#334155',
              fontSize: '13px',
              fontWeight: 800,
              fontFamily: 'monospace',
            }}
            title="Time remaining before screen auto-resets for privacy"
          >
            <Timer size={16} color={totalSecondsLeft <= 30 ? '#DC2626' : '#64748B'} />
            <span>
              {language === 'en' ? 'Reset: ' : language === 'pa' ? 'ਰੀਸੈੱਟ: ' : 'रीसेट: '}
              {formatTimer(totalSecondsLeft)}
            </span>
          </div>

          {/* Wall Clock */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '13px',
              color: '#334155',
              fontWeight: 700,
              padding: '8px 10px',
              background: '#F1F5F9',
              borderRadius: '10px',
            }}
          >
            <Clock size={15} color="#64748B" />
            <span>{timeStr}</span>
          </div>

          {/* Fullscreen Button */}
          <button
            onClick={toggleFullscreen}
            style={{
              background: '#FFFFFF',
              border: '2px solid #CBD5E1',
              color: '#0F172A',
              borderRadius: '10px',
              padding: '8px 12px',
              fontSize: '13px',
              cursor: 'pointer',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
            title="Toggle Fullscreen"
          >
            {isFullscreen ? <Minimize size={16} /> : <Maximize size={16} />}
            <span>{isFullscreen ? 'Exit' : 'Full'}</span>
          </button>

          {/* Doctor Cabin Switcher */}
          <button
            onClick={() => setViewMode(viewMode === 'doctor' ? 'kiosk' : 'doctor')}
            style={{
              background: viewMode === 'doctor' ? '#059669' : '#FFFFFF',
              border: '2px solid #059669',
              color: viewMode === 'doctor' ? '#FFFFFF' : '#059669',
              borderRadius: '10px',
              padding: '8px 14px',
              fontSize: '13px',
              cursor: 'pointer',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
            title="Switch to Doctor Cabin Command Center"
          >
            <Stethoscope size={16} />
            <span>{viewMode === 'doctor' ? 'Kiosk View' : 'Doctor Cabin'}</span>
          </button>

          {/* Gated Design System Showcase (Only visible in Staff Mode) */}
          {isStaffMode && (
            <button
              onClick={() => setViewMode(viewMode === 'kiosk' ? 'showcase' : 'kiosk')}
              style={{
                background: viewMode === 'showcase' ? '#0F172A' : '#FFFFFF',
                border: '2px solid #CBD5E1',
                color: viewMode === 'showcase' ? '#FFFFFF' : '#0F172A',
                borderRadius: '10px',
                padding: '8px 12px',
                fontSize: '13px',
                cursor: 'pointer',
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              {viewMode === 'kiosk' ? <Palette size={16} color="#059669" /> : <LayoutGrid size={16} />}
              <span>{viewMode === 'kiosk' ? 'Design' : 'Flow'}</span>
            </button>
          )}
        </div>
      </header>

      {/* Main Kiosk Flow Canvas */}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {viewMode === 'showcase' ? (
          <DesignSystemShowcase onBack={() => setViewMode('kiosk')} />
        ) : viewMode === 'doctor' ? (
          <DoctorDashboard
            session={session}
            patient={patient}
            onBackToKiosk={() => setViewMode('kiosk')}
          />
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
              <KioskDashboard
                onStartInterview={() => setFlowStep('interview')}
                onScanDocuments={() => setFlowStep('scan')}
                onOpenBodyMap={() => setFlowStep('bodymap')}
                onStartAyush={() => setFlowStep('ayush')}
              />
            )}

            {flowStep === 'bodymap' && (
              <div style={{ flex: 1, padding: '24px 20px', maxWidth: '840px', margin: '0 auto', width: '100%' }}>
                <div style={{ marginBottom: '16px' }}>
                  <KioskButton
                    variant="secondary"
                    size="sm"
                    icon={<ArrowLeft size={18} />}
                    onClick={() => setFlowStep('active')}
                  >
                    {language === 'en' ? '← Back to Dashboard' : '← डैशबोर्ड पर वापस जाएं'}
                  </KioskButton>
                </div>
                <BodyMap
                  language={language || 'hi'}
                  initialSelected={bodyMapSelections || []}
                  onConfirm={(regions) => {
                    setBodyMapSelections(regions);
                    if (session?.session_id) {
                      fetch(`/api/session/${session.session_id}/configure`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ body_map_selections: regions }),
                      }).catch(() => {});
                    }
                    setFlowStep('interview');
                  }}
                  onSkip={() => setFlowStep('interview')}
                />
              </div>
            )}

            {flowStep === 'ayush' && (
              <div style={{ flex: 1, padding: '24px 20px', maxWidth: '960px', margin: '0 auto', width: '100%' }}>
                <div style={{ marginBottom: '16px' }}>
                  <KioskButton
                    variant="secondary"
                    size="sm"
                    icon={<ArrowLeft size={18} />}
                    onClick={() => setFlowStep('active')}
                  >
                    {language === 'en' ? '← Back to Dashboard' : '← डैशबोर्ड पर वापस जाएं'}
                  </KioskButton>
                </div>
                <AyushInterview
                  sessionId={session?.session_id || 'dev-test-001'}
                  language={language || 'hi'}
                  onComplete={() => setFlowStep('active')}
                />
              </div>
            )}

            {flowStep === 'scan' && (
              <DocumentWorkflow
                sessionId={session?.session_id || 'dev-test-001'}
                language={language}
                onBack={() => setFlowStep('active')}
              />
            )}

            {flowStep === 'interview' && (
              <div style={{ flex: 1, padding: '24px 20px', maxWidth: '960px', margin: '0 auto', width: '100%' }}>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '20px',
                  }}
                >
                  <KioskButton
                    variant="secondary"
                    size="sm"
                    icon={<ArrowLeft size={18} />}
                    onClick={() => setFlowStep('active')}
                  >
                    {language === 'en'
                      ? '← Back to Dashboard'
                      : language === 'pa'
                      ? 'ਡੈਸ਼ਬੋਰਡ ਤੇ ਵਾਪਸ ਜਾਓ'
                      : 'डैशबोर्ड पर वापस जाएं (Back to Dashboard)'}
                  </KioskButton>

                  <KioskButton
                    variant="danger"
                    size="sm"
                    icon={<LogOut size={18} />}
                    onClick={wipePrivacyData}
                  >
                    {language === 'en'
                      ? 'End Session'
                      : language === 'pa'
                      ? 'ਸੈਸ਼ਨ ਸਮਾਪਤ ਕਰੋ'
                      : 'सत्र समाप्त करें (End Session)'}
                  </KioskButton>
                </div>

                <InterviewScreen
                  sessionId={session?.session_id || 'dev-test-001'}
                  language={language || 'hi'}
                  onFinish={wipePrivacyData}
                />
              </div>
            )}
          </div>
        )}
      </main>

      {/* Privacy Guarantee Footer */}
      <footer
        style={{
          padding: '16px 24px',
          background: '#FFFFFF',
          borderTop: '2.5px solid #E2E8F0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '13px',
          color: '#475569',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <ShieldCheck size={18} color="#059669" />
          <span style={{ fontWeight: 800, color: '#0F172A' }}>100% On-Premise OPD Kiosk</span>
          <span>•</span>
          <span>DISHA & ISO 27799 Compliant</span>
          <span>•</span>
          <span style={{ color: '#0284C7', fontWeight: 800 }}>ABDM M2 Milestone Validated</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <span>Auto-Purge Queue Reset: 1:30 min</span>

          {/* Discrete Staff Mode Toggle Button for hospital operators */}
          <button
            onClick={() => setIsStaffMode(!isStaffMode)}
            style={{
              background: 'none',
              border: 'none',
              color: isStaffMode ? '#D97706' : '#94A3B8',
              fontSize: '12px',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <Key size={13} />
            <span>{isStaffMode ? 'Staff Mode (Active)' : 'Staff Mode'}</span>
          </button>
        </div>
      </footer>

      {/* Screen-blocking Idle Timeout Overlay with Countdown */}
      <IdleTimeoutOverlay
        isOpen={isWarningActive}
        secondsRemaining={secondsRemaining}
        language={language || 'hi'}
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
