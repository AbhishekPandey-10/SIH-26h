import React, { useState } from 'react';
import KioskCard from './KioskCard';
import KioskButton from './KioskButton';
import { useSession } from '../../contexts/SessionContext';
import { InterviewScreen } from '../interview/InterviewScreen';
import {
  Mic,
  FileText,
  User,
  Calendar,
  CreditCard,
  Languages,
  LogOut,
  ArrowRight,
  Camera,
  CheckCircle2,
  HelpCircle,
  Stethoscope,
  MapPin,
  Compass,
} from 'lucide-react';

const DASHBOARD_TEXT = {
  en: {
    activeSession: 'Active OPD Intake Session',
    welcome: 'Welcome,',
    patientFallback: 'Patient',
    tokenLabel: 'Session Token ID:',
    endSessionBtn: 'End Session',
    endSessionSub: 'Wipe & reset screen',
    verifiedTitle: 'Verified Patient Details',
    abhaLabel: 'ABHA ID / Status:',
    aadhaarVerified: 'Aadhaar Verified',
    walkinVerified: 'Walk-In Patient',
    dobGenderLabel: 'DOB / Gender:',
    male: 'Male',
    female: 'Female',
    other: 'Other',
    languageLabel: 'Selected Language:',
    voiceActive: 'Bhashini AI Voice Active',
    service1Tag: 'Primary Service · AI Voice Intake',
    service1Title: 'Speak Your Symptoms (Clinical Voice Interview)',
    service1Desc: 'Voice-guided clinical interview analyzing chief complaints, pain, onset, and past medical history before you meet the doctor.',
    service1Btn: 'Start Voice Interview (Start Now) →',
    service1Sub: 'Tap card or button to speak',
    service2Tag: 'Optional Service · Document Scanner',
    service2Title: 'Scan Prescriptions & Lab Reports',
    service2Desc: 'Place past prescriptions, lab tests, and hospital discharge summaries in front of the camera to extract medicine lists for the doctor.',
    service2Btn: 'Scan Documents (Scan Docs)',
    service2Sub: 'Scan paper records',
    ocrAlert: 'Document Scanner (OCR Pipeline): 17 sample records & camera scan available.',
    helpText: 'Need help? Visit the OPD Help Desk (Room 102) or speak with a hospital volunteer.',
    helpline: 'Helpline: 1800-11-4477 (Toll Free)',
  },
  hi: {
    activeSession: 'सक्रिय कियोस्क सत्र (Active OPD Intake Session)',
    welcome: 'स्वागत है,',
    patientFallback: 'मरीज (Patient)',
    tokenLabel: 'सत्र टोकन आईडी:',
    endSessionBtn: 'सत्र समाप्त करें (End Session)',
    endSessionSub: 'Wipe & reset screen',
    verifiedTitle: 'सत्यापित मरीज पहचान (Verified Patient Details)',
    abhaLabel: 'ABHA ID / स्थिति:',
    aadhaarVerified: 'आधार द्वारा पंजीकृत (Aadhaar Verified)',
    walkinVerified: 'सीधा ओपीडी पंजीकरण (Walk-In)',
    dobGenderLabel: 'जन्म तिथि / लिंग:',
    male: 'पुरुष (Male)',
    female: 'महिला (Female)',
    other: 'अन्य',
    languageLabel: 'पसंदीदा भाषा (Language):',
    voiceActive: 'भाषिणी वॉइस सक्रिय (Voice Active)',
    service1Tag: 'प्राथमिक सेवा · AI Voice Intake',
    service1Title: 'बोलकर बीमारी बताएं (Voice Clinical Interview)',
    service1Desc: 'SOCRATES दर्द विश्लेषण, पिछली बीमारियों और दवाइयों का आवाज-आधारित साक्षात्कार। डॉक्टर से मिलने से पहले अपने लक्षण बताएं।',
    service1Btn: 'आवाज साक्षात्कार शुरू करें (Start Now) →',
    service1Sub: 'कार्ड या बटन छुएं',
    service2Tag: 'वैकल्पिक सेवा · Document Scanner',
    service2Title: 'पर्चे व टेस्ट रिपोर्ट स्कैन करें (Scan Reports)',
    service2Desc: 'कागजी पर्चे व खून/पेशाब की जांच रिपोर्ट कैमरे के सामने रखकर स्कैन करें और दवाइयों की सूची डॉक्टर हेतु तैयार करें।',
    service2Btn: 'दस्तावेज़ स्कैन करें (Scan Docs)',
    service2Sub: 'कागजी पर्चे स्कैन करें',
    ocrAlert: 'दस्तावेज़ स्कैनर (Dev 2 OCR Pipeline): 17 प्री-सीडेड दस्तावेज़ व कैमरा उपलब्ध है।',
    helpText: 'मदद चाहिए? अस्पताल ओपीडी सहायता डेस्क (Room 102) अथवा स्वयंसेवक से संपर्क करें।',
    helpline: 'हेल्पलाइन: 1800-11-4477 (Toll Free)',
  },
  pa: {
    activeSession: 'ਸਰਗਰਮ ਕਿਓਸਕ ਸੈਸ਼ਨ (Active OPD Session)',
    welcome: 'ਸੁਆਗਤ ਹੈ,',
    patientFallback: 'ਮਰੀਜ਼ (Patient)',
    tokenLabel: 'ਸੈਸ਼ਨ ਟੋਕਨ ਆਈਡੀ:',
    endSessionBtn: 'ਸੈਸ਼ਨ ਸਮਾਪਤ ਕਰੋ (End Session)',
    endSessionSub: 'Wipe & reset screen',
    verifiedTitle: 'ਸਤਿਆਪਿਤ ਮਰੀਜ਼ ਵੇਰਵਾ (Verified Patient)',
    abhaLabel: 'ABHA ID / ਸਥਿਤੀ:',
    aadhaarVerified: 'ਆਧਾਰ ਦੁਆਰਾ ਰਜਿਸਟਰਡ',
    walkinVerified: 'ਸਿੱਧਾ ਵਾਕ-ਇਨ ਮਰੀਜ਼',
    dobGenderLabel: 'ਜਨਮ ਮਿਤੀ / ਲਿੰਗ:',
    male: 'ਪੁਰਸ਼ (Male)',
    female: 'ਮਹਿਲਾ (Female)',
    other: 'ਹੋਰ',
    languageLabel: 'ਚੁਣੀ ਗਈ ਭਾਸ਼ਾ (Language):',
    voiceActive: 'ਭਾਸ਼ਿਣੀ ਆਵਾਜ਼ ਸਰਗਰਮ',
    service1Tag: 'ਮੁੱਖ ਸੇਵਾ · AI Voice Intake',
    service1Title: 'ਬੋਲ ਕੇ ਬਿਮਾਰੀ ਦੱਸੋ (Clinical Voice Interview)',
    service1Desc: 'ਦਰਦ ਵਿਸ਼ਲੇਸ਼ਣ, ਪੁਰਾਣੀਆਂ ਬਿਮਾਰੀਆਂ ਅਤੇ ਦਵਾਈਆਂ ਦੀ ਆਵਾਜ਼-ਅਧਾਰਤ ਪੁੱਛਗਿੱਛ। ਡਾਕਟਰ ਨੂੰ ਮਿਲਣ ਤੋਂ ਪਹਿਲਾਂ ਆਪਣੇ ਲੱਛਣ ਦੱਸੋ।',
    service1Btn: 'ਆਵਾਜ਼ ਇੰਟਰਵਿਊ ਸ਼ੁਰੂ ਕਰੋ (Start Now) →',
    service1Sub: 'ਕਾਰਡ ਜਾਂ ਬਟਨ ਛੂਹੋ',
    service2Tag: 'ਵਿਕਲਪਿਕ ਸੇਵਾ · Document Scanner',
    service2Title: 'ਪਰਚੀਆਂ ਅਤੇ ਲੈਬ ਰਿਪੋਰਟਾਂ ਸਕੈਨ ਕਰੋ',
    service2Desc: 'ਪੁਰਾਣੀਆਂ ਪਰਚੀਆਂ ਅਤੇ ਰਿਪੋਰਟਾਂ ਕੈਮਰੇ ਸਾਹਮਣੇ ਰੱਖ ਕੇ ਸਕੈਨ ਕਰੋ ਤਾਂ ਜੋ ਦਵਾਈਆਂ ਦੀ ਸੂਚੀ ਤਿਆਰ ਹੋ ਸਕੇ।',
    service2Btn: 'ਦਸਤਾਵੇਜ਼ ਸਕੈਨ ਕਰੋ (Scan Docs)',
    service2Sub: 'ਪਰਚੀਆਂ ਸਕੈਨ ਕਰੋ',
    ocrAlert: 'ਦਸਤਾਵੇਜ਼ ਸਕੈਨਰ: 17 ਨਮੂਨਾ ਦਸਤਾਵੇਜ਼ ਅਤੇ ਕੈਮਰਾ ਸਕੈਨ ਉਪਲਬਧ ਹਨ।',
    helpText: 'ਮਦਦ ਚਾਹੀਦੀ ਹੈ? ਓਪੀਡੀ ਹੈਲਪ ਡੈਸਕ (ਕਮਰਾ 102) ਜਾਂ ਹਸਪਤਾਲ ਵਾਲੰਟੀਅਰ ਨਾਲ ਸੰਪਰਕ ਕਰੋ।',
    helpline: 'ਹੈਲਪਲਾਈਨ: 1800-11-4477 (ਟੋਲ ਫ੍ਰੀ)',
  },
};

