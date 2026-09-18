import React, { useState, useRef, useEffect } from 'react';
import KioskCard from './KioskCard';
import KioskButton from './KioskButton';
import { useSession } from '../../contexts/SessionContext';
import {
  QrCode,
  Fingerprint,
  Keyboard,
  UserPlus,
  Camera,
  CheckCircle2,
  XCircle,
  ArrowLeft,
  Search,
  Send,
  User,
  CreditCard,
  Eye,
  EyeOff,
  ShieldCheck,
  AlertCircle,
  Delete,
  RotateCcw,
} from 'lucide-react';

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

/**
 * Mask sensitive string for queue privacy
 */
function maskString(val, visibleCount = 4) {
  if (!val) return '';
  if (val.length <= visibleCount) return val;
  const visible = val.slice(-visibleCount);
  const maskedLength = Math.max(0, val.length - visibleCount);
  return '•'.repeat(maskedLength) + visible;
}

const IDENTITY_TEXT = {
  en: {
    backBtn: 'Change Language',
    stepBadge: 'Step 2 / 3 · Identity Verification',
    title: 'Patient Identification',
    subtitle: 'Scan Ayushman (ABHA) QR card, verify via Aadhaar OTP, or register as a walk-in patient',
    consentNoticeTitle: 'Regulatory ABDM & DISHA Consent:',
    consentNoticeDesc: 'Details scanned or entered at this kiosk are used solely for today\'s OPD consultation and health records access. No data is stored permanently without your explicit consent.',
    tabQr: '1. Scan QR Card',
    tabQrSpeed: '⚡ Fastest',
    tabAadhaar: '2. Aadhaar OTP',
    tabAadhaarSub: 'Via Mobile OTP',
    tabAbha: '3. ABHA ID',
    tabAbhaSub: '14-digit or address',
    tabManual: '4. Without ABHA',
    tabManualSub: 'New Walk-In',
    qrPrompt: 'Place your Ayushman / ABHA Card QR in front of the camera',
    qrScanBtn: 'Scan Simulated ABHA QR (Instant Detect)',
    qrSub: 'Auto-scans instant QR badge',
    aadhaarLabel: 'Enter your 12-digit Aadhaar Number:',
    masked: 'Number is masked',
    visible: 'Visible',
    sendOtpBtn: 'Send OTP',
    sendOtpSub: 'Send verification code',
    otpLabel: 'Enter the 6-digit OTP received on mobile:',
    verifyOtpBtn: 'Verify OTP',
    verifyOtpSub: 'Confirm patient',
    abhaLabel: 'Enter 14-digit ABHA Number or Address:',
    verifyAbhaBtn: 'Verify ABHA',
    verifyAbhaSub: 'Check records',
    staffSandbox: '🛠️ STAFF SANDBOX TEST PATIENTS:',
    manualNotice: 'If you do not have an ABHA or Aadhaar, enter your details to proceed directly to the doctor.',
    manualNameLabel: 'Patient Full Name *',
    manualNamePlaceholder: 'e.g. Ramesh Kumar',
    manualAgeLabel: 'Age:',
    years: 'Years',
    manualGenderLabel: 'Gender:',
    genderMale: 'Male',
    genderFemale: 'Female',
    genderOther: 'Other',
    manualPhoneLabel: 'Mobile Number (for prescription SMS):',
    manualPhonePlaceholder: '10-digit mobile number',
    manualAbhaCheckbox: 'Yes, create a free digital Ayushman (ABHA) account for me (Recommended)',
    manualSubmitBtn: 'Register & Proceed to Doctor (Continue) →',
    manualSubmitSub: 'Proceed directly to clinical interview',
    keyClear: 'Clear',
    keyBack: 'Back',
    modalBadge: 'Verified Patient Profile',
    modalTitle: 'Is this information correct?',
    modalName: 'Name:',
    modalAge: 'Age / DOB:',
    modalGender: 'Gender:',
    modalMobile: 'Mobile:',
    modalAbha: 'ABHA Number:',
    modalNo: 'No (Re-enter)',
    modalYes: 'Yes, Continue',
    modalYesSub: 'Proceed to consent',
  },
  hi: {
    backBtn: 'भाषा बदलें (Change Language)',
    stepBadge: 'कदम 2 / 3 · पहचान (Identity Verification)',
    title: 'अपनी पहचान दर्ज करें (Patient Identification)',
    subtitle: 'आयुष्मान कार्ड (ABHA) QR स्कैन करें, आधार द्वारा लिंक करें अथवा बिना ABHA नया पंजीकरण करें',
    consentNoticeTitle: 'सत्यापन पूर्व सहमति (ABDM & DISHA Regulatory Consent):',
    consentNoticeDesc: 'इस कियोस्क पर स्कैन अथवा दर्ज किया गया विवरण केवल आज के ओपीडी परामर्श व स्वास्थ्य रिकॉर्ड प्राप्ति हेतु प्रयोग किया जाएगा। आपकी स्पष्ट अनुमति के बिना कोई भी डेटा सुरक्षित नहीं किया जाएगा।',
    tabQr: '1. QR कोड स्कैन',
    tabQrSpeed: '⚡ सबसे तेज (Fastest)',
    tabAadhaar: '2. आधार (Aadhaar)',
    tabAadhaarSub: 'ओटीपी द्वारा',
    tabAbha: '3. ABHA संख्या',
    tabAbhaSub: '14 अंक / पता',
    tabManual: '4. बिना ABHA',
    tabManualSub: 'नया पंजीकरण (Walk-In)',
    qrPrompt: 'अपने आयुष्मान (ABHA) कार्ड का QR कोड कैमरा के सामने रखें',
    qrScanBtn: 'सिमुलेटेड ABHA QR स्कैन करें (Instant Detect)',
    qrSub: 'Auto-scans instant QR badge',
    aadhaarLabel: 'अपना 12-अंकीय आधार नंबर दर्ज करें:',
    masked: 'नंबर छुपा हुआ है',
    visible: 'दिखाएं',
    sendOtpBtn: 'ओटीपी भेजें (Send OTP)',
    sendOtpSub: 'Send verification code',
    otpLabel: 'मोबाइल पर प्राप्त 6-अंकीय ओटीपी दर्ज करें:',
    verifyOtpBtn: 'पुष्टि करें (Verify OTP)',
    verifyOtpSub: 'Confirm patient',
    abhaLabel: '14-अंकीय आभा संख्या अथवा पता दर्ज करें:',
    verifyAbhaBtn: 'सत्यापित करें (Verify)',
    verifyAbhaSub: 'Check records',
    staffSandbox: '🛠️ STAFF SANDBOX TEST PATIENTS:',
    manualNotice: 'यदि आपके पास आयुष्मान (ABHA) या आधार नहीं है, तो अपना नाम व विवरण दर्ज कर सीधे डॉक्टर से मिलें।',
    manualNameLabel: 'मरीज का पूरा नाम (Full Name) *',
    manualNamePlaceholder: 'उदा. रमेश कुमार / Ramesh Kumar',
    manualAgeLabel: 'आयु / Age:',
    years: 'वर्ष',
    manualGenderLabel: 'लिंग / Gender:',
    genderMale: 'पुरुष (Male)',
    genderFemale: 'महिला (Female)',
    genderOther: 'अन्य (Other)',
    manualPhoneLabel: 'मोबाइल नंबर (Mobile Number) - पर्ची संदेश हेतु:',
    manualPhonePlaceholder: '10-अंकीय मोबाइल नंबर',
    manualAbhaCheckbox: 'हाँ, मेरे लिए निःशुल्क डिजिटल आयुष्मान (ABHA) खाता भी तैयार करें (Recommended)',
    manualSubmitBtn: 'पंजीकरण करें एवं डॉक्टर से मिलें (Continue) →',
    manualSubmitSub: 'Proceed directly to clinical interview',
    keyClear: 'साफ',
    keyBack: 'हटाएं',
    modalBadge: 'सत्यापित मरीज प्रोफाइल / Verified Patient',
    modalTitle: 'क्या यह विवरण आपका है? (Is this you?)',
    modalName: 'नाम (Name):',
    modalAge: 'आयु / जन्म (Age):',
    modalGender: 'लिंग (Gender):',
    modalMobile: 'मोबाइल (Mobile):',
    modalAbha: 'ABHA Number:',
    modalNo: 'नहीं (No)',
    modalYes: 'हाँ, यह मैं हूँ (Yes, Continue)',
    modalYesSub: 'Proceed to consent',
  },
  pa: {
    backBtn: 'ਭਾਸ਼ਾ ਬਦਲੋ (Change Language)',
    stepBadge: 'ਕਦਮ 2 / 3 · ਪਛਾਣ (Identity Verification)',
    title: 'ਆਪਣੀ ਪਛਾਣ ਦਰਜ ਕਰੋ (Patient Identification)',
    subtitle: 'ਆਯੁਸ਼ਮਾਨ ਕਾਰਡ (ABHA) QR ਸਕੈਨ ਕਰੋ, ਆਧਾਰ ਰਾਹੀਂ ਲਿੰਕ ਕਰੋ ਜਾਂ ਬਿਨਾਂ ABHA ਨਵਾਂ ਰਜਿਸਟ੍ਰੇਸ਼ਨ ਕਰੋ',
    consentNoticeTitle: 'ਸਹਿਮਤੀ ਨੋਟਿਸ (ABDM & DISHA Regulatory Consent):',
    consentNoticeDesc: 'ਇਸ ਕਿਓਸਕ ਤੇ ਸਕੈਨ ਜਾਂ ਦਰਜ ਕੀਤਾ ਗਿਆ ਵੇਰਵਾ ਸਿਰਫ਼ ਅੱਜ ਦੀ ਓਪੀਡੀ ਸਲਾਹ ਲਈ ਵਰਤਿਆ ਜਾਵੇਗਾ। ਤੁਹਾਡੀ ਇਜਾਜ਼ਤ ਤੋਂ ਬਿਨਾਂ ਕੋਈ ਵੀ ਡਾਟਾ ਸੁਰੱਖਿਅਤ ਨਹੀਂ ਕੀਤਾ ਜਾਵੇਗਾ।',
    tabQr: '1. QR ਕੋਡ ਸਕੈਨ',
    tabQrSpeed: '⚡ ਸਭ ਤੋਂ ਤੇਜ਼ (Fastest)',
    tabAadhaar: '2. ਆਧਾਰ (Aadhaar)',
    tabAadhaarSub: 'ਓਟੀਪੀ ਰਾਹੀਂ',
    tabAbha: '3. ABHA ਨੰਬਰ',
    tabAbhaSub: '14 ਅੰਕ / ਪਤਾ',
    tabManual: '4. ਬਿਨਾਂ ABHA',
    tabManualSub: 'ਨਵਾਂ ਰਜਿਸਟ੍ਰੇਸ਼ਨ (Walk-In)',
    qrPrompt: 'ਆਪਣੇ ਆਯੁਸ਼ਮਾਨ (ABHA) ਕਾਰਡ ਦਾ QR ਕੋਡ ਕੈਮਰੇ ਸਾਹਮਣੇ ਰੱਖੋ',
    qrScanBtn: 'ਸਿਮੂਲੇਟਡ ABHA QR ਸਕੈਨ ਕਰੋ (Instant Detect)',
    qrSub: 'Auto-scans instant QR badge',
    aadhaarLabel: 'ਆਪਣਾ 12-ਅੰਕੀ ਆਧਾਰ ਨੰਬਰ ਦਰਜ ਕਰੋ:',
    masked: 'ਨੰਬਰ ਲੁਕਿਆ ਹੋਇਆ ਹੈ',
    visible: 'ਦਿਖਾਓ',
    sendOtpBtn: 'ਓਟੀਪੀ ਭੇਜੋ (Send OTP)',
    sendOtpSub: 'Send verification code',
    otpLabel: 'ਮੋਬਾਈਲ ਤੇ ਆਇਆ 6-ਅੰਕੀ ਓਟੀਪੀ ਦਰਜ ਕਰੋ:',
    verifyOtpBtn: 'ਪੁਸ਼ਟੀ ਕਰੋ (Verify OTP)',
    verifyOtpSub: 'Confirm patient',
    abhaLabel: '14-ਅੰਕੀ ਆਭਾ ਨੰਬਰ ਜਾਂ ਪਤਾ ਦਰਜ ਕਰੋ:',
    verifyAbhaBtn: 'ਸਤਿਆਪਿਤ ਕਰੋ (Verify)',
    verifyAbhaSub: 'Check records',
    staffSandbox: '🛠️ STAFF SANDBOX TEST PATIENTS:',
    manualNotice: 'ਜੇਕਰ ਤੁਹਾਡੇ ਕੋਲ ਆਯੁਸ਼ਮਾਨ (ABHA) ਜਾਂ ਆਧਾਰ ਨਹੀਂ ਹੈ, ਤਾਂ ਆਪਣਾ ਨਾਮ ਦਰਜ ਕਰਕੇ ਸਿੱਧੇ ਡਾਕਟਰ ਨੂੰ ਮਿਲੋ।',
    manualNameLabel: 'ਮਰੀਜ਼ ਦਾ ਪੂਰਾ ਨਾਮ (Full Name) *',
    manualNamePlaceholder: 'ਜਿਵੇਂ ਕਿ ਰਮੇਸ਼ ਕੁਮਾਰ / Ramesh Kumar',
    manualAgeLabel: 'ਉਮਰ / Age:',
    years: 'ਸਾਲ',
    manualGenderLabel: 'ਲਿੰਗ / Gender:',
    genderMale: 'ਪੁਰਸ਼ (Male)',
    genderFemale: 'ਮਹਿਲਾ (Female)',
    genderOther: 'ਹੋਰ (Other)',
    manualPhoneLabel: 'ਮੋਬਾਈਲ ਨੰਬਰ (Mobile Number) - ਪਰਚੀ ਸੰਦੇਸ਼ ਲਈ:',
    manualPhonePlaceholder: '10-ਅੰਕੀ ਮੋਬਾਈਲ ਨੰਬਰ',
    manualAbhaCheckbox: 'ਹਾਂ, ਮੇਰੇ ਲਈ ਮੁਫ਼ਤ ਡਿਜੀਟਲ ਆਯੁਸ਼ਮਾਨ (ABHA) ਖਾਤਾ ਤਿਆਰ ਕਰੋ (Recommended)',
    manualSubmitBtn: 'ਰਜਿਸਟਰ ਕਰੋ ਅਤੇ ਡਾਕਟਰ ਨੂੰ ਮਿਲੋ (Continue) →',
    manualSubmitSub: 'Proceed directly to clinical interview',
    keyClear: 'ਸਾਫ਼',
    keyBack: 'ਹਟਾਓ',
    modalBadge: 'ਸਤਿਆਪਿਤ ਮਰੀਜ਼ ਪ੍ਰੋਫਾਈਲ / Verified Patient',
    modalTitle: 'ਕੀ ਇਹ ਵੇਰਵਾ ਤੁਹਾਡਾ ਹੈ? (Is this you?)',
    modalName: 'ਨਾਮ (Name):',
    modalAge: 'ਉਮਰ / ਜਨਮ (Age):',
    modalGender: 'ਲਿੰਗ (Gender):',
    modalMobile: 'ਮੋਬਾਈਲ (Mobile):',
    modalAbha: 'ABHA Number:',
    modalNo: 'ਨਹੀਂ (No)',
    modalYes: 'ਹਾਂ, ਇਹ ਮੈਂ ਹਾਂ (Yes, Continue)',
    modalYesSub: 'Proceed to consent',
  },
};

