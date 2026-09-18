import React, { useState, useRef, useEffect } from 'react';
import KioskCard from './KioskCard';
import KioskButton from './KioskButton';
import { useSession } from '../../contexts/SessionContext';

/**
 * Format raw digits into standard ABHA format: XX-XXXX-XXXX-XXXX
 */
function formatAbhaInput(val) {
  if (val.includes('@')) return val; // allow abha address e.g. name@abdm
  const clean = val.replace(/\D/g, '').slice(0, 14);
  const parts = [];
  if (clean.length > 0) parts.push(clean.slice(0, 2));
  if (clean.length > 2) parts.push(clean.slice(2, 6));
  if (clean.length > 6) parts.push(clean.slice(6, 10));
  if (clean.length > 10) parts.push(clean.slice(10, 14));
  return parts.join('-');
}

function formatAadhaarInput(val) {
  const clean = val.replace(/\D/g, '').slice(0, 12);
  const parts = [];
  if (clean.length > 0) parts.push(clean.slice(0, 4));
  if (clean.length > 4) parts.push(clean.slice(4, 8));
  if (clean.length > 8) parts.push(clean.slice(8, 12));
  return parts.join(' ');
}

export const IdentityScreen = ({ onBack }) => {
  const {
    verifyAbha,
    requestAadhaarOtp,
    verifyAadhaarOtp,
    confirmIdentity,
    isLoading,
    error,
    setError,
    language,
  } = useSession();

  const [mode, setMode] = useState('type'); // 'type' | 'qr' | 'aadhaar'
  const [abhaInput, setAbhaInput] = useState('');
  const [aadhaarInput, setAadhaarInput] = useState('');
  const [otpInput, setOtpInput] = useState('');
  const [activeTxnId, setActiveTxnId] = useState(null);
  const [isOtpSent, setIsOtpSent] = useState(false);
  const [pendingDemographics, setPendingDemographics] = useState(null);
  const [isCameraActive, setIsCameraActive] = useState(false);

  const videoRef = useRef(null);

  // Quick helper sample ABHA IDs for kiosk test
  const quickTestAbhas = [
    { label: 'Rajesh Kumar (Known Rx & CBC)', id: 'rajesh.kumar@abdm' },
    { label: 'Sunita Devi (14-Digit Format)', id: '91-2048-9182-3041' },
    { label: 'Amit Sharma', id: 'amit.sharma@abdm' },
  ];

  // Camera stream cleanup
  useEffect(() => {
    return () => {
      if (videoRef.current && videoRef.current.srcObject) {
        const stream = videoRef.current.srcObject;
        stream.getTracks().forEach((t) => t.stop());
      }
    };
  }, []);

  const handleStartCamera = async () => {
    setIsCameraActive(true);
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play();
        }
      }
    } catch (err) {
      console.warn('Camera access error or unsupported:', err);
    }
  };

  const handleSimulateQrScan = async (scannedId = 'rajesh.kumar@abdm') => {
    try {
      const demo = await verifyAbha(scannedId);
      setPendingDemographics(demo);
    } catch (err) {
      // Error handled by context
    }
  };

  const handleAbhaSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!abhaInput.trim()) {
      setError('Please enter your 14-digit ABHA ID or ABHA address.');
      return;
    }
    try {
      const demo = await verifyAbha(abhaInput.trim());
      setPendingDemographics(demo);
    } catch (err) {
      // Handled by context
    }
  };

  const handleRequestAadhaarOtp = async (e) => {
    if (e) e.preventDefault();
    const cleanAadhaar = aadhaarInput.replace(/\s+/g, '');
    if (cleanAadhaar.length !== 12) {
      setError('Aadhaar number must be exactly 12 digits.');
      return;
    }
    try {
      const res = await requestAadhaarOtp(cleanAadhaar);
      setActiveTxnId(res.txn_id);
      setIsOtpSent(true);
      setOtpInput('123456'); // Pre-fill sandbox default OTP
    } catch (err) {
      // Handled by context
    }
  };

  const handleVerifyAadhaarOtp = async (e) => {
    if (e) e.preventDefault();
    if (!otpInput.trim()) {
      setError('Please enter the 6-digit OTP.');
      return;
    }
    try {
      const tempPatient = await verifyAadhaarOtp(activeTxnId, otpInput.trim(), aadhaarInput);
      setPendingDemographics(tempPatient);
    } catch (err) {
      // Handled by context
    }
  };

  // Virtual Keypad helper
  const handleKeypadPress = (val) => {
    if (mode === 'type') {
      if (val === 'BACK') {
        setAbhaInput((prev) => formatAbhaInput(prev.slice(0, -1)));
      } else if (val === 'CLR') {
        setAbhaInput('');
      } else {
        setAbhaInput((prev) => formatAbhaInput(prev + val));
      }
    } else if (mode === 'aadhaar') {
      if (isOtpSent) {
        if (val === 'BACK') setOtpInput((prev) => prev.slice(0, -1));
        else if (val === 'CLR') setOtpInput('');
        else if (otpInput.length < 6) setOtpInput((prev) => prev + val);
      } else {
        if (val === 'BACK') setAadhaarInput((prev) => formatAadhaarInput(prev.slice(0, -1)));
        else if (val === 'CLR') setAadhaarInput('');
        else setAadhaarInput((prev) => formatAadhaarInput(prev + val));
      }
    }
  };

  return (
    <div style={{
      width: '100%',
      maxWidth: '820px',
      margin: '0 auto',
      padding: '24px 20px',
      display: 'flex',
      flexDirection: 'column',
      gap: '24px',
    }}>
      {/* Top Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <KioskButton
          variant="secondary"
          size="sm"
          onClick={onBack}
          style={{ minWidth: 'auto', padding: '10px 18px' }}
        >
          ← भाषा बदलें / Change Language
        </KioskButton>
        <span style={{
          fontSize: '14px',
          fontWeight: 700,
          color: 'var(--color-text-muted)',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
        }}>
          कदम 1 / 3 · पहचान (Identity Verification)
        </span>
      </div>

      {/* Screen Title */}
      <div>
        <h1 style={{ fontSize: '32px', fontWeight: 800, color: 'var(--color-text-primary)' }}>
          अपनी पहचान दर्ज करें (Identify Yourself)
        </h1>
        <p style={{ fontSize: '18px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
          आयुष्मान भारत (ABHA) स्वास्थ्य कार्ड से लिंक करें अथवा आधार द्वारा आगे बढ़ें
        </p>
      </div>

      {/* Mode Switcher Tabs */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: '12px',
      }}>
        <button
          onClick={() => { setMode('type'); setError(null); }}
          style={{
            padding: '16px',
            borderRadius: '12px',
            border: '2px solid',
            borderColor: mode === 'type' ? 'var(--color-blue-info)' : 'rgba(255,255,255,0.1)',
            background: mode === 'type' ? 'rgba(59, 130, 246, 0.15)' : 'var(--color-surface-secondary)',
            color: 'var(--color-text-primary)',
            fontSize: '16px',
            fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          ⌨️ ABHA ID दर्ज करें
        </button>

        <button
          onClick={() => { setMode('qr'); setError(null); handleStartCamera(); }}
          style={{
            padding: '16px',
            borderRadius: '12px',
            border: '2px solid',
            borderColor: mode === 'qr' ? 'var(--color-blue-info)' : 'rgba(255,255,255,0.1)',
            background: mode === 'qr' ? 'rgba(59, 130, 246, 0.15)' : 'var(--color-surface-secondary)',
            color: 'var(--color-text-primary)',
            fontSize: '16px',
            fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          📷 QR कोड स्कैन करें
        </button>

        <button
          onClick={() => { setMode('aadhaar'); setError(null); }}
          style={{
            padding: '16px',
            borderRadius: '12px',
            border: '2px solid',
            borderColor: mode === 'aadhaar' ? 'var(--color-amber-warning)' : 'rgba(255,255,255,0.1)',
            background: mode === 'aadhaar' ? 'rgba(245, 158, 11, 0.15)' : 'var(--color-surface-secondary)',
            color: 'var(--color-text-primary)',
            fontSize: '16px',
            fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          🆔 ABHA नहीं है (Aadhaar)
        </button>
      </div>

      {/* Error Alert Display */}
      {error && (
        <div style={{
          padding: '16px 20px',
          background: 'rgba(220, 38, 38, 0.15)',
          border: '1px solid var(--color-red-flag)',
          borderRadius: '12px',
          color: '#FCA5A5',
          fontSize: '16px',
          fontWeight: 600,
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
        }}>
          <span>⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {/* TAB 1: Type ABHA ID */}
      {mode === 'type' && (
        <KioskCard padding="28px">
          <label style={{ display: 'block', fontSize: '16px', fontWeight: 600, marginBottom: '10px' }}>
            14-अंकीय आभा संख्या अथवा पता दर्ज करें:
          </label>
          <div style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
            <input
              type="text"
              value={abhaInput}
              onChange={(e) => setAbhaInput(formatAbhaInput(e.target.value))}
              placeholder="e.g. 91-1024-5829-1482 or rajesh.kumar@abdm"
              style={{
                flex: 1,
                padding: '16px 20px',
                fontSize: '20px',
                fontFamily: 'monospace',
                background: 'var(--color-surface-primary)',
                border: '2px solid var(--color-border-subtle)',
                borderRadius: '12px',
                color: 'var(--color-text-primary)',
                outline: 'none',
              }}
            />
            <KioskButton
              variant="primary"
              size="large"
              loading={isLoading}
              onClick={handleAbhaSubmit}
              disabled={!abhaInput.trim()}
            >
              सत्यापित करें (Verify)
            </KioskButton>
          </div>

          {/* Quick Test Patients */}
          <div style={{ marginTop: '16px' }}>
            <span style={{ fontSize: '13px', color: 'var(--color-text-muted)', fontWeight: 600 }}>
              SANDBOX TEST ACCOUNTS:
            </span>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '8px' }}>
              {quickTestAbhas.map((item) => (
                <button
                  key={item.id}
                  onClick={() => { setAbhaInput(item.id); setError(null); }}
                  style={{
                    padding: '8px 12px',
                    borderRadius: '8px',
                    background: 'rgba(255,255,255,0.06)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    color: 'var(--color-blue-info)',
                    fontSize: '13px',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>
        </KioskCard>
      )}

      {/* TAB 2: QR Camera Scanner */}
      {mode === 'qr' && (
        <KioskCard padding="28px" style={{ textAlign: 'center' }}>
          <div style={{
            position: 'relative',
            width: '100%',
            maxWidth: '420px',
            height: '280px',
            margin: '0 auto 20px auto',
            background: '#000',
            borderRadius: '16px',
            overflow: 'hidden',
            border: '2px dashed var(--color-blue-info)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <video
              ref={videoRef}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              playsInline
              muted
            />
            <div style={{
              position: 'absolute',
              width: '180px',
              height: '180px',
              border: '2px solid rgba(255,255,255,0.5)',
              borderRadius: '12px',
              boxShadow: '0 0 0 9999px rgba(0,0,0,0.4)',
            }} />
          </div>

          <p style={{ fontSize: '16px', color: 'var(--color-text-secondary)', marginBottom: '16px' }}>
            अपने आयुष्मान / ABHA कार्ड का QR कोड कैमरा के सामने रखें
          </p>

          <KioskButton
            variant="secondary"
            size="md"
            loading={isLoading}
            onClick={() => handleSimulateQrScan('rajesh.kumar@abdm')}
          >
            🔍 सिमुलेटेड ABHA QR स्कैन करें (Instant Detect)
          </KioskButton>
        </KioskCard>
      )}

      {/* TAB 3: Aadhaar OTP Fallback */}
      {mode === 'aadhaar' && (
        <KioskCard padding="28px">
          <div style={{
            padding: '8px 14px',
            borderRadius: '8px',
            background: 'rgba(245, 158, 11, 0.15)',
            border: '1px solid var(--color-amber-warning)',
            color: 'var(--color-amber-warning)',
            fontSize: '14px',
            fontWeight: 700,
            marginBottom: '16px',
            display: 'inline-block',
          }}>
            ⚠️ Session created without ABHA linkage
          </div>

          {!isOtpSent ? (
            <div>
              <label style={{ display: 'block', fontSize: '16px', fontWeight: 600, marginBottom: '10px' }}>
                अपना 12-अंकीय आधार नंबर दर्ज करें:
              </label>
              <div style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
                <input
                  type="text"
                  value={aadhaarInput}
                  onChange={(e) => setAadhaarInput(formatAadhaarInput(e.target.value))}
                  placeholder="XXXX XXXX XXXX"
                  style={{
                    flex: 1,
                    padding: '16px 20px',
                    fontSize: '20px',
                    fontFamily: 'monospace',
                    background: 'var(--color-surface-primary)',
                    border: '2px solid var(--color-border-subtle)',
                    borderRadius: '12px',
                    color: 'var(--color-text-primary)',
                    outline: 'none',
                  }}
                />
                <KioskButton
                  variant="primary"
                  size="large"
                  loading={isLoading}
                  onClick={handleRequestAadhaarOtp}
                  disabled={aadhaarInput.replace(/\s+/g, '').length !== 12}
                >
                  ओटीपी भेजें (Send OTP)
                </KioskButton>
              </div>
            </div>
          ) : (
            <div>
              <label style={{ display: 'block', fontSize: '16px', fontWeight: 600, marginBottom: '10px' }}>
                मोबाइल पर प्राप्त 6-अंकीय ओटीपी दर्ज करें:
              </label>
              <div style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
                <input
                  type="text"
                  value={otpInput}
                  onChange={(e) => setOtpInput(e.target.value.slice(0, 6))}
                  placeholder="123456"
                  style={{
                    flex: 1,
                    padding: '16px 20px',
                    fontSize: '24px',
                    letterSpacing: '8px',
                    textAlign: 'center',
                    fontFamily: 'monospace',
                    background: 'var(--color-surface-primary)',
                    border: '2px solid var(--color-border-subtle)',
                    borderRadius: '12px',
                    color: 'var(--color-text-primary)',
                    outline: 'none',
                  }}
                />
                <KioskButton
                  variant="primary"
                  size="large"
                  loading={isLoading}
                  onClick={handleVerifyAadhaarOtp}
                  disabled={otpInput.length < 6}
                >
                  पुष्टि करें (Verify OTP)
                </KioskButton>
              </div>
              <small style={{ color: 'var(--color-text-muted)', fontSize: '13px' }}>
                * सैंडबॉक्स डिफ़ॉल्ट कोड <strong>123456</strong> है।
              </small>
            </div>
          )}
        </KioskCard>
      )}

      {/* Virtual Keypad for Touch Displays */}
      {(mode === 'type' || mode === 'aadhaar') && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '10px',
          maxWidth: '420px',
          margin: '0 auto',
          width: '100%',
        }}>
          {['1', '2', '3', '4', '5', '6', '7', '8', '9', 'CLR', '0', 'BACK'].map((key) => (
            <button
              key={key}
              onClick={() => handleKeypadPress(key)}
              style={{
                height: '56px',
                borderRadius: '12px',
                background: 'var(--color-surface-secondary)',
                border: '1px solid rgba(255,255,255,0.1)',
                color: 'var(--color-text-primary)',
                fontSize: key === 'CLR' || key === 'BACK' ? '16px' : '22px',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              {key === 'BACK' ? '⌫' : key}
            </button>
          ))}
        </div>
      )}

      {/* Demographics Confirmation Modal: "Is this you? [Name, DOB, Gender] -> Yes/No" */}
      {pendingDemographics && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(15, 23, 42, 0.85)',
          backdropFilter: 'blur(10px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '20px',
        }}>
          <KioskCard
            padding="36px"
            style={{
              width: '100%',
              maxWidth: '540px',
              border: '2px solid var(--color-blue-info)',
            }}
          >
            <span style={{
              fontSize: '14px',
              fontWeight: 700,
              color: 'var(--color-blue-info)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}>
              पहचान सत्यापन / Confirmation
            </span>
            <h2 style={{ fontSize: '26px', fontWeight: 800, marginTop: '6px', marginBottom: '20px' }}>
              क्या यह विवरण आपका है? (Is this you?)
            </h2>

            <div style={{
              background: 'var(--color-surface-primary)',
              borderRadius: '12px',
              padding: '20px',
              marginBottom: '24px',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--color-text-secondary)' }}>नाम (Name):</span>
                <strong style={{ fontSize: '18px' }}>{pendingDemographics.name}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--color-text-secondary)' }}>जन्म तिथि (DOB):</span>
                <strong>{pendingDemographics.dob || '1980-01-01'}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--color-text-secondary)' }}>लिंग (Gender):</span>
                <strong>{pendingDemographics.gender === 'M' ? 'पुरुष (Male)' : pendingDemographics.gender === 'F' ? 'महिला (Female)' : 'अन्य (Other)'}</strong>
              </div>
              {pendingDemographics.abha_number && (
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--color-text-secondary)' }}>ABHA Number:</span>
                  <span style={{ fontFamily: 'monospace' }}>{pendingDemographics.abha_number}</span>
                </div>
              )}
              {pendingDemographics.label && (
                <div style={{
                  marginTop: '8px',
                  padding: '6px 10px',
                  borderRadius: '6px',
                  background: 'rgba(245, 158, 11, 0.2)',
                  color: 'var(--color-amber-warning)',
                  fontSize: '13px',
                  fontWeight: 700,
                }}>
                  {pendingDemographics.label}
                </div>
              )}
            </div>

            <div style={{ display: 'flex', gap: '16px' }}>
              <KioskButton
                variant="outline"
                size="large"
                style={{ flex: 1 }}
                onClick={() => setPendingDemographics(null)}
              >
                नहीं (No, Re-enter)
              </KioskButton>
              <KioskButton
                variant="primary"
                size="large"
                style={{ flex: 1.5 }}
                onClick={() => confirmIdentity(pendingDemographics)}
              >
                हाँ, यह मैं हूँ (Yes, Continue) →
              </KioskButton>
            </div>
          </KioskCard>
        </div>
      )}
    </div>
  );
};

export default IdentityScreen;