export const KioskDashboard = ({
  onStartInterview,
  onScanDocuments,
  onOpenBodyMap,
  onStartAyush,
}) => {
  const { session, patient, language, endSession } = useSession();
  const [showInterview, setShowInterview] = useState(false);
  const t = DASHBOARD_TEXT[language] || DASHBOARD_TEXT.hi;

  const handleStartInterview = () => {
    if (onStartInterview) {
      onStartInterview();
    } else {
      setShowInterview(true);
    }
  };

  const handleDocScan = () => {
    if (onScanDocuments) {
      onScanDocuments();
    } else {
      alert(t.ocrAlert);
    }
  };

  if (showInterview) {
    return (
      <div style={{ width: '100%', maxWidth: '900px', margin: '0 auto', padding: '24px 20px' }}>
        <button
          onClick={() => setShowInterview(false)}
          style={{
            marginBottom: '16px',
            background: 'var(--color-surface-secondary)',
            border: '1px solid rgba(255,255,255,0.1)',
            color: 'var(--color-text-primary)',
            padding: '10px 18px',
            borderRadius: '10px',
            cursor: 'pointer',
            fontWeight: 600,
            fontSize: '14px',
          }}
        >
          ← डैशबोर्ड पर लौटें (Back to Dashboard)
        </button>
        <InterviewScreen sessionId={session?.session_id || "dev-test-001"} language={language} />
      </div>
    );
  }

  return (
    <div
      style={{
        width: '100%',
        maxWidth: '960px',
        margin: '0 auto',
        padding: '36px 20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '28px',
      }}
    >
      {/* Top Banner with Patient Session Info */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '24px 28px',
          background: '#FFFFFF',
          borderRadius: '16px',
          border: '2px solid #E2E8F0',
          boxShadow: '0 4px 16px rgba(15, 23, 42, 0.05)',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '4px 12px',
              borderRadius: '999px',
              background: '#ECFDF5',
              border: '1.5px solid #A7F3D0',
              fontSize: '13px',
              color: '#065F46',
              fontWeight: 800,
              marginBottom: '6px',
            }}
          >
            <span
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: '#059669',
              }}
            />
            <span>{t.activeSession}</span>
          </div>

          <h2 style={{ fontSize: '28px', fontWeight: 800, color: '#0F172A', margin: 0 }}>
            {t.welcome} {patient?.name || session?.patient_name || t.patientFallback}
          </h2>

          <span style={{ fontSize: '14px', color: '#64748B', fontFamily: 'monospace', marginTop: '4px', display: 'block' }}>
            {t.tokenLabel} <strong style={{ color: '#0284C7' }}>{session?.session_id || 'OPD-ACTIVE'}</strong>
          </span>
        </div>

        <KioskButton
          variant="danger"
          size="md"
          icon={<LogOut size={20} />}
          onClick={endSession}
          sublabel={t.endSessionSub}
        >
          {t.endSessionBtn}
        </KioskButton>
      </div>

      {/* Patient Identity Card */}
      <KioskCard padding="28px">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '18px' }}>
          <User size={22} color="#059669" />
          <h3 style={{ fontSize: '19px', fontWeight: 800, color: '#0F172A', margin: 0 }}>
            {t.verifiedTitle}
          </h3>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '20px' }}>
          {/* ABHA details */}
          <div
            style={{
              padding: '16px',
              background: '#F8FAFC',
              borderRadius: '12px',
              border: '1px solid #E2E8F0',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#64748B', fontSize: '13px', fontWeight: 600 }}>
              <CreditCard size={16} />
              <span>{t.abhaLabel}</span>
            </div>
            <div style={{ fontSize: '16px', fontWeight: 700, color: '#0F172A', marginTop: '4px', fontFamily: 'monospace' }}>
              {patient?.abha_id || patient?.abha_number || (
                patient?.is_manual_walkin ? (
                  <span style={{ color: '#0284C7', fontFamily: 'inherit' }}>{t.walkinVerified}</span>
                ) : (
                  <span style={{ color: '#D97706', fontFamily: 'inherit' }}>{t.aadhaarVerified}</span>
                )
              )}
            </div>
          </div>

          {/* DOB & Gender */}
          <div
            style={{
              padding: '16px',
              background: '#F8FAFC',
              borderRadius: '12px',
              border: '1px solid #E2E8F0',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#64748B', fontSize: '13px', fontWeight: 600 }}>
              <Calendar size={16} />
              <span>{t.dobGenderLabel}</span>
            </div>
            <div style={{ fontSize: '16px', fontWeight: 700, color: '#0F172A', marginTop: '4px' }}>
              {patient?.dob || '1985-06-15'} ·{' '}
              {patient?.gender === 'M' ? t.male : patient?.gender === 'F' ? t.female : t.other}
            </div>
          </div>

          {/* Language & Engine */}
          <div
            style={{
              padding: '16px',
              background: '#F8FAFC',
              borderRadius: '12px',
              border: '1px solid #E2E8F0',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#64748B', fontSize: '13px', fontWeight: 600 }}>
              <Languages size={16} />
              <span>{t.languageLabel}</span>
            </div>
            <div style={{ fontSize: '16px', fontWeight: 700, color: '#059669', marginTop: '4px' }}>
              {language ? language.toUpperCase() : 'HI'} ({t.voiceActive})
            </div>
          </div>
        </div>
      </KioskCard>

      {/* Main Clinical Actions (2 Large Cards) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '24px' }}>
        {/* Service 1: Voice Clinical Interview (Card itself is fully clickable) */}
        <KioskCard
          padding="32px"
          onClick={onStartInterview}
          style={{
            border: '3.5px solid #059669',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            background: '#FFFFFF',
            boxShadow: '0 8px 24px rgba(5, 150, 105, 0.14)',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
          className="kiosk-card interactive"
        >
          <div>
            <div
              style={{
                width: '64px',
                height: '64px',
                borderRadius: '16px',
                background: '#ECFDF5',
                color: '#059669',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '18px',
              }}
            >
              <Mic size={36} />
            </div>

            <div
              style={{
                display: 'inline-block',
                fontSize: '12px',
                fontWeight: 800,
                color: '#059669',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                marginBottom: '6px',
              }}
            >
              {t.service1Tag}
            </div>

            <h3 style={{ fontSize: '24px', fontWeight: 800, color: '#0F172A', marginBottom: '8px' }}>
              {t.service1Title}
            </h3>

            <p style={{ fontSize: '16px', color: '#475569', lineHeight: 1.5, margin: 0 }}>
              {t.service1Desc}
            </p>
          </div>

          <div style={{ marginTop: '28px' }}>
            <KioskButton
              variant="primary"
              size="lg"
              fullWidth
              icon={<ArrowRight size={24} />}
              iconPosition="right"
              onClick={(e) => {
                e.stopPropagation();
                onStartInterview();
              }}
              sublabel={t.service1Sub}
            >
              {t.service1Btn}
            </KioskButton>
          </div>
        </KioskCard>

        {/* Service 2: Paper Prescriptions & OCR (Card itself is fully clickable) */}
        <KioskCard
          padding="32px"
          onClick={handleDocScan}
          style={{
            border: '2.5px solid #CBD5E1',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            background: '#FFFFFF',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
          className="kiosk-card interactive"
        >
          <div>
            <div
              style={{
                width: '64px',
                height: '64px',
                borderRadius: '16px',
                background: '#F0F9FF',
                color: '#0284C7',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '18px',
              }}
            >
              <FileText size={36} />
            </div>

            <div
              style={{
                display: 'inline-block',
                fontSize: '12px',
                fontWeight: 800,
                color: '#0284C7',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                marginBottom: '6px',
              }}
            >
              {t.service2Tag}
            </div>

            <h3 style={{ fontSize: '24px', fontWeight: 800, color: '#0F172A', marginBottom: '8px' }}>
              {t.service2Title}
            </h3>

            <p style={{ fontSize: '16px', color: '#475569', lineHeight: 1.5, margin: 0 }}>
              {t.service2Desc}
            </p>
          </div>

          <div style={{ marginTop: '28px' }}>
            <KioskButton
              variant="info"
              size="lg"
              fullWidth
              icon={<Camera size={22} />}
              onClick={(e) => {
                e.stopPropagation();
                handleDocScan();
              }}
              sublabel={t.service2Sub}
            >
              {t.service2Btn}
            </KioskButton>
          </div>
        </KioskCard>

        {/* Service 3: Interactive 2D Body Map (Phase 5 Dev 2) */}
        <KioskCard
          padding="32px"
          onClick={onOpenBodyMap}
          style={{
            border: '2.5px solid #CBD5E1',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            background: '#FFFFFF',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
          className="kiosk-card interactive"
        >
          <div>
            <div
              style={{
                width: '64px',
                height: '64px',
                borderRadius: '16px',
                background: '#FEF3C7',
                color: '#D97706',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '18px',
              }}
            >
              <MapPin size={36} />
            </div>

            <div
              style={{
                display: 'inline-block',
                fontSize: '12px',
                fontWeight: 800,
                color: '#D97706',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                marginBottom: '6px',
              }}
            >
              {language === 'en' ? 'Phase 5 · Interactive 2D Body Map' : 'कदम 5 · दर्द का 2D बॉडी मैप'}
            </div>

            <h3 style={{ fontSize: '24px', fontWeight: 800, color: '#0F172A', marginBottom: '8px' }}>
              {language === 'en' ? 'Point to Where It Hurts' : 'दर्द का स्थान चुनें (2D Body Map)'}
            </h3>

            <p style={{ fontSize: '16px', color: '#475569', lineHeight: 1.5, margin: 0 }}>
              {language === 'en'
                ? 'Select anatomical pain regions (chest, upper abdomen, back, knee) on a front/back interactive diagram to skip verbal site questions.'
                : 'शरीर के 2D चित्र पर स्पर्श करके दर्द का स्थान बताएं ताकि डॉक्टर को सटीक अंग की जानकारी तुरंत मिल सके।'}
            </p>
          </div>

          <div style={{ marginTop: '28px' }}>
            <KioskButton
              variant="secondary"
              size="lg"
              fullWidth
              icon={<MapPin size={22} />}
              onClick={(e) => {
                e.stopPropagation();
                if (onOpenBodyMap) onOpenBodyMap();
              }}
              sublabel={language === 'en' ? 'Select pain areas' : 'शरीर के अंग चुनें'}
            >
              {language === 'en' ? 'Open 2D Body Map →' : '2D बॉडी मैप खोलें →'}
            </KioskButton>
          </div>
        </KioskCard>

        {/* Service 4: AYUSH Dashavidha Pariksha (Phase 5 Dev 1) */}
        <KioskCard
          padding="32px"
          onClick={onStartAyush}
          style={{
            border: '2.5px solid #A7F3D0',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            background: 'linear-gradient(135deg, #FFFFFF 0%, #F0FDF4 100%)',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
          className="kiosk-card interactive"
        >
          <div>
            <div
              style={{
                width: '64px',
                height: '64px',
                borderRadius: '16px',
                background: '#ECFDF5',
                color: '#059669',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '18px',
              }}
            >
              <Compass size={36} />
            </div>

            <div
              style={{
                display: 'inline-block',
                fontSize: '12px',
                fontWeight: 800,
                color: '#059669',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                marginBottom: '6px',
              }}
            >
              {language === 'en' ? 'Phase 5 · AYUSH Dashavidha Pariksha' : 'आयुष 10-चरणीय परीक्षा'}
            </div>

            <h3 style={{ fontSize: '24px', fontWeight: 800, color: '#0F172A', marginBottom: '8px' }}>
              {language === 'en' ? 'Ayurvedic 10-Stage Assessment' : 'दशविध परीक्षा (Prakriti & Dosha)'}
            </h3>

            <p style={{ fontSize: '16px', color: '#475569', lineHeight: 1.5, margin: 0 }}>
              {language === 'en'
                ? 'Classical Dashavidha Pariksha evaluating Prakriti, Vikriti, Dhatu Sara, Agni, and Satva to generate an 8-fold Ayurvedic clinical summary.'
                : 'प्रकृति, विकृति, सार, संहनन, और अग्नि का शास्त्रीय आयुर्वेदिक मूल्यांकन तथा त्रिदोष स्कोर विश्लेषण।'}
            </p>
          </div>

          <div style={{ marginTop: '28px' }}>
            <KioskButton
              variant="primary"
              size="lg"
              fullWidth
              icon={<Compass size={22} />}
              onClick={(e) => {
                e.stopPropagation();
                if (onStartAyush) onStartAyush();
              }}
              sublabel={language === 'en' ? 'Prakriti & Dosha Score' : 'दशविध परीक्षा शुरू करें'}
            >
              {language === 'en' ? 'Start AYUSH Assessment →' : 'आयुष परीक्षा शुरू करें →'}
            </KioskButton>
          </div>
        </KioskCard>
      </div>

      {/* Hospital Help & Volunteer Support Strip */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 20px',
          background: '#F8FAFC',
          borderRadius: '12px',
          border: '1.5px solid #E2E8F0',
          fontSize: '14px',
          color: '#475569',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <HelpCircle size={20} color="#0284C7" />
          <span>{t.helpText}</span>
        </div>
        <span style={{ fontWeight: 700, color: '#0F172A' }}>{t.helpline}</span>
      </div>
    </div>
  );
};

export default KioskDashboard;