export const IdentityScreen = ({ onBack }) => {
  const {
    language,
    verifyAbha,
    requestAadhaarOtp,
    verifyAadhaarOtp,
    registerManualPatient,
    confirmIdentity,
    isLoading,
    error,
    setError,
    isStaffMode,
  } = useSession();

  const t = IDENTITY_TEXT[language] || IDENTITY_TEXT.hi;

  // QR-First Hierarchy: default tab is 'qr' (fastest & least error-prone)
  const [mode, setMode] = useState('qr'); // 'qr' | 'aadhaar' | 'type' | 'manual'
  const [abhaInput, setAbhaInput] = useState('');
  const [aadhaarInput, setAadhaarInput] = useState('');
  const [otpInput, setOtpInput] = useState('');
  const [activeTxnId, setActiveTxnId] = useState(null);
  const [isOtpSent, setIsOtpSent] = useState(false);
  const [pendingDemographics, setPendingDemographics] = useState(null);
  const [isCameraActive, setIsCameraActive] = useState(false);

  // Queue Privacy: Show/Hide masked state
  const [isMasked, setIsMasked] = useState(true);

  // Manual Walk-In Registration State
  const [manualName, setManualName] = useState('');
  const [manualAge, setManualAge] = useState('32');
  const [manualGender, setManualGender] = useState('M');
  const [manualPhone, setManualPhone] = useState('');
  const [manualCreateAbha, setManualCreateAbha] = useState(true);

  const videoRef = useRef(null);

  // Quick helper sample ABHA IDs for sandbox (gated to staff/dev mode)
  const quickTestAbhas = [
    { label: 'राजेश कुमार (Rajesh Kumar)', id: 'rajesh.kumar@abdm', sub: 'Known Rx & CBC records' },
    { label: 'सुनीता देवी (Sunita Devi)', id: '91-1024-5829-1482', sub: '14-digit format' },
    { label: 'अमित शर्मा (Amit Sharma)', id: 'amit.sharma@abdm', sub: 'General OPD visit' },
  ];

  // Camera stream setup for default QR mode
  useEffect(() => {
    if (mode === 'qr') {
      handleStartCamera();
    }
    return () => {
      if (videoRef.current && videoRef.current.srcObject) {
        const stream = videoRef.current.srcObject;
        stream.getTracks().forEach((t) => t.stop());
      }
    };
  }, [mode]);

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
      console.warn('Camera access notice:', err);
    }
  };

  const handleSimulateQrScan = async (scannedId = 'rajesh.kumar@abdm') => {
    try {
      const demo = await verifyAbha(scannedId);
      setPendingDemographics(demo);
    } catch (err) {}
  };

  const handleAbhaSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!abhaInput.trim()) {
      setError(language === 'en' ? 'Please enter your 14-digit ABHA ID or address' : 'कृपया अपनी 14-अंकीय आभा संख्या अथवा पता दर्ज करें');
      return;
    }
    try {
      const demo = await verifyAbha(abhaInput.trim());
      setPendingDemographics(demo);
    } catch (err) {}
  };

  const handleRequestAadhaarOtp = async (e) => {
    if (e) e.preventDefault();
    const cleanAadhaar = aadhaarInput.replace(/\s+/g, '');
    if (cleanAadhaar.length !== 12) {
      setError(language === 'en' ? 'Aadhaar number must be exactly 12 digits' : 'आधार संख्या ठीक 12 अंकों की होनी चाहिए');
      return;
    }
    try {
      const res = await requestAadhaarOtp(cleanAadhaar);
      setActiveTxnId(res.txn_id);
      setIsOtpSent(true);
      setOtpInput('123456'); // Pre-fill sandbox default OTP
    } catch (err) {}
  };

  const handleVerifyAadhaarOtp = async (e) => {
    if (e) e.preventDefault();
    if (!otpInput.trim()) {
      setError(language === 'en' ? 'Please enter 6-digit OTP' : 'कृपया 6-अंकीय ओटीपी दर्ज करें');
      return;
    }
    try {
      const tempPatient = await verifyAadhaarOtp(activeTxnId, otpInput.trim(), aadhaarInput);
      setPendingDemographics(tempPatient);
    } catch (err) {}
  };

  const handleManualSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!manualName.trim()) {
      setError(language === 'en' ? 'Please enter patient name' : 'कृपया मरीज का नाम दर्ज करें');
      return;
    }
    try {
      const profile = await registerManualPatient({
        name: manualName.trim(),
        age: manualAge,
        gender: manualGender,
        phone: manualPhone,
        createAbha: manualCreateAbha,
      });
      if (profile) {
        setPendingDemographics(profile);
      }
    } catch (err) {}
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
    } else if (mode === 'manual') {
      if (val === 'BACK') setManualPhone((prev) => prev.slice(0, -1));
      else if (val === 'CLR') setManualPhone('');
      else if (manualPhone.length < 10) setManualPhone((prev) => prev + val);
    }
  };

  return (
    <div
      style={{
        width: '100%',
        maxWidth: '920px',
        margin: '0 auto',
        padding: '24px 20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
      }}
    >
      {/* Top Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <KioskButton
          variant="secondary"
          size="sm"
          icon={<ArrowLeft size={20} />}
          onClick={onBack}
        >
          {t.backBtn}
        </KioskButton>

        <span
          style={{
            fontSize: '14px',
            fontWeight: 800,
            color: '#0284C7',
            background: '#F0F9FF',
            padding: '6px 14px',
            borderRadius: '999px',
            border: '1.5px solid #BAE6FD',
            letterSpacing: '0.02em',
          }}
        >
          {t.stepBadge}
        </span>
      </div>

      {/* Screen Title */}
      <div>
        <h1
          style={{
            fontSize: '32px',
            fontWeight: 800,
            color: '#0F172A',
            letterSpacing: '-0.02em',
            margin: '0 0 6px 0',
          }}
        >
          {t.title}
        </h1>
        <p style={{ fontSize: '17px', color: '#334155', margin: 0 }}>
          {t.subtitle}
        </p>
      </div>

      {/* Pre-Verification Regulatory Consent Notice (ABDM & DISHA) */}
      <div
        style={{
          padding: '14px 18px',
          borderRadius: '12px',
          background: '#F0FDF4',
          border: '1.5px solid #A7F3D0',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          fontSize: '14px',
          color: '#065F46',
          lineHeight: 1.4,
        }}
      >
        <ShieldCheck size={24} color="#059669" style={{ flexShrink: 0 }} />
        <div>
          <strong>{t.consentNoticeTitle}</strong> {t.consentNoticeDesc}
        </div>
      </div>

      {/* Reordered Tabs by Speed & Least Friction (QR First -> Aadhaar -> ABHA -> Manual) */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '10px',
        }}
      >
        {/* Tab 1: QR (Default, Fastest, Zero Literacy) */}
        <button
          type="button"
          onClick={() => {
            setMode('qr');
            setError(null);
          }}
          style={{
            padding: '16px 10px',
            borderRadius: '14px',
            border: '3px solid',
            borderColor: mode === 'qr' ? '#059669' : '#CBD5E1',
            background: mode === 'qr' ? '#ECFDF5' : '#FFFFFF',
            color: mode === 'qr' ? '#065F46' : '#0F172A',
            fontSize: '15px',
            fontWeight: 800,
            cursor: 'pointer',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '6px',
            boxShadow: '0 2px 6px rgba(15, 23, 42, 0.04)',
            transition: 'all 0.15s ease',
          }}
        >
          <QrCode size={26} color={mode === 'qr' ? '#059669' : '#475569'} />
          <span>{t.tabQr}</span>
          <span style={{ fontSize: '11px', color: '#059669', fontWeight: 800 }}>{t.tabQrSpeed}</span>
        </button>

        {/* Tab 2: Aadhaar OTP */}
        <button
          type="button"
          onClick={() => {
            setMode('aadhaar');
            setError(null);
          }}
          style={{
            padding: '16px 10px',
            borderRadius: '14px',
            border: '3px solid',
            borderColor: mode === 'aadhaar' ? '#D97706' : '#CBD5E1',
            background: mode === 'aadhaar' ? '#FFFBEB' : '#FFFFFF',
            color: mode === 'aadhaar' ? '#92400E' : '#0F172A',
            fontSize: '15px',
            fontWeight: 800,
            cursor: 'pointer',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '6px',
            boxShadow: '0 2px 6px rgba(15, 23, 42, 0.04)',
            transition: 'all 0.15s ease',
          }}
        >
          <Fingerprint size={26} color={mode === 'aadhaar' ? '#D97706' : '#475569'} />
          <span>{t.tabAadhaar}</span>
          <span style={{ fontSize: '11px', color: '#D97706', fontWeight: 800 }}>{t.tabAadhaarSub}</span>
        </button>

        {/* Tab 3: ABHA ID Typing */}
        <button
          type="button"
          onClick={() => {
            setMode('type');
            setError(null);
          }}
          style={{
            padding: '16px 10px',
            borderRadius: '14px',
            border: '3px solid',
            borderColor: mode === 'type' ? '#059669' : '#CBD5E1',
            background: mode === 'type' ? '#ECFDF5' : '#FFFFFF',
            color: mode === 'type' ? '#065F46' : '#0F172A',
            fontSize: '15px',
            fontWeight: 800,
            cursor: 'pointer',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '6px',
            boxShadow: '0 2px 6px rgba(15, 23, 42, 0.04)',
            transition: 'all 0.15s ease',
          }}
        >
          <Keyboard size={26} color={mode === 'type' ? '#059669' : '#475569'} />
          <span>{t.tabAbha}</span>
          <span style={{ fontSize: '11px', color: '#64748B' }}>{t.tabAbhaSub}</span>
        </button>

        {/* Tab 4: Manual Walk-In (No ABHA Route) */}
        <button
          type="button"
          onClick={() => {
            setMode('manual');
            setError(null);
          }}
          style={{
            padding: '16px 10px',
            borderRadius: '14px',
            border: '3px solid',
            borderColor: mode === 'manual' ? '#0284C7' : '#CBD5E1',
            background: mode === 'manual' ? '#F0F9FF' : '#FFFFFF',
            color: mode === 'manual' ? '#0369A1' : '#0F172A',
            fontSize: '15px',
            fontWeight: 800,
            cursor: 'pointer',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '6px',
            boxShadow: '0 2px 6px rgba(15, 23, 42, 0.04)',
            transition: 'all 0.15s ease',
          }}
        >
          <UserPlus size={26} color={mode === 'manual' ? '#0284C7' : '#475569'} />
          <span>{t.tabManual}</span>
          <span style={{ fontSize: '11px', color: '#0284C7', fontWeight: 800 }}>{t.tabManualSub}</span>
        </button>
      </div>

      {/* Error Alert Display */}
      {error && (
        <div
          style={{
            padding: '16px 20px',
            background: '#FEF2F2',
            border: '2px solid #EF4444',
            borderRadius: '14px',
            color: '#991B1B',
            fontSize: '16px',
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
          }}
        >
          <AlertCircle size={24} color="#DC2626" />
          <span>{error}</span>
        </div>
      )}

      {/* TAB 1: QR Camera Scanner (Default) */}
      {mode === 'qr' && (
        <KioskCard padding="32px" style={{ textAlign: 'center' }}>
          <div
            style={{
              position: 'relative',
              width: '100%',
              maxWidth: '440px',
              height: '280px',
              margin: '0 auto 20px auto',
              background: '#0F172A',
              borderRadius: '16px',
              overflow: 'hidden',
              border: '3px dashed #059669',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <video
              ref={videoRef}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              playsInline
              muted
            />
            <div
              style={{
                position: 'absolute',
                width: '190px',
                height: '190px',
                border: '3px solid #10B981',
                borderRadius: '14px',
                boxShadow: '0 0 0 9999px rgba(15, 23, 42, 0.55)',
              }}
            />
          </div>

          <p style={{ fontSize: '18px', color: '#1E293B', fontWeight: 700, marginBottom: '18px' }}>
            {t.qrPrompt}
          </p>

          <KioskButton
            variant="primary"
            size="lg"
            icon={<Camera size={24} />}
            loading={isLoading}
            onClick={() => handleSimulateQrScan('rajesh.kumar@abdm')}
            sublabel={t.qrSub}
          >
            {t.qrScanBtn}
          </KioskButton>
        </KioskCard>
      )}

      {/* TAB 2: Aadhaar OTP */}
      {mode === 'aadhaar' && (
        <KioskCard padding="32px">
          {!isOtpSent ? (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <label
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    fontSize: '17px',
                    fontWeight: 700,
                    color: '#0F172A',
                  }}
                >
                  <Fingerprint size={20} color="#D97706" />
                  <span>{t.aadhaarLabel}</span>
                </label>

                {/* Queue Privacy Masking Toggle */}
                <button
                  type="button"
                  onClick={() => setIsMasked(!isMasked)}
                  style={{
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    color: '#0284C7',
                    fontSize: '14px',
                    fontWeight: 700,
                  }}
                >
                  {isMasked ? <EyeOff size={18} /> : <Eye size={18} />}
                  <span>{isMasked ? t.masked : t.visible}</span>
                </button>
              </div>

              <div style={{ display: 'flex', gap: '14px', marginBottom: '20px' }}>
                <input
                  type={isMasked ? 'password' : 'text'}
                  value={aadhaarInput}
                  onChange={(e) => setAadhaarInput(formatAadhaarInput(e.target.value))}
                  placeholder="XXXX XXXX XXXX"
                  style={{
                    flex: 1,
                    padding: '18px 22px',
                    fontSize: '22px',
                    fontFamily: 'monospace',
                    background: '#FFFFFF',
                    border: '2.5px solid #CBD5E1',
                    borderRadius: '14px',
                    color: '#0F172A',
                    outline: 'none',
                  }}
                />

                <KioskButton
                  variant="primary"
                  size="lg"
                  icon={<Send size={22} />}
                  loading={isLoading}
                  onClick={handleRequestAadhaarOtp}
                  disabled={aadhaarInput.replace(/\s+/g, '').length !== 12}
                  sublabel={t.sendOtpSub}
                >
                  {t.sendOtpBtn}
                </KioskButton>
              </div>
            </div>
          ) : (
            <div>
              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  fontSize: '17px',
                  fontWeight: 700,
                  marginBottom: '12px',
                  color: '#0F172A',
                }}
              >
                <CheckCircle2 size={20} color="#059669" />
                <span>{t.otpLabel}</span>
              </label>

              <div style={{ display: 'flex', gap: '14px', marginBottom: '20px' }}>
                <input
                  type="text"
                  value={otpInput}
                  onChange={(e) => setOtpInput(e.target.value.slice(0, 6))}
                  placeholder="123456"
                  style={{
                    flex: 1,
                    padding: '18px 22px',
                    fontSize: '26px',
                    letterSpacing: '8px',
                    textAlign: 'center',
                    fontFamily: 'monospace',
                    background: '#FFFFFF',
                    border: '2.5px solid #059669',
                    borderRadius: '14px',
                    color: '#0F172A',
                    outline: 'none',
                  }}
                />

                <KioskButton
                  variant="primary"
                  size="lg"
                  icon={<CheckCircle2 size={24} />}
                  loading={isLoading}
                  onClick={handleVerifyAadhaarOtp}
                  disabled={otpInput.length < 6}
                  sublabel={t.verifyOtpSub}
                >
                  {t.verifyOtpBtn}
                </KioskButton>
              </div>
            </div>
          )}
        </KioskCard>
      )}

      {/* TAB 3: ABHA ID Typing */}
      {mode === 'type' && (
        <KioskCard padding="32px">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <label
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '17px',
                fontWeight: 700,
                color: '#0F172A',
              }}
            >
              <CreditCard size={20} color="#059669" />
              <span>{t.abhaLabel}</span>
            </label>

            {/* Privacy toggle */}
            <button
              type="button"
              onClick={() => setIsMasked(!isMasked)}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                color: '#0284C7',
                fontSize: '14px',
                fontWeight: 700,
              }}
            >
              {isMasked ? <EyeOff size={18} /> : <Eye size={18} />}
              <span>{isMasked ? t.masked : t.visible}</span>
            </button>
          </div>

          <div style={{ display: 'flex', gap: '14px', marginBottom: '20px' }}>
            <input
              type={isMasked ? 'password' : 'text'}
              value={abhaInput}
              onChange={(e) => setAbhaInput(formatAbhaInput(e.target.value))}
              placeholder="e.g. 91-1024-5829-1482 or rajesh.kumar@abdm"
              style={{
                flex: 1,
                padding: '18px 22px',
                fontSize: '22px',
                fontFamily: 'monospace',
                background: '#FFFFFF',
                border: '2.5px solid #CBD5E1',
                borderRadius: '14px',
                color: '#0F172A',
                outline: 'none',
              }}
            />

            <KioskButton
              variant="primary"
              size="lg"
              icon={<Search size={22} />}
              loading={isLoading}
              onClick={handleAbhaSubmit}
              disabled={!abhaInput.trim()}
              sublabel={t.verifyAbhaSub}
            >
              {t.verifyAbhaBtn}
            </KioskButton>
          </div>

          {/* Sandbox Test Patients: Gated strictly to Staff Mode */}
          {isStaffMode && (
            <div
              style={{
                padding: '16px',
                background: '#FFFBEB',
                borderRadius: '12px',
                border: '1.5px solid #F59E0B',
              }}
            >
              <span
                style={{
                  fontSize: '12px',
                  color: '#92400E',
                  fontWeight: 800,
                  textTransform: 'uppercase',
                  display: 'block',
                  marginBottom: '8px',
                }}
              >
                {t.staffSandbox}
              </span>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                {quickTestAbhas.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => {
                      setAbhaInput(item.id);
                      setError(null);
                    }}
                    style={{
                      padding: '8px 12px',
                      borderRadius: '8px',
                      background: '#FFFFFF',
                      border: '1.5px solid #CBD5E1',
                      color: '#0284C7',
                      fontSize: '13px',
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>
          )}
        </KioskCard>
      )}

      {/* TAB 4: Manual Walk-In Registration (No ABHA Path) */}
      {mode === 'manual' && (
        <KioskCard padding="32px">
          <div
            style={{
              padding: '10px 14px',
              borderRadius: '10px',
              background: '#F0F9FF',
              border: '1.5px solid #BAE6FD',
              color: '#0369A1',
              fontSize: '14px',
              fontWeight: 700,
              marginBottom: '20px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <UserPlus size={18} />
            <span>{t.manualNotice}</span>
          </div>

          <form onSubmit={handleManualSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            {/* Patient Name */}
            <div>
              <label style={{ display: 'block', fontSize: '16px', fontWeight: 700, marginBottom: '6px', color: '#0F172A' }}>
                {t.manualNameLabel}
              </label>
              <input
                type="text"
                value={manualName}
                onChange={(e) => setManualName(e.target.value)}
                placeholder={t.manualNamePlaceholder}
                style={{
                  width: '100%',
                  padding: '16px 20px',
                  fontSize: '18px',
                  borderRadius: '12px',
                  border: '2px solid #CBD5E1',
                  background: '#FFFFFF',
                  color: '#0F172A',
                }}
              />
            </div>

            {/* Age Selection with Quick Chips */}
            <div>
              <label style={{ display: 'block', fontSize: '16px', fontWeight: 700, marginBottom: '6px', color: '#0F172A' }}>
                {t.manualAgeLabel} <strong>{manualAge} {t.years}</strong>
              </label>
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                {['18', '25', '35', '45', '55', '65', '75'].map((ageOption) => (
                  <button
                    key={ageOption}
                    type="button"
                    onClick={() => setManualAge(ageOption)}
                    style={{
                      padding: '10px 18px',
                      borderRadius: '10px',
                      background: manualAge === ageOption ? '#ECFDF5' : '#FFFFFF',
                      border: `2px solid ${manualAge === ageOption ? '#059669' : '#CBD5E1'}`,
                      color: manualAge === ageOption ? '#065F46' : '#0F172A',
                      fontWeight: 800,
                      fontSize: '16px',
                      cursor: 'pointer',
                    }}
                  >
                    {ageOption} {t.years}
                  </button>
                ))}
              </div>
            </div>

            {/* Gender Selection */}
            <div>
              <label style={{ display: 'block', fontSize: '16px', fontWeight: 700, marginBottom: '6px', color: '#0F172A' }}>
                {t.manualGenderLabel}
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                {[
                  { key: 'M', label: t.genderMale },
                  { key: 'F', label: t.genderFemale },
                  { key: 'O', label: t.genderOther },
                ].map((g) => (
                  <button
                    key={g.key}
                    type="button"
                    onClick={() => setManualGender(g.key)}
                    style={{
                      padding: '14px',
                      borderRadius: '12px',
                      background: manualGender === g.key ? '#ECFDF5' : '#FFFFFF',
                      border: `2.5px solid ${manualGender === g.key ? '#059669' : '#CBD5E1'}`,
                      color: manualGender === g.key ? '#065F46' : '#0F172A',
                      fontWeight: 800,
                      fontSize: '16px',
                      cursor: 'pointer',
                    }}
                  >
                    {g.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Mobile Number */}
            <div>
              <label style={{ display: 'block', fontSize: '16px', fontWeight: 700, marginBottom: '6px', color: '#0F172A' }}>
                {t.manualPhoneLabel}
              </label>
              <input
                type="text"
                value={manualPhone}
                onChange={(e) => setManualPhone(e.target.value.replace(/\D/g, '').slice(0, 10))}
                placeholder={t.manualPhonePlaceholder}
                style={{
                  width: '100%',
                  padding: '16px 20px',
                  fontSize: '20px',
                  fontFamily: 'monospace',
                  borderRadius: '12px',
                  border: '2px solid #CBD5E1',
                  background: '#FFFFFF',
                  color: '#0F172A',
                }}
              />
            </div>

            {/* Inline "Create ABHA" toggle */}
            <div
              onClick={() => setManualCreateAbha(!manualCreateAbha)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '14px',
                borderRadius: '10px',
                background: manualCreateAbha ? '#ECFDF5' : '#F8FAFC',
                border: `1.5px solid ${manualCreateAbha ? '#059669' : '#CBD5E1'}`,
                cursor: 'pointer',
              }}
            >
              <input
                type="checkbox"
                checked={manualCreateAbha}
                onChange={() => {}}
                style={{ width: '22px', height: '22px', accentColor: '#059669' }}
              />
              <span style={{ fontSize: '15px', fontWeight: 700, color: '#0F172A' }}>
                {t.manualAbhaCheckbox}
              </span>
            </div>

            <KioskButton
              type="submit"
              variant="primary"
              size="xl"
              icon={<CheckCircle2 size={26} />}
              loading={isLoading}
              onClick={handleManualSubmit}
              sublabel={t.manualSubmitSub}
            >
              {t.manualSubmitBtn}
            </KioskButton>
          </form>
        </KioskCard>
      )}

      {/* Large Virtual Keypad (available on manual, aadhaar, and type modes) */}
      {(mode === 'type' || mode === 'aadhaar' || mode === 'manual') && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: '12px',
            maxWidth: '440px',
            margin: '0 auto',
            width: '100%',
          }}
        >
          {['1', '2', '3', '4', '5', '6', '7', '8', '9', 'CLR', '0', 'BACK'].map((key) => {
            const isSpecial = key === 'CLR' || key === 'BACK';
            return (
              <button
                key={key}
                type="button"
                onClick={() => handleKeypadPress(key)}
                style={{
                  height: '62px',
                  borderRadius: '14px',
                  background: isSpecial ? '#F1F5F9' : '#FFFFFF',
                  border: '2px solid #CBD5E1',
                  color: isSpecial ? '#DC2626' : '#0F172A',
                  fontSize: isSpecial ? '16px' : '24px',
                  fontWeight: 800,
                  cursor: 'pointer',
                  boxShadow: '0 2px 4px rgba(15, 23, 42, 0.05)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                  transition: 'all 0.1s ease',
                }}
              >
                {key === 'BACK' ? (
                  <>
                    <Delete size={22} color="#DC2626" />
                    <span>{t.keyBack}</span>
                  </>
                ) : key === 'CLR' ? (
                  <>
                    <RotateCcw size={20} color="#DC2626" />
                    <span>{t.keyClear}</span>
                  </>
                ) : (
                  key
                )}
              </button>
            );
          })}
        </div>
      )}

      {/* Demographics Confirmation Modal with Queue Privacy Masking */}
      {pendingDemographics && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(15, 23, 42, 0.7)',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '20px',
          }}
        >
          <KioskCard
            padding="36px"
            highlight="green"
            style={{
              width: '100%',
              maxWidth: '560px',
              borderWidth: '3px',
              boxShadow: '0 25px 50px -12px rgba(15, 23, 42, 0.25)',
              background: '#FFFFFF',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '20px' }}>
              <div
                style={{
                  width: '60px',
                  height: '60px',
                  borderRadius: '16px',
                  background: '#ECFDF5',
                  border: '2px solid #A7F3D0',
                  color: '#059669',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <User size={34} />
              </div>

              <div>
                <span
                  style={{
                    fontSize: '13px',
                    fontWeight: 800,
                    color: '#059669',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                  }}
                >
                  {t.modalBadge}
                </span>
                <h2 style={{ fontSize: '26px', fontWeight: 800, color: '#0F172A', margin: '2px 0 0 0' }}>
                  {t.modalTitle}
                </h2>
              </div>
            </div>

            {/* Patient Details Table with Queue Privacy */}
            <div
              style={{
                background: '#F8FAFC',
                borderRadius: '14px',
                border: '1.5px solid #E2E8F0',
                padding: '20px',
                marginBottom: '28px',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: '#64748B', fontSize: '15px', fontWeight: 600 }}>{t.modalName}</span>
                <strong style={{ fontSize: '20px', color: '#0F172A' }}>{pendingDemographics.name}</strong>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: '#64748B', fontSize: '15px', fontWeight: 600 }}>{t.modalAge}</span>
                <strong style={{ fontSize: '16px', color: '#0F172A' }}>
                  {pendingDemographics.age ? `${pendingDemographics.age} ${t.years}` : pendingDemographics.dob || '1985'}
                </strong>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: '#64748B', fontSize: '15px', fontWeight: 600 }}>{t.modalGender}</span>
                <strong style={{ fontSize: '16px', color: '#0F172A' }}>
                  {pendingDemographics.gender === 'M'
                    ? t.genderMale
                    : pendingDemographics.gender === 'F'
                    ? t.genderFemale
                    : t.genderOther}
                </strong>
              </div>

              {/* Masked mobile number for queue privacy */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: '#64748B', fontSize: '15px', fontWeight: 600 }}>{t.modalMobile}</span>
                <span style={{ fontFamily: 'monospace', fontSize: '15px', fontWeight: 700, color: '#334155' }}>
                  {maskString(pendingDemographics.mobile, 3)}
                </span>
              </div>

              {/* Masked ABHA Number if present */}
              {pendingDemographics.abha_number && (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ color: '#64748B', fontSize: '15px', fontWeight: 600 }}>{t.modalAbha}</span>
                  <span
                    style={{
                      fontFamily: 'monospace',
                      fontSize: '15px',
                      fontWeight: 700,
                      color: '#0284C7',
                      background: '#F0F9FF',
                      padding: '2px 8px',
                      borderRadius: '6px',
                    }}
                  >
                    {maskString(pendingDemographics.abha_number, 4)}
                  </span>
                </div>
              )}
            </div>

            {/* Clear Action Buttons */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.4fr', gap: '16px' }}>
              <KioskButton
                variant="secondary"
                size="lg"
                icon={<XCircle size={22} color="#DC2626" />}
                onClick={() => setPendingDemographics(null)}
                sublabel={language === 'en' ? 'Re-enter details' : 'दोबारा दर्ज करें'}
              >
                {t.modalNo}
              </KioskButton>

              <KioskButton
                variant="primary"
                size="lg"
                icon={<CheckCircle2 size={24} />}
                onClick={() => confirmIdentity(pendingDemographics)}
                sublabel={t.modalYesSub}
              >
                {t.modalYes}
              </KioskButton>
            </div>
          </KioskCard>
        </div>
      )}
    </div>
  );
};

export default IdentityScreen;
